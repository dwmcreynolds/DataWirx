"""
OrchestratorAgent — the Master Orchestrator of the AI hierarchy.

Memory responsibilities:
  - Generates a unique task_id for each run
  - Initialises Task Memory with the user prompt
  - Passes memory + task_id to all spawned agents (scoped access)
  - Can write to Canon (limited) and trigger the Memory Curator
  - Runs the Curator at end of each top-level task

The orchestrator uses claude-opus-4-6 by default.
Specialists default to claude-sonnet-4-6.
"""

import uuid
import os
from typing import Optional
from base_agent import BaseAgent
from specialists import create_specialist
from tool_defs import ORCHESTRATOR_TOOLS
from memory_tools import ORCHESTRATOR_MEMORY_TOOLS
from memory_store import MemoryStore
from web_tools import web_search

MAX_ORCHESTRATOR_DEPTH = 3

_SYSTEM_PROMPT = """\
You are the Master Orchestrator of a multi-agent AI hierarchy with persistent memory.

Your role:
1. Analyze the incoming task and decompose it into component parts
2. Route each component to the most appropriate specialist agent
3. Synthesize all agent outputs into a coherent, high-quality final response
4. Manage memory — store verified facts in Canon, unverified findings in Buffer

Available tools:
  • web_search           — search the live web for current information
  • research_agent       — deep research + web search + spawn sub-agents
  • code_agent           — software development, debugging, technical implementation
  • data_agent           — statistical analysis, data processing, pattern recognition
  • writing_agent        — content creation, editing, summarization, communication
  • spawn_sub_orchestrator — spawn a child orchestrator for complex parallel work
  • write_to_buffer      — store unverified findings for Curator review
  • write_to_task_memory — store shared artifacts for this task
  • write_to_canon       — store confirmed facts directly to Canon (use sparingly)
  • run_memory_curator   — trigger Curator to promote Buffer → Canon at task end

Memory rules you must follow:
  • After a complex task, call run_memory_curator to consolidate knowledge
  • Write user-confirmed facts directly to Canon via write_to_canon
  • For anything uncertain, use write_to_buffer instead
  • Sub-agents operate in Buffer + Task memory scope — they cannot write to Canon

Orchestration principles:
  - Decompose before delegating — break complex tasks before assigning them
  - Be specific — give sub-agents all context they need to succeed independently
  - Pass task_id and relevant context to each agent call
  - Synthesize — your final answer should integrate all agent outputs cohesively
"""


