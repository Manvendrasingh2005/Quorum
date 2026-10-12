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
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_status_message(msg: str) -> dict:
    """Classifies log messages by agent and flags critic verification loops."""
    msg_str = str(msg).strip()
    agent = "System"
    is_rejection = False
    is_approval = False

    if "[Planner]" in msg_str or "Planner Agent" in msg_str or "planning:" in msg_str.lower():
        agent = "Planner"
    elif "[Critic]" in msg_str or "Critic" in msg_str:
        agent = "Critic"
        if "REJECTED" in msg_str or "❌" in msg_str:
            is_rejection = True
        elif "APPROVED" in msg_str or "✅" in msg_str:
            is_approval = True
    elif "[Researcher]" in msg_str or "Researcher" in msg_str or "search" in msg_str.lower() or "arxiv" in msg_str.lower():
        agent = "Researcher"
    elif "[Writer]" in msg_str or "Writer Agent" in msg_str or "synthesiz" in msg_str.lower():
        agent = "Writer"
    elif "[Supervisor]" in msg_str:
        agent = "Supervisor"

    return {
        "agent": agent,
        "status": msg_str,
        "is_rejection": is_rejection,
        "is_approval": is_approval,
    }

# Store supervisors in memory temporarily for the 2-step process
active_sessions = {}

class PlanRequest(BaseModel):
    topic: str
    base64_image: str | None = None

class ExecuteRequest(BaseModel):
    topic: str
    custom_subquestions: list[str]

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify backend connectivity."""
    return {"status": "ok", "app": "Quorum API", "version": "1.0.0"}

@app.post("/api/plan")
async def generate_plan(request: PlanRequest):
    """
    Step 1: Generates the initial plan using the Planner Agent.
    """
    try:
        supervisor = Supervisor()
        
        # We run this in a thread since it's currently sync
        plan_list = await asyncio.to_thread(supervisor.plan_research, request.topic, getattr(request, 'base64_image', None))
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
    loop = asyncio.get_running_loop()

    def on_status_callback(msg: str):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, msg)
        except Exception:
            pass

    async def event_generator():
        supervisor = Supervisor(on_status=on_status_callback)

        def run_sync():
            try:
                res = supervisor.execute_research_async(topic, custom_subs)
                loop.call_soon_threadsafe(queue.put_nowait, {
                    "type": "done", 
                    "report": res.report,
                    "metrics": res.metrics,
                    "findings": [f.model_dump() for f in res.findings]
                })
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(e)})

        # Start execution in a background thread
        loop.run_in_executor(None, run_sync)

        while True:
            msg = await queue.get()
            if isinstance(msg, dict):
                if msg.get("type") == "done":
                    yield {
                        "event": "agent_log",
                        "data": json.dumps({
                            "type": "done",
                            "report": msg["report"],
                            "metrics": msg["metrics"],
                            "findings": msg["findings"],
                        }),
                    }
                    break
                elif msg.get("type") == "error":
                    yield {"event": "error", "data": json.dumps({"error": msg["error"]})}
                    break
            else:
                parsed = parse_status_message(msg)
                yield {"event": "agent_log", "data": json.dumps(parsed)}
                
    return EventSourceResponse(event_generator())

@app.get("/api/stream")
async def stream_research_get(topic: str, request: Request):
    """
    GET SSE stream: Plans and executes end-to-end multi-agent research.
    Enables native EventSource in browsers without requiring POST fetch streaming.
    """
    if not topic:
        raise HTTPException(status_code=400, detail="Missing topic query parameter")

    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_status_callback(msg: str):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, msg)
        except Exception:
            pass

    async def event_generator():
        supervisor = Supervisor(on_status=on_status_callback)

        def run_sync():
            try:
                res = supervisor.run_async(topic)
                loop.call_soon_threadsafe(queue.put_nowait, {
                    "type": "done",
                    "report": res.report,
                    "metrics": res.metrics,
                    "findings": [f.model_dump() for f in res.findings],
                })
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(e)})

        loop.run_in_executor(None, run_sync)

        while True:
            msg = await queue.get()
            if isinstance(msg, dict):
                if msg.get("type") == "done":
                    yield {
                        "event": "agent_log",
                        "data": json.dumps({
                            "type": "done",
                            "report": msg["report"],
                            "metrics": msg["metrics"],
                            "findings": msg["findings"],
                        }),
                    }
                    break
                elif msg.get("type") == "error":
                    yield {"event": "error", "data": json.dumps({"error": msg["error"]})}
                    break
            else:
                parsed = parse_status_message(msg)
                yield {"event": "agent_log", "data": json.dumps(parsed)}

    return EventSourceResponse(event_generator())

@app.get("/api/history")
async def get_history():
    """Fetches past research from SQLite."""
    try:
        records = get_recent_reports()
        return {"history": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PDFRequest(BaseModel):
    topic: str
    markdown_report: str

@app.post("/api/export_pdf")
async def export_pdf(request: PDFRequest):
    """Converts a markdown report string into a PDF and returns it."""
    import io
    import markdown as md
    from xhtml2pdf import pisa
    from fastapi.responses import Response

    html_content = md.markdown(request.markdown_report, extensions=['tables'])
    styled_html = f"""
    <html>
        <head>
            <style>
                @page {{ margin: 2cm; }}
                body {{ font-family: Helvetica, Arial, sans-serif; font-size: 12pt; color: #333; }}
                h1 {{ color: #1f6feb; border-bottom: 2px solid #ccc; padding-bottom: 5px; }}
                h2, h3 {{ color: #0d1117; margin-top: 20px; }}
                p {{ line-height: 1.6; }}
                li {{ margin-bottom: 8px; }}
                code {{ background-color: #f6f8fa; padding: 2px 4px; border-radius: 4px; font-family: Courier, monospace; }}
            </style>
        </head>
        <body>
            <h1>Quorum AI Research Report</h1>
            <p><b>Topic</b>: {request.topic}</p>
            <hr>
            {html_content}
        </body>
    </html>
    """
    pdf_buf = io.BytesIO()
    pisa.CreatePDF(styled_html, dest=pdf_buf)
    
    return Response(
        content=pdf_buf.getvalue(), 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=Quorum_Report.pdf"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
