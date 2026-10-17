from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import asyncio
import json
import os
import sys
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

import time
from collections import defaultdict
import jwt

# Optional Supabase JWT secret for cryptographic verification (defaults to claims extraction if unset)
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

class SimpleRateLimiter:
    """Sliding-window in-memory rate limiter per user/client IP."""
    def __init__(self):
        self.requests = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, key: str, max_requests: int, window_seconds: int = 60):
        now = time.time()
        async with self._lock:
            # Prune timestamps older than window
            self.requests[key] = [t for t in self.requests[key] if now - t < window_seconds]
            if len(self.requests[key]) >= max_requests:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded: maximum {max_requests} requests per {window_seconds}s."
                )
            self.requests[key].append(now)

rate_limiter = SimpleRateLimiter()

async def get_current_user_id(request: Request) -> str:
    """Extract and validate user ID from Bearer token or query param, or fallback to client IP identifier."""
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif request.query_params.get("token"):
        token = request.query_params.get("token").strip()

    if token:
        try:
            if SUPABASE_JWT_SECRET:
                payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
                return payload.get("sub", "authenticated_user")
            else:
                payload = jwt.decode(token, options={"verify_signature": False})
                return payload.get("sub", "authenticated_user")
        except Exception as e:
            print(f"[Auth] JWT token decoding warning: {e}")
    client_ip = request.client.host if request.client else "unknown"
    return f"anon_{client_ip}"

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
async def generate_plan(request: Request, body: PlanRequest):
    """
    Step 1: Generates the initial plan using the Planner Agent.
    Guarded by user-scoped rate limiting.
    """
    user_id = await get_current_user_id(request)
    await rate_limiter.check(f"plan_{user_id}", max_requests=10, window_seconds=60)
    try:
        supervisor = Supervisor(user_id=user_id)
        
        # We run this in a thread since it's currently sync
        plan_list = await asyncio.to_thread(supervisor.plan_research, body.topic, getattr(body, 'base64_image', None))
        return {"subquestions": plan_list}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute")
async def execute_research(request: Request):
    """
    Step 2: Executes the research using the pre-planned questions.
    Returns a Server-Sent Events (SSE) stream of agent progress, live tokens, and final report.
    """
    user_id = await get_current_user_id(request)
    await rate_limiter.check(f"execute_{user_id}", max_requests=5, window_seconds=60)

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

    def on_chunk_callback(chunk: str):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "report_chunk", "chunk": chunk})
        except Exception:
            pass

    async def event_generator():
        supervisor = Supervisor(
            on_status=on_status_callback,
            on_report_chunk=on_chunk_callback,
            user_id=user_id
        )

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
                if msg.get("type") == "report_chunk":
                    yield {
                        "event": "report_chunk",
                        "data": json.dumps({"chunk": msg["chunk"]}),
                    }
                elif msg.get("type") == "done":
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

    user_id = await get_current_user_id(request)
    await rate_limiter.check(f"stream_{user_id}", max_requests=5, window_seconds=60)

    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_status_callback(msg: str):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, msg)
        except Exception:
            pass

    def on_chunk_callback(chunk: str):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "report_chunk", "chunk": chunk})
        except Exception:
            pass

    async def event_generator():
        supervisor = Supervisor(
            on_status=on_status_callback,
            on_report_chunk=on_chunk_callback,
            user_id=user_id
        )

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
                if msg.get("type") == "report_chunk":
                    yield {
                        "event": "report_chunk",
                        "data": json.dumps({"chunk": msg["chunk"]}),
                    }
                elif msg.get("type") == "done":
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
async def get_history(request: Request):
    """Fetches past research from SQLite with multi-tenant user isolation."""
    user_id = await get_current_user_id(request)
    try:
        # If user is authenticated, isolate history to their user_id
        filter_user = user_id if not user_id.startswith("anon_") else None
        records = get_recent_reports(user_id=filter_user)
        return {"history": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PDFRequest(BaseModel):
    topic: str
    markdown_report: str

@app.post("/api/export_pdf")
async def export_pdf(request: Request, body: PDFRequest):
    """Converts a markdown report string into a PDF and returns it."""
    user_id = await get_current_user_id(request)
    await rate_limiter.check(f"pdf_{user_id}", max_requests=10, window_seconds=60)

    import io
    import markdown as md
    from xhtml2pdf import pisa
    from fastapi.responses import Response

    html_content = md.markdown(body.markdown_report, extensions=['tables'])
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
            <p><b>Topic</b>: {body.topic}</p>
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
