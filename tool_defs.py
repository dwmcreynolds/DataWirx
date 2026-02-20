"""
Tool JSON schemas for the Orchestrated AI Hierarchy.

ORCHESTRATOR_TOOLS    — tools available to the Master Orchestrator
SPECIALIST_SPAWN_TOOL — spawn tool available to every specialist agent
RESEARCH_AGENT_TOOLS  — spawn + web_search for the Research Agent
"""

from web_tools import WEB_SEARCH_SCHEMA  # noqa: E402

ORCHESTRATOR_TOOLS = [
    {
        "name": "research_agent",
        "description": (
            "Delegate to the Research Agent for information gathering, knowledge "
            "synthesis, fact-checking, and retrieval tasks. Use when the task "
            "requires finding, summarizing, or connecting information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Detailed description of the research task to perform.",
                },
                "context": {
                    "type": "string",
                    "description": "Relevant background, constraints, or prior findings.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "code_agent",
        "description": (
            "Delegate to the Code Agent for software development tasks: writing "
            "code, debugging, refactoring, code review, and technical explanations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Detailed description of the coding task to perform.",
                },
                "context": {
                    "type": "string",
                    "description": "Existing code, requirements, language/framework constraints.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "data_agent",
        "description": (
            "Delegate to the Data Agent for data analysis, statistical analysis, "
            "data transformation, pattern recognition, and data-driven insights."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Detailed description of the data analysis task.",
                },
                "context": {
                    "type": "string",
                    "description": "Data samples, schemas, or analytical context.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "writing_agent",
        "description": (
            "Delegate to the Writing Agent for content creation, editing, "
            "summarization, translation, and communication tasks of any format."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Detailed description of the writing task.",
                },
                "context": {
                    "type": "string",
                    "description": "Source material, style guidelines, or audience information.",
                },
            },
            "required": ["task"],
        },
    },
    WEB_SEARCH_SCHEMA,
    {
        "name": "spawn_sub_orchestrator",
        "description": (
            "Spawn an independent sub-orchestrator to manage a complex sub-task "
            "that itself requires coordinating multiple specialist agents. Use this "
            "when a portion of the work is large enough to warrant its own hierarchy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The complex sub-task for the sub-orchestrator to handle.",
                },
                "context": {
                    "type": "string",
                    "description": "Context, goals, and constraints for the sub-orchestrator.",
                },
            },
            "required": ["task"],
        },
    },
]

RESEARCH_AGENT_TOOLS = [
    WEB_SEARCH_SCHEMA,
    {
        "name": "spawn_sub_agent",
        "description": (
            "Spawn a specialized sub-agent to handle a specific portion of your task "
            "that falls outside your primary domain or requires specialist expertise."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["research", "code", "data", "writing"],
                    "description": "The type of specialist agent to spawn.",
                },
                "task": {
                    "type": "string",
                    "description": "The task for the sub-agent to perform.",
                },
                "context": {
                    "type": "string",
                    "description": "Context and information to pass to the sub-agent.",
                },
            },
            "required": ["agent_type", "task"],
        },
    },
]

SPECIALIST_SPAWN_TOOL = [
    {
        "name": "spawn_sub_agent",
        "description": (
            "Spawn a specialized sub-agent to handle a specific portion of your task "
            "that falls outside your primary domain or requires specialist expertise."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["research", "code", "data", "writing"],
                    "description": "The type of specialist agent to spawn.",
                },
                "task": {
                    "type": "string",
                    "description": "The task for the sub-agent to perform.",
                },
                "context": {
                    "type": "string",
                    "description": "Context and information to pass to the sub-agent.",
                },
            },
            "required": ["agent_type", "task"],
        },
    }
]
