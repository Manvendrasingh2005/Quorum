"""
Multi-agent research system: Planner -> Researcher -> Critic -> Writer,
orchestrated by a plain-Python Supervisor (no LLM cost for orchestration itself).

Each "agent" is the same underlying Gemini model, but with a distinct system
prompt, responsibility, and (for the Critic) the power to reject another
agent's output and send it back for revision. That rejection loop is what
makes this genuinely multi-agent rather than a renamed pipeline.

Setup: same as agent_planner.py -- .env with GEMINI_API_KEY and TAVILY_API_KEY.
Run:   python agent_multiagent.py
"""
from dotenv import load_dotenv; load_dotenv()
import os
import json
import time
from dataclasses import dataclass, field
from google import genai
from google.genai import types, errors
from tavily import TavilyClient

# All models below are free-tier. Each agent role gets a different PRIMARY model
# based on what that role actually needs, with the others as fallback if the
# primary is overloaded/quota-exhausted. This costs nothing extra -- it's about
# matching task difficulty to model capability, and giving the Critic a
# different model than the Researcher so it isn't just grading its own work.
ALL_MODELS = ("gemini-3.8-flash", "gemini-flash-lite-latest", "gemini-3.7-flash", "gemini-3.5-flash")

ROLE_MODELS = {
    "planner":    ("gemini-flash-lite-latest", "gemini-3.7-flash", "gemini-3.8-flash"),
    "researcher": ("gemini-3.8-flash", "gemini-flash-lite-latest", "gemini-3.7-flash"),
    "critic":     ("gemini-3.7-flash", "gemini-3.8-flash", "gemini-flash-lite-latest"),
    "writer":     ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-lite-latest"),
}
MODEL_ATTEMPTS = 2
MAX_RESEARCH_STEPS = 4      # tool-call steps per Researcher sub-question
MAX_SUBQUESTIONS = 4
MAX_CRITIC_RETRIES = 2      # how many times a Researcher can be sent back by the Critic

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

search_decl = types.FunctionDeclaration(
    name="search_web",
    description="Search the web for current information on a topic.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "The search query"}},
        "required": ["query"],
    },
)
tool_config = types.GenerateContentConfig(
    tools=[types.Tool(function_declarations=[search_decl])],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)


# ---- METRICS ----
class RunMetrics:
    def __init__(self):
        self.start_time = None
        self.model_calls = 0
        self.search_calls = 0
        self.fallback_events = 0
        self.retry_events = 0
        self.critic_rejections = 0
        self.subquestions = 0
        self.model_used_by_role = {}  # role -> {model_name: count}

    def start(self):
        self.start_time = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self.start_time

    def summary(self) -> str:
        return (
            f"\n--- Run metrics ---\n"
            f"Total time:         {self.elapsed():.1f}s\n"
            f"Sub-questions:      {self.subquestions}\n"
            f"Model calls:        {self.model_calls}\n"
            f"Search calls:       {self.search_calls}\n"
            f"Fallback switches:  {self.fallback_events}\n"
            f"Same-model retries: {self.retry_events}\n"
            f"Critic rejections:  {self.critic_rejections}\n"
            f"Model usage by role:\n" +
            "".join(
                f"  {role}: {counts}\n" for role, counts in self.model_used_by_role.items()
            )
        )

    def record_model_use(self, role: str, model: str):
        self.model_used_by_role.setdefault(role, {})
        self.model_used_by_role[role][model] = self.model_used_by_role[role].get(model, 0) + 1


metrics = RunMetrics()


def search_web(**kwargs) -> str:
    if "query" in kwargs:
        queries = [kwargs["query"]]
    elif "queries" in kwargs:
        queries = kwargs["queries"]
    else:
        return json.dumps({"error": f"Expected 'query' or 'queries', got: {list(kwargs.keys())}"})

    all_results = []
    for q in queries:
        metrics.search_calls += 1
        results = tavily.search(query=q, max_results=5)
        all_results.extend(
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results["results"]
        )
    return json.dumps(all_results)


TOOL_FUNCTIONS = {"search_web": search_web}


# ---- CORE MODEL CALL (shared infra, used by every agent, routed by role) ----
def call_model(contents, system_prompt: str, use_tools: bool, role: str):
    cfg = tool_config if use_tools else types.GenerateContentConfig()
    cfg.system_instruction = system_prompt

    # Role's preferred chain first, then any remaining models as a last resort
    primary_chain = ROLE_MODELS.get(role, ALL_MODELS)
    models = list(primary_chain) + [m for m in ALL_MODELS if m not in primary_chain]
    last_error = None

    for model_index, model in enumerate(models):
        for attempt in range(MODEL_ATTEMPTS):
            try:
                metrics.model_calls += 1
                response = client.models.generate_content(model=model, contents=contents, config=cfg)
                metrics.record_model_use(role, model)
                return response
            except errors.ServerError as e:
                last_error = e
                if attempt + 1 < MODEL_ATTEMPTS:
                    wait = 2 ** attempt * 2
                    print(f"    {model} busy ({e.code}), retrying in {wait}s...")
                    metrics.retry_events += 1
                    time.sleep(wait)
                elif model_index + 1 < len(models):
                    print(f"    {model} unavailable; trying {models[model_index + 1]}...")
                    metrics.fallback_events += 1
            except errors.ClientError as e:
                if e.code != 429:
                    raise
                last_error = e
                if model_index + 1 < len(models):
                    print(f"    {model} quota exhausted; trying {models[model_index + 1]}...")
                    metrics.fallback_events += 1
                    break

    raise RuntimeError(f"All models failed: {', '.join(models)}") from last_error


def ask(prompt: str, system_prompt: str, role: str, use_tools: bool = False):
    """One-shot plain text call (no tool loop)."""
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    response = call_model(contents, system_prompt, use_tools, role)
    return response


