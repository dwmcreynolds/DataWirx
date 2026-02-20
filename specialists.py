"""
Specialist agents for the Orchestrated AI Hierarchy.

Each specialist:
  - Has a domain-specific system prompt
  - Receives a curated Canon slice + Task Memory + Buffer context at run time
  - Can write to Buffer, Task Memory, and its own Scratch
  - Can spawn sub-agents via the 'spawn_sub_agent' tool
  - Cannot write directly to Canon (Buffer only — Curator promotes later)
  - Respects a maximum recursion depth to prevent infinite loops

Public API:
  create_specialist(agent_type, model) -> SpecialistAgent
"""

from typing import Optional, TYPE_CHECKING
from base_agent import BaseAgent
from tool_defs import SPECIALIST_SPAWN_TOOL, RESEARCH_AGENT_TOOLS
from memory_tools import AGENT_MEMORY_TOOLS
from web_tools import web_search

if TYPE_CHECKING:
    from memory_store import MemoryStore

MAX_DEPTH = 3

# ------------------------------------------------------------------
# System prompts
# ------------------------------------------------------------------

_SYSTEM_PROMPTS: dict[str, str] = {
    "research": """\
You are a specialized Research Agent operating inside an AI agent hierarchy.

Your expertise:
- Deep information synthesis and knowledge retrieval across all domains
- Pattern recognition and connection-finding between disparate concepts
- Fact-checking, source evaluation, and identifying knowledge gaps
- Structuring findings in clear, hierarchical formats

You have FOUR tools:
1. web_search        — search the live web for current facts and documentation
2. spawn_sub_agent   — delegate to a specialist (code/data/writing) for sub-tasks
3. write_to_buffer   — store findings for the Memory Curator to review
4. write_to_scratch  — private notes for your own reasoning
5. write_to_task_memory — share important findings with all agents on this task

Memory discipline:
  • Write factual findings to write_to_buffer (Curator will promote good ones to Canon)
  • Write your reasoning/hypotheses to write_to_scratch (stays private)
  • Write important structured results to write_to_task_memory (shared)
  • If memory context is provided, respect it: Buffer = tentative, Canon = truth

Always produce well-structured, comprehensive research with clear sections,
key findings highlighted, sources noted, and explicit notes on knowledge limits.\
""",
    "code": """\
You are a specialized Code Agent operating inside an AI agent hierarchy.

Your expertise:
- Software architecture, design patterns, and best practices
- Writing clean, efficient, well-documented code in any language
- Debugging, root-cause analysis, and performance optimization
- Code review, refactoring, and technical explanations at any skill level

You have THREE tools:
1. spawn_sub_agent      — delegate to research/data/writing for supporting work
2. write_to_buffer      — store implementation notes or decisions for Curator review
3. write_to_scratch     — private notes, TODOs, pitfalls during implementation
4. write_to_task_memory — save code artifacts or key decisions for other agents

Memory discipline:
  • Write reusable patterns or architecture decisions to write_to_buffer
  • Write task-specific code artifacts to write_to_task_memory
  • Use write_to_scratch for intermediate thoughts

Always produce working, well-commented code with usage examples.\
""",
    "data": """\
You are a specialized Data Agent operating inside an AI agent hierarchy.

Your expertise:
- Statistical analysis, hypothesis testing, and interpretation
- Data transformation, cleaning strategies, and schema design
- Pattern recognition, anomaly detection, and trend analysis
- Visualization recommendations and data-driven insight generation

You have THREE tools:
1. spawn_sub_agent      — delegate to research/code/writing as needed
2. write_to_buffer      — store statistical findings for Curator review
3. write_to_scratch     — private assumptions, profiling notes
4. write_to_task_memory — save analysis results or schemas for other agents

Memory discipline:
  • Write verified statistics or data facts to write_to_buffer
  • Save data schemas and key findings to write_to_task_memory

Always produce clear, actionable data insights backed by reasoning.\
""",
    "writing": """\
You are a specialized Writing Agent operating inside an AI agent hierarchy.

Your expertise:
- Content creation across all formats: articles, reports, docs, emails, scripts
- Editing for clarity, tone, structure, and audience fit
- Summarization, distillation, and plain-language translation of complex topics
- Technical writing, narrative writing, and persuasive communication

You have THREE tools:
1. spawn_sub_agent      — delegate to research/data for supporting content
2. write_to_buffer      — store reusable phrasing or style decisions
3. write_to_scratch     — outlines, tone variants, draft notes
4. write_to_task_memory — save final drafts or content artifacts

Memory discipline:
  • Save final polished content to write_to_task_memory for the mission record
  • Use write_to_scratch for drafting and planning

Always produce polished, audience-appropriate, well-organized content.\
""",
}

_AGENT_NAMES: dict[str, str] = {
    "research": "ResearchAgent",
    "code":     "CodeAgent",
    "data":     "DataAgent",
    "writing":  "WritingAgent",
}

