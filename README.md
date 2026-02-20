# Orchestrated AI Hierarchy

A multi-agent AI system built on the [Anthropic Claude API](https://docs.anthropic.com/en/api) where a **Master Orchestrator** dynamically routes tasks to specialist sub-agents, each of which can spawn further sub-agents — all backed by a layered, drift-resistant memory system.

---

## Architecture

```
User Task
    │
    ▼
OrchestratorAgent  (claude-opus-4-6)
    ├─ tool: research_agent   ──► ResearchAgent  (claude-sonnet-4-6)
    │                                └─ web_search (DuckDuckGo, live)
    ├─ tool: code_agent       ──► CodeAgent      (claude-sonnet-4-6)
    ├─ tool: data_agent       ──► DataAgent      (claude-sonnet-4-6)
    ├─ tool: writing_agent    ──► WritingAgent   (claude-sonnet-4-6)
    └─ tool: spawn_sub_orchestrator ──► OrchestratorAgent (recursive)
               └─ Each specialist can also:
                  └─ tool: spawn_sub_agent ──► any specialist (max depth 3)
```

Routing uses Claude's native `tool_use` API — the Orchestrator calls agents as tools and synthesises their outputs into a unified final response.

---

## Memory System

The hierarchy uses a **Canon / Buffer / Scratch / Task** memory model designed to prevent hallucination drift across multi-agent runs.

```
memory/
├── canon/canon.json          # Verified, stable truth (write-restricted)
├── buffer/buffer.jsonl       # Unverified findings (open write, append-only)
├── scratch/{agent}_{task}    # Ephemeral per-agent private notes
├── tasks/{task_id}.json      # Per-run mission folder
└── disputes/disputes.jsonl   # Conflict records (never silently overwrite Canon)
```

### Memory layers (retrieval priority order)

| Layer | Who writes | Who reads | Trust level |
|---|---|---|---|
| **Task Memory** | All agents | All agents on task | High — current mission |
| **Canon** | Orchestrator + Curator only | All agents (scoped slice) | Full trust |
| **Buffer** | All agents | All agents (labelled tentative) | Tentative only |
| **Scratch** | Agent itself | Agent itself | Private |

### The Memory Curator

At the end of each complex task, the **MemoryCurator** (powered by `claude-haiku`) reviews all Buffer entries and:

1. **Promotes** high-confidence, non-conflicting entries → Canon
2. **Flags** conflicts as Dispute records (Canon is never silently overwritten)
3. **Dismisses** low-quality, speculative, or task-specific entries

This single rule — *most agents are read-only on Canon* — prevents 80% of memory drift in multi-agent systems.

---

## Project Structure

```
orchestrated_ai/
├── main.py           # Interactive CLI
├── gui.py            # Tkinter desktop GUI (dark theme)
├── base_agent.py     # BaseAgent: Claude API + agentic loop
├── orchestrator.py   # Master Orchestrator
├── specialists.py    # Research / Code / Data / Writing agents
├── curator.py        # Memory Curator (Buffer → Canon promotion)
├── memory_store.py   # Canon, Buffer, Scratch, Task, Dispute storage
├── memory_tools.py   # Claude tool schemas for memory operations
├── tool_defs.py      # Claude tool schemas for agent routing
├── web_tools.py      # DuckDuckGo web search
├── requirements.txt
└── .env              # API key (not committed)
```

---

## Quickstart

**1. Clone and install**

```bash
git clone https://github.com/dwmcreynolds/DataWirx.git
cd DataWirx
pip install -r requirements.txt
```

**2. Add your Anthropic API key**

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

**3. Run**

Desktop GUI:
```bash
python gui.py
```

Command-line interface:
```bash
python main.py
```

---

## Example Tasks

**Simple** — routes to one specialist:
> `Write a short poem about recursion`

**Multi-agent** — Orchestrator delegates to several:
> `Research the pros and cons of Python vs Rust, then write a comparison guide with code examples`

**Live web search** — Research Agent searches the web:
> `Search the web for the latest AI news this week and write a summary`

**Deep hierarchy with memory** — spawns sub-agents, stores findings in Buffer, Curator promotes to Canon:
> `Research quantum computing, write Python code for a simple quantum simulation, and document everything`

---

## How Drift & Hallucination Are Prevented

| Threat | Defence |
|---|---|
| Agent writes false info to Canon | Only Orchestrator + Curator can write Canon |
| Sub-agent misapplies a preference | Each agent receives a **curated Canon slice**, not full Canon |
| Hallucinated "fact" persists | Buffer entries labelled **tentative** until Curator promotes |
| Two agents contradict each other | Conflicts become **Dispute records** — Canon never silently overwritten |
| Memory grows stale/noisy | Curator **scores confidence** and dismisses low-quality entries |

---

## Requirements

- Python 3.10+
- `anthropic >= 0.40.0`
- `python-dotenv >= 1.0.0`
- `duckduckgo-search >= 6.0.0`

---

## License

MIT
