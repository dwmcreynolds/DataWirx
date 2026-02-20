"""
MemoryCurator — the gatekeeper between Buffer and Canon.

The Curator is the ONLY reliable path for Buffer → Canon promotion.
It uses deterministic rules first, then LLM judgement for edge cases.

Promotion pipeline per task:
  1. Read all unpromoted, undismissed Buffer entries for the task
  2. Cluster redundancies (same claim, different phrasing)
  3. Detect conflicts with existing Canon
  4. Score confidence (repetition, source quality, consistency)
  5. Promote if rules pass — write to Canon with audit trail
  6. Flag conflicts as Disputes (never silently overwrite Canon)
  7. Dismiss low-quality entries

The Curator uses claude-haiku-4-5 for speed and cost efficiency.
"""

from typing import Optional
from base_agent import BaseAgent
from memory_store import MemoryStore
from memory_tools import CURATOR_TOOLS

_CURATOR_SYSTEM = """\
You are the Memory Curator for an Orchestrated AI Hierarchy.

Your sole responsibility is to decide what moves from the Buffer (unverified)
into the Canon (verified, stable truth).

Canon rules:
  • Canon is the ship's official log — only add entries that are reliable
  • NEVER overwrite existing Canon — if there is a conflict, flag it as a dispute
  • When in doubt, dismiss rather than promote

Promotion criteria (promote if ALL met):
  ✓ The claim is specific and factual, not speculative
  ✓ It does not contradict existing Canon
  ✓ Confidence ≥ 0.6 OR it comes from a reliable source (web_search, user_input)
  ✓ It is worth preserving across future tasks (not task-specific trivia)

Conflict handling:
  • If a Buffer entry directly contradicts a Canon entry, call flag_conflict
  • Do NOT promote conflicting entries even if you think the Buffer is right
  • Disputes are resolved by humans

Dismissal criteria (dismiss if ANY met):
  ✗ Speculative, vague, or opinion-based
  ✗ Task-specific detail not useful beyond this task
  ✗ Confidence < 0.4 with weak sourcing
  ✗ Already captured in Canon (redundant)

Work through each Buffer entry methodically. Use your tools for every decision.
"""


class MemoryCurator(BaseAgent):
    def __init__(self, memory: MemoryStore, model: str = "claude-haiku-4-5-20251001"):
        super().__init__(
            name="MemoryCurator",
            system_prompt=_CURATOR_SYSTEM,
            model=model,
            max_tokens=4096,
        )
        self.memory = memory

    def curate_task(self, task_id: str) -> str:
        """
        Run curation for all unpromoted Buffer entries in a task.
        Returns a summary of actions taken.
        """
        buffer = [
            e for e in self.memory.read_buffer(task_id=task_id, promoted=False)
            if not e.get("dismissed")
        ]

        if not buffer:
            return f"[Curator] No buffer entries to curate for task {task_id}."

        print(f"\n  [MemoryCurator] Curating {len(buffer)} buffer entries for task {task_id}...")

        canon = self.memory.read_canon()

        # Build evaluation context
        buffer_text = "\n".join(
            f"  ID={e['id']} agent={e['agent']} conf={e['confidence']:.1f} "
            f"src={e['source']}\n  claim: {e['claim']}"
            for e in buffer
        )

        canon_text = "\n".join(
            f"  [{k}]: {v['content'][:150]}"
            for k, v in list(canon.items())[:20]
        ) or "  (empty)"

        prompt = (
            f"Curate these {len(buffer)} Buffer entries for task {task_id}.\n\n"
            f"BUFFER ENTRIES:\n{buffer_text}\n\n"
            f"EXISTING CANON (for conflict detection):\n{canon_text}\n\n"
            "For each entry: promote_to_canon, flag_conflict, or dismiss_buffer_entry."
        )

        messages = [{"role": "user", "content": prompt}]

        def dispatch(tool_name: str, tool_input: dict) -> str:
            return self._dispatch(tool_name, tool_input)

        result = self._agentic_loop(messages, CURATOR_TOOLS, dispatch)
        print(f"  [MemoryCurator] Done. {self.memory.summary()}")
        return result

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "promote_to_canon":
            return self._promote(tool_input)
        if tool_name == "flag_conflict":
            return self._flag_conflict(tool_input)
        if tool_name == "dismiss_buffer_entry":
            return self._dismiss(tool_input)
        return f"[Error] Unknown curator tool: {tool_name}"

    def _promote(self, inp: dict) -> str:
        entry_id  = inp.get("entry_id", "")
        namespace = inp.get("namespace", "facts")
        key       = inp.get("key", entry_id)
        confidence = float(inp.get("confidence", 0.7))

        # Find the buffer entry
        all_buffer = self.memory.read_buffer()
        entry = next((e for e in all_buffer if e.get("id") == entry_id), None)
        if not entry:
            return f"[Curator] Entry {entry_id!r} not found in buffer."

        # Check for conflict with existing Canon before promoting
        existing = self.memory.read_canon(namespace=namespace)
        full_key = f"{namespace}/{key}"
        if full_key in existing:
            return (
                f"[Curator] Canon[{full_key}] already exists. "
                f"Use flag_conflict if there is a discrepancy."
            )

        canon_id = self.memory.write_canon(
            namespace=namespace,
            key=key,
            content=entry["claim"],
            source=f"buffer:{entry['source']}|curator_promoted",
            confidence=confidence,
        )
        self.memory.mark_buffer_promoted(entry_id)
        return f"[Curator] Promoted buffer:{entry_id} → Canon[{canon_id}] (conf={confidence:.2f})"

    def _flag_conflict(self, inp: dict) -> str:
        dispute_id = self.memory.add_dispute(
            buffer_id=inp.get("buffer_id", ""),
            canon_id=inp.get("canon_id", ""),
            reason=inp.get("reason", ""),
        )
        return f"[Curator] Conflict recorded as dispute {dispute_id}"

    def _dismiss(self, inp: dict) -> str:
        entry_id = inp.get("entry_id", "")
        reason   = inp.get("reason", "low quality or task-specific")
        self.memory.mark_buffer_dismissed(entry_id)
        return f"[Curator] Dismissed buffer:{entry_id} — {reason}"