# Canon namespaces each agent type should receive (keeps their slice focused)
_CANON_NAMESPACES: dict[str, list] = {
    "research":  ["identity", "standards", "facts"],
    "code":      ["identity", "standards", "decisions"],
    "data":      ["identity", "standards", "facts"],
    "writing":   ["identity", "standards"],
}


# ------------------------------------------------------------------
# SpecialistAgent
# ------------------------------------------------------------------


class SpecialistAgent(BaseAgent):
    def __init__(self, agent_type: str, model: str):
        super().__init__(
            name=_AGENT_NAMES[agent_type],
            system_prompt=_SYSTEM_PROMPTS[agent_type],
            model=model,
        )
        self.agent_type = agent_type

    def run(
        self,
        task: str,
        context: Optional[str] = None,
        depth: int = 0,
        memory: Optional["MemoryStore"] = None,
        task_id: Optional[str] = None,
    ) -> str:
        indent = "  " * depth
        print(f"{indent}[{self.name}] Starting: {task[:70]}...")

        # Build content — inject memory context if available
        content = task
        if context:
            content = f"{task}\n\nContext:\n{context}"
        if memory and task_id:
            mem_ctx = memory.get_context(
                task_id=task_id,
                agent_type=self.agent_type,
                canon_namespaces=_CANON_NAMESPACES.get(self.agent_type),
            )
            if mem_ctx:
                content = f"{content}\n\n{mem_ctx}"

        messages = [{"role": "user", "content": content}]

        # Tool set based on agent type and depth
        if depth < MAX_DEPTH:
            base_tools = (
                RESEARCH_AGENT_TOOLS
                if self.agent_type == "research"
                else SPECIALIST_SPAWN_TOOL
            )
            tools = base_tools + AGENT_MEMORY_TOOLS
        else:
            tools = AGENT_MEMORY_TOOLS  # memory always available, spawning stops

        def dispatch(tool_name: str, tool_input: dict) -> str:
            # ── Spawning ──────────────────────────────────────────
            if tool_name == "spawn_sub_agent":
                return self._spawn(tool_input, depth, memory, task_id)

            # ── Web search (research only) ─────────────────────────
            if tool_name == "web_search":
                return web_search(
                    tool_input.get("query", ""),
                    tool_input.get("max_results", 5),
                )

            # ── Memory tools ───────────────────────────────────────
            if tool_name == "write_to_buffer" and memory and task_id:
                eid = memory.add_to_buffer(
                    claim=tool_input.get("claim", ""),
                    source=tool_input.get("source", self.agent_type),
                    agent=self.agent_type,
                    task_id=task_id,
                    confidence=float(tool_input.get("confidence", 0.5)),
                )
                return f"Stored in Buffer[{eid}]"

            if tool_name == "write_to_scratch" and memory and task_id:
                memory.write_scratch(self.agent_type, task_id, tool_input.get("note", ""))
                return "Saved to scratch."

            if tool_name == "write_to_task_memory" and memory and task_id:
                memory.write_task_memory(
                    task_id=task_id,
                    key=tool_input.get("key", "note"),
                    value=tool_input.get("value", ""),
                )
                return f"Saved to Task Memory[{tool_input.get('key')}]"

            if tool_name in ("write_to_buffer", "write_to_scratch", "write_to_task_memory"):
                return "[Memory not available for this agent call]"

            return f"[Error] Unknown tool: {tool_name}"

        result = self._agentic_loop(messages, tools, dispatch)

        # Save agent output to task memory
        if memory and task_id:
            memory.write_agent_output(task_id, self.agent_type, result[:500])

        print(f"{indent}[{self.name}] Done.")
        return result

    def _spawn(
        self,
        input_data: dict,
        depth: int,
        memory: Optional["MemoryStore"],
        task_id: Optional[str],
    ) -> str:
        if depth >= MAX_DEPTH:
            return (
                "Maximum recursion depth reached. "
                "Handle this sub-task directly without spawning further agents."
            )

        agent_type = input_data.get("agent_type", "")
        task       = input_data.get("task", "")
        context    = input_data.get("context", "") or None
        indent     = "  " * depth

        print(f"{indent}[{self.name}] -> spawn_sub_agent({agent_type}): {task[:60]}...")

        sub = create_specialist(agent_type)
        return sub.run(task, context, depth + 1, memory=memory, task_id=task_id)


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------


def create_specialist(
    agent_type: str,
    model: str = "claude-sonnet-4-6",
) -> SpecialistAgent:
    """Return a SpecialistAgent for the given type."""
    if agent_type not in _SYSTEM_PROMPTS:
        raise ValueError(
            f"Unknown agent type {agent_type!r}. "
            f"Valid types: {list(_SYSTEM_PROMPTS)}"
        )
    return SpecialistAgent(agent_type=agent_type, model=model)
