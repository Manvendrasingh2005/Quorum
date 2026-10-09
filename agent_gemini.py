from dotenv import load_dotenv; load_dotenv()
import os
import json
import time
from google import genai
from google.genai import types, errors
from tavily import TavilyClient

MODEL = "gemini-3.8-flash"  # confirmed available via models.list()
FALLBACK_MODELS = (
    "gemini-flash-lite-latest",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
)
MODEL_ATTEMPTS = 2
MAX_STEPS = 6               # safety limit so the loop can never run forever

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

SYSTEM = (
    "You are a research assistant. Use the search_web tool to find current, "
    "factual information before answering. Cite source URLs in your answer."
)

# 1) TOOL DEFINITION: what the model "sees". It only requests calls, never runs code.
search_decl = types.FunctionDeclaration(
    name="search_web",
    description="Search the web for current information on a topic.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"}
        },
        "required": ["query"],
    },
)

# Turn OFF automatic function calling so YOU control the loop
config = types.GenerateContentConfig(
    system_instruction=SYSTEM,
    tools=[types.Tool(function_declarations=[search_decl])],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)


# 2) TOOL IMPLEMENTATION: the real Python function that runs on your machine.
def search_web(query: str) -> str:
    results = tavily.search(query=query, max_results=5)
    slim = [
        {"title": r["title"], "url": r["url"], "content": r["content"]}
        for r in results["results"]
    ]
    return json.dumps(slim)


TOOL_FUNCTIONS = {"search_web": search_web}


# 3) RETRY WRAPPER: handles "server busy" errors with exponential backoff
def call_model(contents):
    models = (MODEL, *FALLBACK_MODELS)
    last_error = None

    for model_index, model in enumerate(models):
        for attempt in range(MODEL_ATTEMPTS):
            try:
                return client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except errors.ServerError as e:
                last_error = e
                if attempt + 1 < MODEL_ATTEMPTS:
                    wait = 2 ** attempt * 2
                    print(
                        f"{model} is busy ({e.code}), "
                        f"retrying in {wait}s..."
                    )
                    time.sleep(wait)
                elif model_index + 1 < len(models):
                    print(f"{model} is still unavailable; trying {models[model_index + 1]}...")
            except errors.ClientError as e:
                if e.code != 429:
                    raise
                last_error = e
                if model_index + 1 < len(models):
                    print(
                        f"{model} quota exhausted (429); "
                        f"trying {models[model_index + 1]}..."
                    )
                    break

    raise RuntimeError(
        "All configured Gemini models failed or exhausted their quota: "
        f"{', '.join(models)}"
    ) from last_error


# 4) THE AGENT LOOP
def run_agent(question: str) -> str:
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]

    for step in range(MAX_STEPS):
        response = call_model(contents)

        contents.append(response.candidates[0].content)

        # No tool requested -> this is the final answer
        if not response.function_calls:
            return response.text

        # Otherwise run each requested tool and send the results back
        result_parts = []
        for fc in response.function_calls:
            print(f"[step {step + 1}] calling {fc.name}({dict(fc.args)})")
            try:
                output = TOOL_FUNCTIONS[fc.name](**fc.args)
            except Exception as e:
                output = f"Tool error: {e}"
            result_parts.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": output}
                )
            )

        contents.append(types.Content(role="user", parts=result_parts))

    return "Stopped: reached max steps without a final answer."


if __name__ == "__main__":
    q = input("Ask a research question: ")
    print("\n" + run_agent(q))