# ============================================================
# AGENT 1: PLANNER
# ============================================================
PLANNER_SYSTEM = (
    "You are a Planning Agent. Your only job is to break a broad research topic "
    "into focused, non-overlapping sub-questions. You do not answer questions yourself."
)

def planner_agent(topic: str) -> list[str]:
    prompt = (
        f"Break this topic into {MAX_SUBQUESTIONS} focused sub-questions that together "
        f"give a complete picture. Topic: \"{topic}\"\n\n"
        "Respond with ONLY a JSON array of strings. Example: [\"question 1\", \"question 2\"]"
    )
    response = ask(prompt, PLANNER_SYSTEM, role="planner")
    text = response.text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        return json.loads(text)[:MAX_SUBQUESTIONS]
    except json.JSONDecodeError:
        print("  [Planner] returned malformed JSON, using topic as single question.")
        return [topic]


# ============================================================
# AGENT 2: RESEARCHER
# ============================================================
RESEARCHER_SYSTEM = (
    "You are a Researcher Agent. Use the search_web tool to find current, factual "
    "information and answer the sub-question. Always cite source URLs. "
    "If you are revising after Critic feedback, address the feedback directly."
)

def researcher_agent(question: str, critic_feedback: str | None = None) -> str:
    prompt = question
    if critic_feedback:
        prompt = (
            f"{question}\n\n"
            f"Your previous answer was rejected by the Critic Agent for this reason:\n"
            f"\"{critic_feedback}\"\n"
            "Revise your research to address this specifically."
        )

    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    for step in range(MAX_RESEARCH_STEPS):
        response = call_model(contents, RESEARCHER_SYSTEM, use_tools=True, role="researcher")
        contents.append(response.candidates[0].content)

        if not response.function_calls:
            return response.text

        result_parts = []
        for fc in response.function_calls:
            print(f"    [Researcher searching] {dict(fc.args)}")
            try:
                output = TOOL_FUNCTIONS[fc.name](**fc.args)
            except Exception as e:
                output = f"Tool error: {e}"
            result_parts.append(types.Part.from_function_response(name=fc.name, response={"result": output}))

        contents.append(types.Content(role="user", parts=result_parts))

    return "Could not complete research within step limit."


# ============================================================
# AGENT 3: CRITIC
# ============================================================
CRITIC_SYSTEM = (
    "You are a Critic Agent reviewing a Researcher's work. Be skeptical. "
    "Check whether claims are grounded in the cited sources, whether sources "
    "are actually present, and whether the answer fully addresses the question. "
    "Respond with ONLY JSON: {\"approved\": true/false, \"feedback\": \"...\"}. "
    "If approved is true, feedback can be a brief note. If false, feedback must "
    "explain exactly what's missing or unsupported so the Researcher can fix it."
)

def critic_agent(question: str, researcher_answer: str) -> dict:
    prompt = (
        f"Sub-question: {question}\n\n"
        f"Researcher's answer:\n{researcher_answer}\n\n"
        "Evaluate this. Respond with ONLY the JSON object described in your instructions."
    )
    response = ask(prompt, CRITIC_SYSTEM, role="critic")
    text = response.text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("  [Critic] returned malformed JSON, defaulting to approve.")
        return {"approved": True, "feedback": "Critic parsing failed; auto-approved."}


# ============================================================
# AGENT 4: WRITER
# ============================================================
WRITER_SYSTEM = (
    "You are a Writer Agent. You only receive Critic-approved findings. "
    "Synthesize them into one well-organized report with headings. "
    "Do not repeat overlapping points -- merge them. Preserve source URL citations."
)

def writer_agent(topic: str, findings: dict[str, str]) -> str:
    findings_text = "\n\n".join(f"Sub-question: {q}\nApproved findings: {a}" for q, a in findings.items())
    prompt = f"Write a research report on: \"{topic}\"\n\nBased on:\n\n{findings_text}"
    response = ask(prompt, WRITER_SYSTEM, role="writer")
    return response.text


# ============================================================
# SUPERVISOR (plain Python -- routes agents, no LLM call itself)
# ============================================================
def run_multiagent_research(topic: str) -> str:
    metrics.start()
    print(f"\n[Supervisor] Dispatching Planner Agent for: {topic}\n")
    subquestions = planner_agent(topic)
    metrics.subquestions = len(subquestions)
    for i, q in enumerate(subquestions, 1):
        print(f"  {i}. {q}")

    approved_findings = {}
    for i, q in enumerate(subquestions, 1):
        print(f"\n[Supervisor] Sub-question {i}/{len(subquestions)}: {q}")
        feedback = None
        for attempt in range(MAX_CRITIC_RETRIES + 1):
            print(f"  [Supervisor] -> Researcher Agent (attempt {attempt + 1})")
            answer = researcher_agent(q, critic_feedback=feedback)

            print(f"  [Supervisor] -> Critic Agent reviewing...")
            verdict = critic_agent(q, answer)

            if verdict.get("approved"):
                print(f"  [Critic] APPROVED. {verdict.get('feedback', '')}")
                approved_findings[q] = answer
                break
            else:
                metrics.critic_rejections += 1
                feedback = verdict.get("feedback", "No specific feedback given.")
                print(f"  [Critic] REJECTED: {feedback}")
                if attempt == MAX_CRITIC_RETRIES:
                    print(f"  [Supervisor] Max retries reached, accepting best-effort answer.")
                    approved_findings[q] = answer

    print(f"\n[Supervisor] -> Writer Agent synthesizing final report...\n")
    report = writer_agent(topic, approved_findings)
    return report + metrics.summary()


if __name__ == "__main__":
    topic = input("Enter a research topic: ")
    print("\n" + run_multiagent_research(topic))
