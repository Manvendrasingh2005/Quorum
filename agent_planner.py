from dotenv import load_dotenv; load_dotenv()
import os
import json
import time
from google import genai
from google.genai import types, errors
from tavily import TavilyClient

MODEL = "gemini-3.8-flash"
FALLBACK_MODELS = ("gemini-flash-lite-latest", "gemini-3.7-flash", "gemini-3.5-flash")
MODEL_ATTEMPTS = 2
MAX_STEPS = 4          # per sub-question, so keep this lower than before
MAX_SUBQUESTIONS = 4   # cap so a run can't explode in cost/time

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


# ---- METRICS: lightweight run tracking for evaluation ----
class RunMetrics:
    def __init__(self):
        self.start_time = None
        self.model_calls = 0
        self.search_calls = 0
        self.fallback_events = 0   # times we had to switch away from the primary model
        self.retry_events = 0      # times we retried the same model after a 503
        self.subquestions = 0

    def start(self):
        self.start_time = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self.start_time

    def summary(self) -> str:
        return (
            f"\n--- Run metrics ---\n"
            f"Total time:        {self.elapsed():.1f}s\n"
            f"Sub-questions:     {self.subquestions}\n"
            f"Model calls:       {self.model_calls}\n"
            f"Search calls:      {self.search_calls}\n"
            f"Fallback switches: {self.fallback_events}\n"
            f"Same-model retries:{self.retry_events}\n"
        )


metrics = RunMetrics()

SYSTEM = (
    "You are a research assistant. Use the search_web tool to find current, "
    "factual information before answering. Cite source URLs in your answer."
)

search_decl = types.FunctionDeclaration(
    name="search_web",
    description="Search the web for current information on a topic.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "The search query"}},
        "required": ["query"],
    },
)

config = types.GenerateContentConfig(
    system_instruction=SYSTEM,
    tools=[types.Tool(function_declarations=[search_decl])],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)

# A separate config for plain text tasks (planning, synthesis) with NO tools
plain_config = types.GenerateContentConfig(system_instruction=SYSTEM)


def search_web(**kwargs) -> str:
    # The model should send `query` (a single string), per our schema below.
    # Some runs send `queries` (a list) instead -- handle both so one
    # mismatched argument name doesn't waste a full step of the loop.
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


def call_model(contents, use_tools=True):
    cfg = config if use_tools else plain_config
    models = (MODEL, *FALLBACK_MODELS)
    last_error = None

    for model_index, model in enumerate(models):
        for attempt in range(MODEL_ATTEMPTS):
            try:
                metrics.model_calls += 1
                return client.models.generate_content(model=model, contents=contents, config=cfg)
            except errors.ServerError as e:
                last_error = e
                if attempt + 1 < MODEL_ATTEMPTS:
                    wait = 2 ** attempt * 2
                    print(f"{model} is busy ({e.code}), retrying in {wait}s...")
                    metrics.retry_events += 1
                    time.sleep(wait)
                elif model_index + 1 < len(models):
                    print(f"{model} is still unavailable; trying {models[model_index + 1]}...")
                    metrics.fallback_events += 1
            except errors.ClientError as e:
                if e.code != 429:
                    raise
                last_error = e
                if model_index + 1 < len(models):
                    print(f"{model} quota exhausted (429); trying {models[model_index + 1]}...")
                    metrics.fallback_events += 1
                    break

    raise RuntimeError(f"All configured Gemini models failed: {', '.join(models)}") from last_error


# ---- STEP 1: PLAN ----
def plan_subquestions(topic: str) -> list[str]:
    prompt = (
        f"Break this research topic into {MAX_SUBQUESTIONS} focused sub-questions "
        f"that together would give a complete picture. Topic: \"{topic}\"\n\n"
        "Respond with ONLY a JSON array of strings, nothing else. "
        "Example: [\"question 1\", \"question 2\"]"
    )
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    response = call_model(contents, use_tools=False)

    text = response.text.strip()
    # Models sometimes wrap JSON in ```json fences despite instructions — strip them
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()

    try:
        questions = json.loads(text)
        return questions[:MAX_SUBQUESTIONS]
    except json.JSONDecodeError:
        print("Planner didn't return clean JSON, falling back to the topic as-is.")
        return [topic]


# ---- STEP 2: RESEARCH (this is your Phase 1 loop, reused per sub-question) ----
def research_subquestion(question: str) -> str:
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]

    for step in range(MAX_STEPS):
        response = call_model(contents, use_tools=True)
        contents.append(response.candidates[0].content)

        if not response.function_calls:
            return response.text

        result_parts = []
        for fc in response.function_calls:
            print(f"    [searching] {dict(fc.args)}")
            try:
                output = TOOL_FUNCTIONS[fc.name](**fc.args)
            except Exception as e:
                output = f"Tool error: {e}"
            result_parts.append(types.Part.from_function_response(name=fc.name, response={"result": output}))

        contents.append(types.Content(role="user", parts=result_parts))

    return "Could not find a complete answer within the step limit."


# ---- STEP 3: SYNTHESIZE ----
def synthesize_report(topic: str, findings: dict[str, str]) -> str:
    findings_text = "\n\n".join(f"Sub-question: {q}\nFindings: {a}" for q, a in findings.items())
    prompt = (
        f"Write a well-organized research report on: \"{topic}\"\n\n"
        f"Base it on these findings from sub-research:\n\n{findings_text}\n\n"
        "Structure it with headings, synthesize overlapping points instead of repeating them, "
        "and preserve source URLs as citations."
    )
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    response = call_model(contents, use_tools=False)
    return response.text


# ---- ORCHESTRATOR ----
def run_research_agent(topic: str) -> str:
    metrics.start()
    print(f"\nPlanning sub-questions for: {topic}\n")
    subquestions = plan_subquestions(topic)
    metrics.subquestions = len(subquestions)
    for i, q in enumerate(subquestions, 1):
        print(f"  {i}. {q}")

    findings = {}
    for i, q in enumerate(subquestions, 1):
        print(f"\nResearching ({i}/{len(subquestions)}): {q}")
        findings[q] = research_subquestion(q)

    print("\nSynthesizing final report...\n")
    report = synthesize_report(topic, findings)
    return report + metrics.summary()


if __name__ == "__main__":
    topic = input("Enter a research topic: ")
    print("\n" + run_research_agent(topic))