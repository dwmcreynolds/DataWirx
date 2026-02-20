"""
Tool schemas for memory operations in the Orchestrated AI Hierarchy.

AGENT_MEMORY_TOOLS        — for all specialist agents (buffer + scratch + task)
ORCHESTRATOR_MEMORY_TOOLS — Orchestrator additionally gets canon write + curator
CURATOR_TOOLS             — MemoryCurator's promotion / dispute tools
"""

# ------------------------------------------------------------------
# Shared by all agents
# ------------------------------------------------------------------

AGENT_MEMORY_TOOLS = [
    {
        "name": "write_to_buffer",
        "description": (
            "Store an unverified finding, claim, or piece of information in the "
            "shared Buffer. Use this for any information you discover that may be "
            "valuable but you cannot fully verify. Do NOT write to Buffer what you "
            "already know to be false. Buffer entries are labelled TENTATIVE and "
            "will be reviewed by the Memory Curator before potentially becoming Canon."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "The claim or finding to store (be specific and factual in phrasing).",
                },
                "source": {
                    "type": "string",
                    "description": "Where this came from: 'web_search', 'reasoning', 'user_input', etc.",
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence level 0.0–1.0. Use 0.3 for uncertain, 0.7 for likely, 0.9 for near-certain.",
                },
            },
            "required": ["claim", "source"],
        },
    },
    {
        "name": "write_to_scratch",
        "description": (
            "Write a private note to your own scratchpad for this task. "
            "Use this for hypotheses, reasoning steps, intermediate thoughts, "
            "TODOs, or anything you want to remember mid-task. "
            "Scratch is private (other agents cannot see it) and ephemeral."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "Your private note.",
                },
            },
            "required": ["note"],
        },
    },
    {
        "name": "write_to_task_memory",
        "description": (
            "Write a named artifact or finding to the shared Task Memory for this run. "
            "All agents on this task can read task memory. Use this for important "
            "intermediate results, structured data, or findings you want to share "
            "with other agents or preserve in the mission record."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Short label for this artifact (e.g. 'research_summary', 'data_schema').",
                },
                "value": {
                    "type": "string",
                    "description": "The content to store.",
                },
            },
            "required": ["key", "value"],
        },
    },
]

# ------------------------------------------------------------------
# Orchestrator-only additions
# ------------------------------------------------------------------

ORCHESTRATOR_MEMORY_TOOLS = AGENT_MEMORY_TOOLS + [
    {
        "name": "write_to_canon",
        "description": (
            "Write a verified, stable fact or decision to the Canon — the system's "
            "authoritative knowledge base. Only use this for information that is "
            "CONFIRMED and should persist across all future tasks. "
            "Prefer letting the Memory Curator promote Buffer entries to Canon. "
            "Only write directly to Canon for user-confirmed facts or architectural decisions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Canon namespace: 'identity', 'standards', 'decisions', or 'projects/{name}'.",
                },
                "key": {
                    "type": "string",
                    "description": "Unique key within the namespace.",
                },
                "content": {
                    "type": "string",
                    "description": "The verified content to canonise.",
                },
                "source": {
                    "type": "string",
                    "description": "Where this was confirmed (e.g. 'user_confirmed', 'test_passed').",
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence level 0.0–1.0.",
                },
            },
            "required": ["namespace", "key", "content", "source"],
        },
    },
    {
        "name": "run_memory_curator",
        "description": (
            "Trigger the Memory Curator to review all Buffer entries for the current task. "
            "The Curator will promote high-confidence, non-conflicting entries to Canon, "
            "flag conflicts as disputes, and dismiss low-quality entries. "
            "Call this at the end of a complex task to consolidate knowledge."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to curate (defaults to current task).",
                },
            },
            "required": [],
        },
    },
]

# ------------------------------------------------------------------
# Memory Curator tools
# ------------------------------------------------------------------

CURATOR_TOOLS = [
    {
        "name": "promote_to_canon",
        "description": (
            "Promote a Buffer entry to Canon because it is reliable, "
            "non-conflicting, and worth preserving as verified truth."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {
                    "type": "string",
                    "description": "The 8-char Buffer entry ID to promote.",
                },
                "namespace": {
                    "type": "string",
                    "description": "Target Canon namespace (e.g. 'facts', 'decisions', 'projects/X').",
                },
                "key": {
                    "type": "string",
                    "description": "Key within the namespace.",
                },
                "confidence": {
                    "type": "number",
                    "description": "Curated confidence score 0.0–1.0.",
                },
            },
            "required": ["entry_id", "namespace", "key"],
        },
    },
    {
        "name": "flag_conflict",
        "description": (
            "Flag a conflict between a Buffer entry and an existing Canon entry. "
            "This creates a Dispute record. Do NOT overwrite Canon — record the dispute."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "buffer_id": {
                    "type": "string",
                    "description": "The Buffer entry ID that conflicts.",
                },
                "canon_id": {
                    "type": "string",
                    "description": "The Canon entry ID it conflicts with.",
                },
                "reason": {
                    "type": "string",
                    "description": "Explanation of the conflict.",
                },
            },
            "required": ["buffer_id", "canon_id", "reason"],
        },
    },
    {
        "name": "dismiss_buffer_entry",
        "description": (
            "Dismiss a Buffer entry as low-quality, incorrect, or redundant. "
            "It will not be promoted to Canon."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {
                    "type": "string",
                    "description": "The Buffer entry ID to dismiss.",
                },
                "reason": {
                    "type": "string",
                    "description": "Why it is being dismissed.",
                },
            },
            "required": ["entry_id"],
        },
    },
]
