"""
Web search capability for the Orchestrated AI Hierarchy.

Uses DuckDuckGo (free, no API key required).

Exports:
  web_search(query, max_results) -> str   — callable used by agents
  WEB_SEARCH_SCHEMA                       — Claude tool JSON schema
"""

WEB_SEARCH_SCHEMA = {
    "name": "web_search",
    "description": (
        "Search the web for current information on any topic. "
        "Use this to find up-to-date facts, news, documentation, or data "
        "that may not be in your training knowledge."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up on the web.",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (1–10). Defaults to 5.",
            },
        },
        "required": ["query"],
    },
}


def web_search(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo and return formatted results."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return (
            "[Error] duckduckgo-search is not installed. "
            "Run: pip install duckduckgo-search"
        )

    print(f"  [web_search] Searching: {query[:70]}...")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        return f"[Search error] {exc}"

    if not results:
        return f"No web results found for: {query!r}"

    lines = [f"Web search results for: {query!r}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.get('title', 'No title')}")
        lines.append(f"   URL: {r.get('href', '')}")
        lines.append(f"   {r.get('body', '')}\n")

    return "\n".join(lines)
