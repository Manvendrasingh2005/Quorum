"""
Multi-Agent Research System — Configuration.

Centralizes all model settings, API keys, and tunable parameters.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]
TAVILY_API_KEY: str = os.environ["TAVILY_API_KEY"]

# ── Model Configuration ──────────────────────────────────────────────────────
# All free-tier Gemini models. Each agent role gets a different PRIMARY model
# so the Critic isn't grading its own model's work.
ALL_MODELS: tuple[str, ...] = (
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
)

# Role → preferred model chain (first = primary, rest = fallback)
ROLE_MODELS: dict[str, tuple[str, ...]] = {
    "planner":    ("gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"),
    "researcher": ("gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.1-flash-lite"),
    "critic":     ("gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-flash-lite-latest"),
    "writer":     ("gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"),
}

# ── Agent Parameters ─────────────────────────────────────────────────────────
MODEL_ATTEMPTS: int = 1           # retries per model before falling back (was 2)
MAX_RESEARCH_STEPS: int = 3       # tool-call steps per Researcher sub-question (was 4)
MAX_SUBQUESTIONS: int = 3         # cap on planner output (was 4)
MAX_CRITIC_RETRIES: int = 1       # times Critic can reject before force-accept (was 2)
SEARCH_MAX_RESULTS: int = 3      # Tavily results per query (was 5)

# ── Pydantic Validation ─────────────────────────────────────────────────────
MAX_SCHEMA_RETRIES: int = 2       # retries when model output fails validation
