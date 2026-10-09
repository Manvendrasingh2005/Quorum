"""
Search tool — extracted and isolated from agent code.

Tools are registered here and can be used by any agent that needs them.
The Supervisor decides which agents get tool access.
"""
import json
from tavily import TavilyClient
from src.config import TAVILY_API_KEY, SEARCH_MAX_RESULTS
from google.genai import types


# ── Tavily Client ─────────────────────────────────────────────────────────────
_tavily = TavilyClient(api_key=TAVILY_API_KEY)


# ── Tool Declaration (what the model "sees") ──────────────────────────────────
SEARCH_DECLARATION = types.FunctionDeclaration(
    name="search_web",
    description="Search the web for current information on a topic.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
        },
        "required": ["query"],
    },
)


def search_web(query: str | None = None, queries: list[str] | None = None) -> str:
    """Execute a web search. Handles both single 'query' and list 'queries' args
    since models sometimes send either format."""
    if query:
        search_queries = [query]
    elif queries:
        search_queries = queries
    else:
        return json.dumps({"error": "Expected 'query' or 'queries' argument."})

    all_results = []
    for q in search_queries:
        results = _tavily.search(query=q, max_results=SEARCH_MAX_RESULTS)
        all_results.extend(
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results["results"]
        )
    return json.dumps(all_results)


# ── Tool Registry ─────────────────────────────────────────────────────────────
TOOL_FUNCTIONS: dict[str, callable] = {
    "search_web": search_web,
}
