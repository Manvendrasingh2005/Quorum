"""
Phase 1: A minimal tool-calling agent loop (no frameworks).

Setup:
    pip install anthropic tavily-python
    export ANTHROPIC_API_KEY="your-key"
    export TAVILY_API_KEY="your-key"     # free tier at tavily.com

Run:
    python agent.py
"""
import os
import json
import anthropic
from tavily import TavilyClient

MODEL = "claude-sonnet-5"   # swap for any current Claude model
MAX_STEPS = 6               # safety limit so the loop can never run forever

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

SYSTEM = (
    "You are a research assistant. Use the search_web tool to find current, "
    "factual information before answering. Cite source URLs in your answer."
)

# 1) TOOL DEFINITION: this is what the model "sees". It never runs your code,
#    it only decides to request a call using this schema.
TOOLS = [
    {
        "name": "search_web",
        "description": "Search the web for current information on a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    }
]


# 2) TOOL IMPLEMENTATION: the real Python function that runs on your machine.
def search_web(query: str) -> str:
    results = tavily.search(query=query, max_results=5)
    slim = [
        {"title": r["title"], "url": r["url"], "content": r["content"]}
        for r in results["results"]
    ]
    return json.dumps(slim)


TOOL_FUNCTIONS = {"search_web": search_web}


# 3) THE AGENT LOOP
def run_agent(question: str) -> str:
    messages = [{"role": "user", "content": question}]

    for step in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        # Keep the model's full reply in the history (memory = the messages list)
        messages.append({"role": "assistant", "content": response.content})

        # If the model didn't ask for a tool, it's done: return the final answer
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        # Otherwise, run every tool the model requested and report the results
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[step {step + 1}] calling {block.name}({block.input})")
                try:
                    output = TOOL_FUNCTIONS[block.name](**block.input)
                    is_error = False
                except Exception as e:
                    output, is_error = f"Tool error: {e}", True
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,  # must match the request's id
                        "content": output,
                        "is_error": is_error,
                    }
                )

        # Tool results go back as a "user" message, then the loop repeats
        messages.append({"role": "user", "content": tool_results})

    return "Stopped: reached max steps without a final answer."


if __name__ == "__main__":
    q = input("Ask a research question: ")
    print("\n" + run_agent(q))