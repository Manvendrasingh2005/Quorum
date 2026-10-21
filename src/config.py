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
# High-concurrency, ultra-low-latency Gemini models.
# Each agent role receives a distinct primary model to prevent self-grading bias.
ALL_MODELS: tuple[str, ...] = (
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
)

# Role → preferred model chain (first = primary, rest = fallback)
ROLE_MODELS: dict[str, tuple[str, ...]] = {
    "planner":    ("gemini-3-flash-preview", "gemini-3.5-flash", "gemini-flash-lite-latest"),
    "researcher": ("gemini-3-flash-preview", "gemini-3.5-flash", "gemini-flash-lite-latest"),
    "critic":     ("gemini-3.5-flash", "gemini-3-flash-preview", "gemini-flash-lite-latest"),
    "writer":     ("gemini-3-flash-preview", "gemini-3.5-flash", "gemini-flash-lite-latest"),
}

# ── Agent Parameters ─────────────────────────────────────────────────────────
MODEL_ATTEMPTS: int = 1           # retries per model before falling back
MAX_RESEARCH_STEPS: int = 2       # tool-call steps per Researcher sub-question for speed
MAX_SUBQUESTIONS: int = 3         # cap on standard planner output
MAX_CRITIC_RETRIES: int = 1       # times Critic can reject before force-accept
SEARCH_MAX_RESULTS: int = 3      # Tavily results per query
DEFAULT_SOCKET_TIMEOUT: float = 15.0  # HTTP socket timeout guard in seconds

# ── Pydantic Validation ─────────────────────────────────────────────────────
MAX_SCHEMA_RETRIES: int = 1       # retries when model output fails validation

# ── Research Depth Presets ──────────────────────────────────────────────────
DEPTH_PRESETS: dict[str, dict] = {
    "flash": {
        "subquestions": 1,
        "max_results": 2,
        "timeout": 20.0,
        "label": "Flash Brief",
        "description": "Rapid factual verification (~10s)",
    },
    "standard": {
        "subquestions": 3,
        "max_results": 3,
        "timeout": 30.0,
        "label": "Standard Dossier",
        "description": "Comprehensive multi-angle research (~20-25s)",
    },
    "deep": {
        "subquestions": 4,
        "max_results": 4,
        "timeout": 35.0,
        "label": "Deep Investigation",
        "description": "Exhaustive deep-dive investigation (~40-50s)",
    },
}


def get_depth_preset(depth: str) -> dict:
    """Return preset configuration for the specified research depth."""
    return DEPTH_PRESETS.get(depth.lower(), DEPTH_PRESETS["standard"])


