from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

from src.orchestrator.supervisor import Supervisor
from src.memory.db import get_recent_reports

app = FastAPI(title="Quorum API")

# Allow CORS for the Vite frontend (which usually runs on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store supervisors in memory temporarily for the 2-step process
# Key: topic string, Value: Supervisor instance
active_sessions = {}

class PlanRequest(BaseModel):
    topic: str

class ExecuteRequest(BaseModel):
    topic: str
    custom_subquestions: list[str]

@app.post("/api/plan")
async def generate_plan(request: PlanRequest):
    """
    Step 1: Generates the initial plan using the Planner Agent.
    """
    try:
        supervisor = Supervisor(request.topic)
        active_sessions[request.topic] = supervisor
        
        # We run this in a thread since it's currently sync
        plan_list = await asyncio.to_thread(supervisor.plan_research)
        return {"subquestions": plan_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute")
async def execute_research(request: Request):
    """
    Step 2: Executes the research using the pre-planned questions.
    Returns a Server-Sent Events (SSE) stream of agent progress and final report.
    """
    body = await request.json()
    topic = body.get("topic")
    custom_subs = body.get("custom_subquestions", [])
    
    supervisor = active_sessions.get(topic)
    if not supervisor:
        raise HTTPException(status_code=400, detail="No active planning session for this topic. Plan first.")

    # Override the plan with user-curated subquestions
    supervisor.plan = custom_subs

    async def event_generator():
        try:
            # supervisor.execute_research_async() is a sync generator yielding events
            # We wrap it to yield SSE formatted data
            for event in supervisor.execute_research_async():
                yield {
                    "event": "agent_log",
                    "data": json.dumps(event)
                }
                await asyncio.sleep(0.01) # Yield control to let stream flush
            
            # When done, clear session
            if topic in active_sessions:
                del active_sessions[topic]

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
            
    return EventSourceResponse(event_generator())

@app.get("/api/history")
async def get_history():
    """Fetches past research from SQLite."""
    try:
        records = get_recent_reports()
        return {"history": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
