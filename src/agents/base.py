"""
Base Agent — shared infrastructure for all agent roles.

Handles:
- Model calling with retry + multi-model fallback
- Metrics tracking
- Tool execution loop
- Pydantic output validation with error-correction retries
"""
import json
import time
import re
from google import genai
from google.genai import types, errors
from pydantic import BaseModel, ValidationError

from src.config import (
    GEMINI_API_KEY,
    ALL_MODELS,
    ROLE_MODELS,
    MODEL_ATTEMPTS,
    MAX_SCHEMA_RETRIES,
)
from src.tools.search import SEARCH_DECLARATION, search_web
from src.tools.pdf import PDF_DECLARATION, read_pdf_url

TOOL_FUNCTIONS = {
    "search_web": search_web,
    "read_pdf_url": read_pdf_url,
}


# ── Shared Gemini Client ──────────────────────────────────────────────────────
_client = genai.Client(api_key=GEMINI_API_KEY)


# ── Metrics (singleton, shared across all agents) ─────────────────────────────
class RunMetrics:
    """Tracks everything measurable about a research run."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.start_time: float | None = None
        self.model_calls: int = 0
        self.search_calls: int = 0
        self.fallback_events: int = 0
        self.retry_events: int = 0
        self.critic_rejections: int = 0
        self.critic_approvals: int = 0
        self.schema_retries: int = 0
        self.memory_hits: int = 0
        self.subquestions: int = 0
        self.model_used_by_role: dict[str, dict[str, int]] = {}
        self.agent_messages: list[dict] = []  # log of inter-agent communication

    def start(self):
        self.reset()
        self.start_time = time.monotonic()

    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        return time.monotonic() - self.start_time

    def record_model_use(self, role: str, model: str):
        self.model_used_by_role.setdefault(role, {})
        self.model_used_by_role[role][model] = (
            self.model_used_by_role[role].get(model, 0) + 1
        )

    def log_message(self, sender: str, receiver: str, msg_type: str, summary: str):
        """Log inter-agent communication for UI visualization."""
        self.agent_messages.append({
            "time": self.elapsed(),
            "sender": sender,
            "receiver": receiver,
            "type": msg_type,
            "summary": summary,
        })

    def to_dict(self) -> dict:
        return {
            "total_time": round(self.elapsed(), 1),
            "model_calls": self.model_calls,
            "search_calls": self.search_calls,
            "fallback_events": self.fallback_events,
            "retry_events": self.retry_events,
            "critic_rejections": self.critic_rejections,
            "critic_approvals": self.critic_approvals,
            "schema_retries": self.schema_retries,
            "memory_hits": self.memory_hits,
            "subquestions": self.subquestions,
            "model_usage_by_role": self.model_used_by_role,
        }

    def summary(self) -> str:
        return (
            f"\n{'─' * 40}\n"
            f"  Run Metrics\n"
            f"{'─' * 40}\n"
            f"  Total time:         {self.elapsed():.1f}s\n"
            f"  Sub-questions:      {self.subquestions}\n"
            f"  Model calls:        {self.model_calls}\n"
            f"  Search calls:       {self.search_calls}\n"
            f"  Critic approvals:   {self.critic_approvals}\n"
            f"  Critic rejections:  {self.critic_rejections}\n"
            f"  Memory hits:        {self.memory_hits}\n"
            f"  Schema retries:     {self.schema_retries}\n"
            f"  Fallback switches:  {self.fallback_events}\n"
            f"  Same-model retries: {self.retry_events}\n"
            f"{'─' * 40}\n"
        )


# Global metrics instance, importable by all agents
metrics = RunMetrics()


# ── Base Agent Class ──────────────────────────────────────────────────────────
class BaseAgent:
    """
    Base class for all agents.

    Subclasses define:
      - role: str          — agent role name (planner, researcher, etc.)
      - system_prompt: str — constraining instructions for this role
      - uses_tools: bool   — whether this agent has tool access
    """

    role: str = "base"
    system_prompt: str = "You are a helpful assistant."
    uses_tools: bool = False

    def _get_config(self) -> types.GenerateContentConfig:
        """Build the GenerateContentConfig for this agent's role."""
        if self.uses_tools:
            cfg = types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=[SEARCH_DECLARATION, PDF_DECLARATION])],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            )
        else:
            cfg = types.GenerateContentConfig()
        cfg.system_instruction = self.system_prompt
        return cfg

    def _call_model(self, contents: list[types.Content]) -> types.GenerateContentResponse:
        """Call Gemini with role-based model routing, retry, and fallback."""
        cfg = self._get_config()

        primary_chain = ROLE_MODELS.get(self.role, ALL_MODELS)
        models = list(primary_chain) + [m for m in ALL_MODELS if m not in primary_chain]
        last_error = None

        for model_index, model in enumerate(models):
            for attempt in range(MODEL_ATTEMPTS):
                try:
                    metrics.model_calls += 1
                    response = _client.models.generate_content(
                        model=model, contents=contents, config=cfg
                    )
                    metrics.record_model_use(self.role, model)
                    return response
                except errors.ServerError as e:
                    last_error = e
                    if attempt + 1 < MODEL_ATTEMPTS:
                        wait = 2 ** attempt * 2
                        print(f"    [{self.role}] {model} busy ({e.code}), retrying in {wait}s...")
                        metrics.retry_events += 1
                        time.sleep(wait)
                    elif model_index + 1 < len(models):
                        print(f"    [{self.role}] {model} unavailable; trying {models[model_index + 1]}...")
                        metrics.fallback_events += 1
                except errors.ClientError as e:
                    if e.code != 429:
                        raise
                    last_error = e
                    if model_index + 1 < len(models):
                        print(f"    [{self.role}] {model} quota exhausted; trying {models[model_index + 1]}...")
                        metrics.fallback_events += 1
                        break

        raise RuntimeError(
            f"[{self.role}] All models failed: {', '.join(models)}"
        ) from last_error

    def _ask(self, prompt: str) -> types.GenerateContentResponse:
        """One-shot call (no tool loop)."""
        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
        return self._call_model(contents)

    def _ask_with_tools(self, prompt: str) -> str:
        """Multi-step tool-calling loop. Returns final text response."""
        from src.config import MAX_RESEARCH_STEPS

        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

        for step in range(MAX_RESEARCH_STEPS):
            response = self._call_model(contents)
            contents.append(response.candidates[0].content)

            if not response.function_calls:
                return response.text

            result_parts = []
            for fc in response.function_calls:
                # GenAI sometimes returns None for args instead of an empty dict
                args = fc.args or {}
                print(f"    [{self.role}] 🔍 searching: {dict(args)}")
                metrics.search_calls += 1
                try:
                    output = TOOL_FUNCTIONS[fc.name](**args)
                except Exception as e:
                    output = f"Tool error: {e}"
                result_parts.append(
                    types.Part.from_function_response(
                        name=fc.name, response={"result": output}
                    )
                )

            contents.append(types.Content(role="user", parts=result_parts))

        return "Could not complete research within step limit."

    def _extract_json(self, text: str) -> str:
        """Strip markdown fences and extract JSON from model output."""
        text = text.strip()
        # Try to extract from ```json ... ``` blocks
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        return text

    def _validated_ask(
        self,
        prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:
        """
        Ask the model and validate the response against a Pydantic schema.
        If validation fails, retry with an error-correction prompt.
        This is a real production pattern.
        """
        last_text = ""
        for attempt in range(MAX_SCHEMA_RETRIES + 1):
            if attempt == 0:
                response = self._ask(prompt)
            else:
                # Error-correction retry: tell the model what went wrong
                metrics.schema_retries += 1
                correction_prompt = (
                    f"{prompt}\n\n"
                    f"Your previous response was invalid. The validation error was:\n"
                    f"{validation_error}\n\n"
                    f"Your previous response was:\n{last_text}\n\n"
                    f"Fix the JSON to match the required schema exactly."
                )
                response = self._ask(correction_prompt)

            last_text = response.text.strip()
            json_str = self._extract_json(last_text)

            try:
                data = json.loads(json_str)
                return schema.model_validate(data)
            except json.JSONDecodeError as e:
                validation_error = f"Invalid JSON: {e}"
                print(f"    [{self.role}] ⚠️ JSON parse failed (attempt {attempt + 1}): {e}")
            except ValidationError as e:
                validation_error = str(e)
                print(f"    [{self.role}] ⚠️ Schema validation failed (attempt {attempt + 1})")

        # If all retries exhausted, raise
        raise ValueError(
            f"[{self.role}] Failed to get valid {schema.__name__} after "
            f"{MAX_SCHEMA_RETRIES + 1} attempts. Last response: {last_text[:200]}"
        )