class OrchestratorAgent(BaseAgent):
    def __init__(
        self,
        model: str = "claude-opus-4-6",
        specialist_model: str = "claude-sonnet-4-6",
        depth: int = 0,
        memory: Optional[MemoryStore] = None,
        task_id: Optional[str] = None,
    ):
        label = "Orchestrator" if depth == 0 else f"SubOrchestrator[depth={depth}]"
        super().__init__(
            name=label,
            system_prompt=_SYSTEM_PROMPT,
            model=model,
        )
        self.depth = depth
        self.specialist_model = specialist_model

        # Memory setup — only top-level orchestrator creates the store
        if memory is None and depth == 0:
            memory_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "memory"
            )
            memory = MemoryStore(memory_dir)
        self.memory = memory
        self.current_task_id = task_id

        # Tool set — disable at max depth, add memory tools
        if depth < MAX_ORCHESTRATOR_DEPTH:
            self._tools = ORCHESTRATOR_TOOLS + ORCHESTRATOR_MEMORY_TOOLS
        else:
            self._tools = None

    def run(self, task: str, context: Optional[str] = None, depth: int = 0) -> str:
        # Generate task ID for top-level runs
        is_top_level = (self.depth == 0 and self.current_task_id is None)
        if is_top_level:
            self.current_task_id = str(uuid.uuid4())[:12]
            if self.memory:
                self.memory.init_task(self.current_task_id, task)

        indent = "  " * self.depth
        print(f"\n{indent}[{self.name}] Task({self.current_task_id}): {task[:80]}...")

        # Inject memory context into the prompt
        content = task
        if context:
            content = f"{task}\n\nContext:\n{context}"
        if self.memory and self.current_task_id:
            mem_ctx = self.memory.get_context(
                task_id=self.current_task_id,
                agent_type="orchestrator",
                canon_namespaces=None,  # Orchestrator sees all Canon
            )
            if mem_ctx:
                content = f"{content}\n\n{mem_ctx}"

        messages = [{"role": "user", "content": content}]

        def dispatch(tool_name: str, tool_input: dict) -> str:
            return self._dispatch_tool(tool_name, tool_input)

        result = self._agentic_loop(messages, self._tools, dispatch)

        # After top-level task: save output and run Curator
        if is_top_level and self.memory:
            self.memory.write_agent_output(
                self.current_task_id, "orchestrator", result[:500]
            )
            print(f"\n  [Memory] {self.memory.summary()}")

        return result

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        task    = tool_input.get("task", "")
        context = tool_input.get("context") or None
        indent  = "  " * self.depth

        print(f"{indent}[{self.name}] -> {tool_name}: {task[:65] or str(tool_input)[:65]}...")

        # ── Orchestrator-only memory tools ──────────────────────────
        if tool_name == "write_to_canon" and self.memory:
            canon_id = self.memory.write_canon(
                namespace=tool_input.get("namespace", "facts"),
                key=tool_input.get("key", "entry"),
                content=tool_input.get("content", ""),
                source=tool_input.get("source", "orchestrator"),
                confidence=float(tool_input.get("confidence", 0.9)),
            )
            return f"Written to Canon[{canon_id}]"

        if tool_name == "run_memory_curator" and self.memory:
            from curator import MemoryCurator
            tid = tool_input.get("task_id") or self.current_task_id
            curator = MemoryCurator(self.memory)
            return curator.curate_task(tid)

        # ── Shared memory tools ──────────────────────────────────────
        if tool_name == "write_to_buffer" and self.memory:
            eid = self.memory.add_to_buffer(
                claim=tool_input.get("claim", ""),
                source=tool_input.get("source", "orchestrator"),
                agent="orchestrator",
                task_id=self.current_task_id or "unknown",
                confidence=float(tool_input.get("confidence", 0.5)),
            )
            return f"Stored in Buffer[{eid}]"

        if tool_name == "write_to_task_memory" and self.memory:
            self.memory.write_task_memory(
                task_id=self.current_task_id or "unknown",
                key=tool_input.get("key", "note"),
                value=tool_input.get("value", ""),
            )
            return f"Saved to Task Memory[{tool_input.get('key')}]"

        if tool_name == "write_to_scratch" and self.memory:
            self.memory.write_scratch("orchestrator", self.current_task_id or "?",
                                      tool_input.get("note", ""))
            return "Saved to scratch."

        # ── Web search ───────────────────────────────────────────────
        if tool_name == "web_search":
            return web_search(
                tool_input.get("query", ""),
                tool_input.get("max_results", 5),
            )

        # ── Sub-orchestrator ─────────────────────────────────────────
        if tool_name == "spawn_sub_orchestrator":
            return self._spawn_sub_orchestrator(task, context)

        # ── Specialist agents ─────────────────────────────────────────
        specialist_map = {
            "research_agent": "research",
            "code_agent":     "code",
            "data_agent":     "data",
            "writing_agent":  "writing",
        }
        agent_type = specialist_map.get(tool_name)
        if agent_type is None:
            return f"[Error] Unknown tool: {tool_name!r}"

        agent = create_specialist(agent_type, model=self.specialist_model)
        return agent.run(
            task, context,
            depth=self.depth + 1,
            memory=self.memory,
            task_id=self.current_task_id,
        )

    def _spawn_sub_orchestrator(self, task: str, context: Optional[str]) -> str:
        if self.depth >= MAX_ORCHESTRATOR_DEPTH:
            return "Maximum orchestrator depth reached. Use specialist agents directly."
        sub = OrchestratorAgent(
            model=self.model,
            specialist_model=self.specialist_model,
            depth=self.depth + 1,
            memory=self.memory,
            task_id=self.current_task_id,
        )
        return sub.run(task, context)
