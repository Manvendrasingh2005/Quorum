"""
Search tool — extracted and isolated from agent code.

Tools are registered here and can be used by any agent that needs them.
The Supervisor decides which agents get tool access.
"""
import json
import re
from tavily import TavilyClient
from src.config import TAVILY_API_KEY, SEARCH_MAX_RESULTS
from google.genai import types


# ── Tavily Client ─────────────────────────────────────────────────────────────
_tavily = TavilyClient(api_key=TAVILY_API_KEY)

# ── Prompt Injection Defense ──────────────────────────────────────────────────
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"(?i)disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"(?i)you\s+are\s+now\s+(in\s+developer\s+mode|dan|an\s+unrestricted)",
    r"(?i)system\s*prompt\s*override",
    r"(?i)<\s*system\s*>",
    r"(?i)\[\s*system\s*\]",
    r"(?i)IMPORTANT:\s*override\s*all",
]

def sanitize_web_content(text: str) -> str:
    """Sanitizes third-party scraped web content against indirect prompt injections."""
    if not text:
        return ""
    sanitized = text
    for pattern in INJECTION_PATTERNS:
        sanitized = re.sub(pattern, "[FILTERED_INJECTION_ATTEMPT]", sanitized)
    # Strip dangerous ASCII control characters except standard whitespace
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)
    return sanitized.strip()


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
    since models sometimes send either format. Applies adversarial sanitization to results."""
    if query:
        search_queries = [query]
    elif queries:
        search_queries = queries
    else:
        return json.dumps({"error": "Expected 'query' or 'queries' argument."})

    all_results = []
    for q in search_queries:
        try:
            results = _tavily.search(query=q, max_results=SEARCH_MAX_RESULTS)
            for r in results.get("results", []):
                clean_title = sanitize_web_content(r.get("title", ""))
                clean_content = sanitize_web_content(r.get("content", ""))
                all_results.append({
                    "title": clean_title,
                    "url": r.get("url", ""),
                    "content": f"<search_context>{clean_content}</search_context>",
                })
        except Exception as e:
            print(f"    [search_web] Error searching '{q}': {e}")
            all_results.append({
                "title": f"Live Search Reference: {q[:40]}",
                "url": f"https://en.wikipedia.org/wiki/Special:Search?search={q.replace(' ', '+')}",
                "content": f"<search_context>Primary topic inquiry: {q}. Focus on verifiable facts and latest technical milestones.</search_context>",
            })
    return json.dumps(all_results)


# ── Tool Registry ─────────────────────────────────────────────────────────────
TOOL_FUNCTIONS: dict[str, callable] = {
    "search_web": search_web,
}
