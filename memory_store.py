"""
MemoryStore — persistent, layered memory for the Orchestrated AI Hierarchy.

Layers (read priority: highest → lowest):
  1. Task Memory   — current mission artifacts and findings
  2. Canon         — verified, stable truths (write-restricted)
  3. Buffer        — unverified claims, candidate facts (open write)
  4. Scratch       — ephemeral per-agent notes (agent-local)

Disputes are recorded when Buffer claims conflict with Canon.
The MemoryCurator (curator.py) promotes Buffer → Canon via deterministic rules.

Storage: plain JSON / JSONL files under memory/ in the project directory.
"""

import json
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class MemoryStore:
    def __init__(self, base_dir: str):
        self.base = Path(base_dir)
        for d in ["canon", "buffer", "scratch", "tasks", "disputes"]:
            (self.base / d).mkdir(parents=True, exist_ok=True)
        self._seed_canon_if_empty()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _read_json(self, path: Path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    def _write_json(self, path: Path, data) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _append_jsonl(self, path: Path, record: dict) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path) -> list:
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return records

    def _seed_canon_if_empty(self) -> None:
        """Seed Canon with baseline identity entries on first run."""
        canon = self._read_json(self.base / "canon" / "canon.json", {})
        if canon:
            return
        self.write_canon(
            namespace="identity",
            key="system",
            content=(
                "This is an Orchestrated AI Hierarchy. "
                "Agents: Orchestrator, ResearchAgent (web search), "
                "CodeAgent, DataAgent, WritingAgent. "
                "Max recursion depth: 3."
            ),
            source="system_init",
            confidence=1.0,
            confirmed_by_user=True,
        )
        self.write_canon(
            namespace="standards",
            key="memory_rules",
            content=(
                "Canon = verified truth (write-restricted to Orchestrator and Curator). "
                "Buffer = unverified candidates (open write). "
                "Scratch = ephemeral per-agent notes. "
                "Task = current mission artifacts. "
                "Buffer claims must be labelled tentative until promoted."
            ),
            source="system_init",
            confidence=1.0,
            confirmed_by_user=True,
        )

    # ------------------------------------------------------------------
    # Canon  (write-restricted: Orchestrator + Curator only)
    # ------------------------------------------------------------------

    def read_canon(self, namespace: Optional[str] = None) -> dict:
        """Return all Canon entries, optionally filtered to a namespace prefix."""
        data = self._read_json(self.base / "canon" / "canon.json", {})
        if namespace:
            return {k: v for k, v in data.items() if k.startswith(namespace)}
        return data

    def write_canon(
        self,
        namespace: str,
        key: str,
        content: str,
        source: str,
        confidence: float = 1.0,
        confirmed_by_user: bool = False,
    ) -> str:
        """Write a verified entry to Canon. Returns the entry ID."""
        canon_file = self.base / "canon" / "canon.json"
        data = self._read_json(canon_file, {})
        entry_id = f"{namespace}/{key}"
        data[entry_id] = {
            "content": content,
            "source": source,
            "confidence": confidence,
            "confirmed_by_user": confirmed_by_user,
            "last_verified": self._now(),
            "namespace": namespace,
        }
        self._write_json(canon_file, data)
        return entry_id

    # ------------------------------------------------------------------
    # Buffer  (open write — any agent)
    # ------------------------------------------------------------------

    def add_to_buffer(
        self,
        claim: str,
        source: str,
        agent: str,
        task_id: str,
        confidence: float = 0.5,
    ) -> str:
        """Append an unverified claim to the Buffer. Returns entry ID."""
        entry_id = str(uuid.uuid4())[:8]
        record = {
            "id": entry_id,
            "claim": claim,
            "source": source,
            "agent": agent,
            "task_id": task_id,
            "confidence": confidence,
            "timestamp": self._now(),
            "promoted": False,
            "dismissed": False,
        }
        self._append_jsonl(self.base / "buffer" / "buffer.jsonl", record)
        print(f"  [Memory/Buffer] +{entry_id}: {claim[:60]}...")
        return entry_id

    def read_buffer(
        self,
        task_id: Optional[str] = None,
        promoted: Optional[bool] = None,
    ) -> list:
        """Read Buffer entries with optional filters."""
        records = self._read_jsonl(self.base / "buffer" / "buffer.jsonl")
        if task_id is not None:
            records = [r for r in records if r.get("task_id") == task_id]
        if promoted is not None:
            records = [r for r in records if r.get("promoted") == promoted]
        return records

    def _rewrite_buffer(self, updater) -> None:
        """Rewrite buffer.jsonl applying updater(record) to each entry."""
        buf_file = self.base / "buffer" / "buffer.jsonl"
        records = self._read_jsonl(buf_file)
        buf_file.write_text(
            "\n".join(json.dumps(updater(r), ensure_ascii=False) for r in records) + "\n",
            encoding="utf-8",
        )

    def mark_buffer_promoted(self, entry_id: str) -> None:
        self._rewrite_buffer(
            lambda r: {**r, "promoted": True} if r.get("id") == entry_id else r
        )

    def mark_buffer_dismissed(self, entry_id: str) -> None:
        self._rewrite_buffer(
            lambda r: {**r, "dismissed": True} if r.get("id") == entry_id else r
        )

    # ------------------------------------------------------------------
    # Scratch  (per-agent, per-task — ephemeral)
    # ------------------------------------------------------------------

    def write_scratch(self, agent_type: str, task_id: str, note: str) -> None:
        path = self.base / "scratch" / f"{agent_type}_{task_id}.json"
        notes = self._read_json(path, [])
        notes.append({"note": note, "timestamp": self._now()})
        self._write_json(path, notes)

    def read_scratch(self, agent_type: str, task_id: str) -> list:
        path = self.base / "scratch" / f"{agent_type}_{task_id}.json"
        return self._read_json(path, [])

    def clear_scratch(self, agent_type: str, task_id: str) -> None:
        path = self.base / "scratch" / f"{agent_type}_{task_id}.json"
        if path.exists():
            path.unlink()

    # ------------------------------------------------------------------
    # Task Memory  (per-task, shared between all agents on that task)
    # ------------------------------------------------------------------

    def init_task(self, task_id: str, prompt: str) -> None:
        path = self.base / "tasks" / f"{task_id}.json"
        self._write_json(path, {
            "task_id": task_id,
            "prompt": prompt,
            "created": self._now(),
            "artifacts": {},
            "agent_outputs": {},
        })
        print(f"  [Memory/Task] Initialised task {task_id}")

    def write_task_memory(self, task_id: str, key: str, value: str) -> None:
        path = self.base / "tasks" / f"{task_id}.json"
        data = self._read_json(path, {"artifacts": {}})
        data.setdefault("artifacts", {})[key] = {
            "value": value,
            "timestamp": self._now(),
        }
        self._write_json(path, data)
        print(f"  [Memory/Task] {task_id}[{key}] saved")

    def write_agent_output(self, task_id: str, agent: str, output: str) -> None:
        path = self.base / "tasks" / f"{task_id}.json"
        data = self._read_json(path, {"agent_outputs": {}})
        data.setdefault("agent_outputs", {})[agent] = output
        self._write_json(path, data)

    def read_task_memory(self, task_id: str) -> dict:
        return self._read_json(self.base / "tasks" / f"{task_id}.json", {})

    # ------------------------------------------------------------------
    # Disputes  (conflict log — never overwrite Canon, record dispute)
    # ------------------------------------------------------------------

    def add_dispute(self, buffer_id: str, canon_id: str, reason: str) -> str:
        dispute_id = str(uuid.uuid4())[:8]
        record = {
            "id": dispute_id,
            "buffer_id": buffer_id,
            "canon_id": canon_id,
            "reason": reason,
            "timestamp": self._now(),
            "resolved": False,
        }
        self._append_jsonl(self.base / "disputes" / "disputes.jsonl", record)
        print(f"  [Memory/Dispute] {dispute_id}: buffer:{buffer_id} vs canon:{canon_id}")
        return dispute_id

    def read_disputes(self, resolved: Optional[bool] = None) -> list:
        records = self._read_jsonl(self.base / "disputes" / "disputes.jsonl")
        if resolved is not None:
            records = [r for r in records if r.get("resolved") == resolved]
        return records

    # ------------------------------------------------------------------
    # Context retrieval (ordered: Task → Canon → Buffer → Scratch)
    # ------------------------------------------------------------------

    def get_context(
        self,
        task_id: str,
        agent_type: str,
        canon_namespaces: Optional[list] = None,
        max_buffer: int = 8,
        max_scratch: int = 5,
    ) -> str:
        """
        Build the ordered memory context string for an agent.

        Agents receive:
          1. Task memory    (current mission truth)
          2. Canon slice    (stable verified truth)
          3. Buffer entries (labelled TENTATIVE — not truth)
          4. Own scratch    (private notes)
        """
        sections = []

        # 1. Task memory
        task = self.read_task_memory(task_id)
        artifacts = task.get("artifacts", {})
        prior_outputs = task.get("agent_outputs", {})
        if artifacts or prior_outputs:
            lines = ["── TASK MEMORY (mission artifacts) ──"]
            for k, v in artifacts.items():
                lines.append(f"  [{k}] {v['value'][:400]}")
            for agent, out in prior_outputs.items():
                lines.append(f"  [output:{agent}] {out[:300]}")
            sections.append("\n".join(lines))

        # 2. Canon slice
        canon = self.read_canon()
        if canon_namespaces:
            canon = {k: v for k, v in canon.items()
                     if any(k.startswith(ns) for ns in canon_namespaces)}
        if canon:
            lines = ["── CANON (verified truth — trust fully) ──"]
            for k, entry in list(canon.items())[:10]:
                lines.append(f"  [{k}] {entry['content'][:300]}")
            sections.append("\n".join(lines))

        # 3. Buffer (tentative)
        buffer = self.read_buffer(task_id=task_id, promoted=False)
        buffer = [b for b in buffer if not b.get("dismissed")]
        if buffer:
            lines = ["── BUFFER (TENTATIVE — unverified, do NOT treat as truth) ──"]
            for entry in buffer[-max_buffer:]:
                lines.append(
                    f"  [tentative|{entry['agent']}|conf:{entry['confidence']:.1f}] "
                    f"{entry['claim'][:300]}"
                )
            sections.append("\n".join(lines))

        # 4. Scratch (own notes)
        scratch = self.read_scratch(agent_type, task_id)
        if scratch:
            lines = ["── SCRATCH (your own notes) ──"]
            for item in scratch[-max_scratch:]:
                lines.append(f"  - {item['note'][:200]}")
            sections.append("\n".join(lines))

        if not sections:
            return ""

        header = f"[Memory context for task {task_id} | agent: {agent_type}]"
        return header + "\n" + "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Summary (for logging / GUI)
    # ------------------------------------------------------------------

    def summary(self) -> str:
        canon_count  = len(self.read_canon())
        buffer_all   = self.read_buffer()
        buffer_live  = [b for b in buffer_all if not b.get("promoted") and not b.get("dismissed")]
        disputes     = self.read_disputes(resolved=False)
        tasks        = list((self.base / "tasks").glob("*.json"))
        return (
            f"Canon:{canon_count} entries | "
            f"Buffer:{len(buffer_live)} live / {len(buffer_all)} total | "
            f"Tasks:{len(tasks)} | Disputes:{len(disputes)} open"
        )
