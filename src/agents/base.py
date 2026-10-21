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
import sys
import threading
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from google import genai
from google.genai import types, errors
from pydantic import BaseModel, ValidationError

from src.config import (
    GEMINI_API_KEY,
    ALL_MODELS,
    ROLE_MODELS,
    MODEL_ATTEMPTS,
    MAX_SCHEMA_RETRIES,
    DEFAULT_SOCKET_TIMEOUT,
)
from src.tools.search import SEARCH_DECLARATION, search_web
from src.tools.pdf import PDF_DECLARATION, read_pdf_url

TOOL_FUNCTIONS = {
    "search_web": search_web,
    "read_pdf_url": read_pdf_url,
}


# ── Shared Gemini Client (Guarded with Network Socket Timeout) ────────────────
_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=int(DEFAULT_SOCKET_TIMEOUT * 1000)),
)


# ── Metrics (Thread-Safe, Session-Scoped) ────────────────────────────────────
class RunMetrics:
    """Tracks everything measurable about a research run."""

    def __init__(self):
        self._lock = threading.RLock()
        self.reset()

    def reset(self):
        with getattr(self, '_lock', threading.RLock()):
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
        with self._lock:
            self.start_time = time.monotonic()

    def elapsed(self) -> float:
        with self._lock:
            if self.start_time is None:
                return 0.0
            return time.monotonic() - self.start_time

    def inc_model_calls(self):
        with self._lock:
            self.model_calls += 1

    def inc_search_calls(self):
        with self._lock:
            self.search_calls += 1

    def inc_fallback_events(self):
        with self._lock:
            self.fallback_events += 1

    def inc_retry_events(self):
        with self._lock:
            self.retry_events += 1

    def inc_critic_rejections(self):
        with self._lock:
            self.critic_rejections += 1

    def inc_critic_approvals(self):
        with self._lock:
            self.critic_approvals += 1

    def inc_schema_retries(self):
        with self._lock:
            self.schema_retries += 1

    def inc_memory_hits(self):
        with self._lock:
            self.memory_hits += 1

    def set_subquestions(self, count: int):
        with self._lock:
            self.subquestions = count

    def record_model_use(self, role: str, model: str):
        with self._lock:
            self.model_used_by_role.setdefault(role, {})
            self.model_used_by_role[role][model] = (
                self.model_used_by_role[role].get(model, 0) + 1
            )

    def log_message(self, sender: str, receiver: str, msg_type: str, summary: str):
        """Log inter-agent communication for UI visualization."""
        with self._lock:
            self.agent_messages.append({
                "time": round(self.elapsed(), 2),
                "sender": sender,
                "receiver": receiver,
                "type": msg_type,
                "summary": summary,
            })

    def to_dict(self) -> dict:
        with self._lock:
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
                "model_usage_by_role": {k: dict(v) for k, v in self.model_used_by_role.items()},
            }

    def summary(self) -> str:
        with self._lock:
            return (
                f"\n{'-' * 40}\n"
                f"  Run Metrics\n"
                f"{'-' * 40}\n"
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
                f"{'-' * 40}\n"
            )


