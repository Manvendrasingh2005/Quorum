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
    "gemini-3.8-flash",
    "gemini-flash-lite-latest",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
)

# Role → preferred model chain (first = primary, rest = fallback)
ROLE_MODELS: dict[str, tuple[str, ...]] = {
    "planner":    ("gemini-flash-lite-latest", "gemini-3.7-flash", "gemini-3.8-flash"),
    "researcher": ("gemini-3.8-flash", "gemini-flash-lite-latest", "gemini-3.7-flash"),
    "critic":     ("gemini-3.7-flash", "gemini-3.8-flash", "gemini-flash-lite-latest"),
    "writer":     ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-lite-latest"),
}

# ── Agent Parameters ─────────────────────────────────────────────────────────
MODEL_ATTEMPTS: int = 2           # retries per model before falling back
MAX_RESEARCH_STEPS: int = 4       # tool-call steps per Researcher sub-question
MAX_SUBQUESTIONS: int = 4         # cap on planner output
MAX_CRITIC_RETRIES: int = 2       # times Critic can reject before force-accept
SEARCH_MAX_RESULTS: int = 5      # Tavily results per query

# ── Pydantic Validation ─────────────────────────────────────────────────────
MAX_SCHEMA_RETRIES: int = 2       # retries when model output fails validation
