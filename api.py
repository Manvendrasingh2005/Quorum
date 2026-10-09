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
        supervisor = Supervisor()
        
        # We run this in a thread since it's currently sync
        plan_list = await asyncio.to_thread(supervisor.plan_research, request.topic)
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
    
    if not topic or not custom_subs:
        raise HTTPException(status_code=400, detail="Missing topic or subquestions")

    queue = asyncio.Queue()

    def on_status_callback(msg: str):
        # Called from synchronous threads, must be threadsafe
        loop = asyncio.get_event_loop()
        try:
            loop.call_soon_threadsafe(queue.put_nowait, msg)
        except Exception:
            pass

    async def event_generator():
        supervisor = Supervisor(on_status=on_status_callback)
        loop = asyncio.get_running_loop()

        def run_sync():
            try:
                res = supervisor.execute_research_async(topic, custom_subs)
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "done", "report": res.report})
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(e)})

        # Start execution in a background thread
        loop.run_in_executor(None, run_sync)

        while True:
            msg = await queue.get()
            if isinstance(msg, dict):
                if msg.get("type") == "done":
                    yield {"event": "agent_log", "data": json.dumps({"report": msg["report"]})}
                    break
                elif msg.get("type") == "error":
                    yield {"event": "error", "data": json.dumps({"error": msg["error"]})}
                    break
            else:
                yield {"event": "agent_log", "data": json.dumps({"agent": "System", "status": msg})}
                
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