# Default global metrics instance (for backward compatibility)
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
    max_output_tokens: int | None = None  # Override in subclass to cap generation

    def __init__(self, metrics_instance: RunMetrics | None = None):
        self._metrics = metrics_instance

    @property
    def metrics(self) -> RunMetrics:
        return self._metrics if self._metrics is not None else metrics

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
        if self.max_output_tokens:
            cfg.max_output_tokens = self.max_output_tokens
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
                    self.metrics.inc_model_calls()
                    t_call = time.perf_counter()
                    print(f"    [{self.role}] calling model {model} (attempt {attempt + 1}/{MODEL_ATTEMPTS})...", flush=True)
                    response = _client.models.generate_content(
                        model=model, contents=contents, config=cfg
                    )
                    call_ms = (time.perf_counter() - t_call) * 1000
                    print(f"    [{self.role}] model {model} responded in {call_ms:.0f}ms", flush=True)
                    self.metrics.record_model_use(self.role, model)
                    return response
                except errors.ServerError as e:
                    last_error = e
                    if attempt + 1 < MODEL_ATTEMPTS:
                        wait = 1
                        print(f"    [{self.role}] {model} server busy ({e.code}), retrying in {wait}s...")
                        self.metrics.inc_retry_events()
                        time.sleep(wait)
                    elif model_index + 1 < len(models):
                        print(f"    [{self.role}] {model} server error ({e.code}); falling back to {models[model_index + 1]}...")
                        self.metrics.inc_fallback_events()
                        break
                except errors.ClientError as e:
                    last_error = e
                    if model_index + 1 < len(models):
                        print(f"    [{self.role}] {model} client issue ({e.code}); falling back to {models[model_index + 1]}...")
                        self.metrics.inc_fallback_events()
                        break
                    if e.code != 429:
                        raise
                except Exception as e:
                    # Catch socket timeouts, WinError connection drops, DNS failures
                    last_error = e
                    if model_index + 1 < len(models):
                        print(f"    [{self.role}] {model} connection error ({type(e).__name__}); falling back to {models[model_index + 1]}...")
                        self.metrics.inc_fallback_events()
                        break

        raise RuntimeError(
            f"[{self.role}] All models failed: {', '.join(models)}"
        ) from last_error

    def _call_model_stream(self, contents: list[types.Content]):
        """Call Gemini with role-based model routing and stream chunks."""
        cfg = self._get_config()
        primary_chain = ROLE_MODELS.get(self.role, ALL_MODELS)
        models = list(primary_chain) + [m for m in ALL_MODELS if m not in primary_chain]
        last_error = None

        for model_index, model in enumerate(models):
            for attempt in range(MODEL_ATTEMPTS):
                try:
                    self.metrics.inc_model_calls()
                    stream = _client.models.generate_content_stream(
                        model=model, contents=contents, config=cfg
                    )
                    self.metrics.record_model_use(self.role, model)
                    return stream
                except errors.ServerError as e:
                    last_error = e
                    if attempt + 1 < MODEL_ATTEMPTS:
                        time.sleep(1)
                        self.metrics.inc_retry_events()
                    elif model_index + 1 < len(models):
                        print(f"    [{self.role}] Stream {model} server error ({e.code}); trying {models[model_index + 1]}...")
                        self.metrics.inc_fallback_events()
                        break
                except errors.ClientError as e:
                    last_error = e
                    if model_index + 1 < len(models):
                        print(f"    [{self.role}] Stream {model} client issue ({e.code}); trying {models[model_index + 1]}...")
                        self.metrics.inc_fallback_events()
                        break
                    if e.code != 429:
                        raise
                except Exception as e:
                    last_error = e
                    if model_index + 1 < len(models):
                        print(f"    [{self.role}] Stream {model} connection error ({type(e).__name__}); trying {models[model_index + 1]}...")
                        self.metrics.inc_fallback_events()
                        break

        raise RuntimeError(
            f"[{self.role}] All models failed: {', '.join(models)}"
        ) from last_error

    def _ask(self, prompt: str, image_data: str | None = None) -> types.GenerateContentResponse:
        """One-shot call (no tool loop), with optional image support."""
        import base64
        parts = []
        if image_data:
            raw_b64 = image_data.split(",", 1)[1] if "," in image_data else image_data
            parts.append(
                types.Part.from_bytes(
                    data=base64.b64decode(raw_b64),
                    mime_type="image/jpeg",
                )
            )
        parts.append(types.Part.from_text(text=prompt))
        
        contents = [types.Content(role="user", parts=parts)]
        return self._call_model(contents)

    def _ask_stream(self, prompt: str):
        """One-shot streaming call (no tool loop). Yields chunk stream."""
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        return self._call_model_stream(contents)

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
                print(f"    [{self.role}] [search] searching: {dict(args)}")
                self.metrics.inc_search_calls()
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

        # Tool step limit reached; prompt model for final synthesis using the search results collected
        contents.append(types.Content(role="user", parts=[types.Part(text="Synthesize your findings from the searches above into a concise, factual answer with inline source URL citations.")]))
        final_response = self._call_model(contents)
        return final_response.text

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
        image_data: str | None = None
    ) -> BaseModel:
        """
        Ask the model and validate the response against a Pydantic schema.
        If validation fails, retry with an error-correction prompt.
        This is a real production pattern.
        """
        last_text = ""
        for attempt in range(MAX_SCHEMA_RETRIES + 1):
            if attempt == 0:
                response = self._ask(prompt, image_data=image_data)
            else:
                # Error-correction retry: tell the model what went wrong
                self.metrics.inc_schema_retries()
                correction_prompt = (
                    f"{prompt}\n\n"
                    f"Your previous response was invalid. The validation error was:\n"
                    f"{validation_error}\n\n"
                    f"Your previous response was:\n{last_text}\n\n"
                    f"Fix the JSON to match the required schema exactly."
                )
                response = self._ask(correction_prompt)

            last_text = response.text.strip() if response.text else ""
            print(f"    [{self.role}] model output len={len(last_text)}, extracting json...", flush=True)
            json_str = self._extract_json(last_text)
            print(f"    [{self.role}] validating with schema {schema.__name__}...", flush=True)

            try:
                data = json.loads(json_str)
                result = schema.model_validate(data)
                print(f"    [{self.role}] validation success!", flush=True)
                return result
            except json.JSONDecodeError as e:
                validation_error = f"Invalid JSON: {e}"
                print(f"    [{self.role}] [!] JSON parse failed (attempt {attempt + 1}): {e}", flush=True)
            except ValidationError as e:
                validation_error = str(e)
                print(f"    [{self.role}] [!] Schema validation failed (attempt {attempt + 1}): {e}", flush=True)

        # If all retries exhausted, raise
        raise ValueError(
            f"[{self.role}] Failed to get valid {schema.__name__} after "
            f"{MAX_SCHEMA_RETRIES + 1} attempts. Last response: {last_text[:200]}"
        )
