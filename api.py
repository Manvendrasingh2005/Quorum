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
from src.orchestrator.job_manager import job_manager, parse_agent_log
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
    depth: str = "standard"

class ExecuteRequest(BaseModel):
    topic: str
    custom_subquestions: list[str]
    depth: str = "standard"

class CreateJobRequest(BaseModel):
    topic: str
    custom_subquestions: list[str] | None = None
    depth: str = "standard"

class VerifyCitationsRequest(BaseModel):
    urls: list[str]

class DocxRequest(BaseModel):
    topic: str
    markdown_report: str

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify backend connectivity."""
    return {"status": "ok", "app": "Quorum API", "version": "1.0.0"}

@app.post("/api/plan")
async def generate_plan(request: Request, body: PlanRequest):
    """
    Step 1: Generates the initial plan using the Planner Agent based on depth.
    Guarded by user-scoped rate limiting.
    """
    user_id = await get_current_user_id(request)
    await rate_limiter.check(f"plan_{user_id}", max_requests=10, window_seconds=60)
    try:
        supervisor = Supervisor(user_id=user_id)
        
        # We run this in a thread since it's currently sync
        plan_list = await asyncio.to_thread(
            supervisor.plan_research,
            body.topic,
            getattr(body, 'base64_image', None),
            depth=body.depth,
        )
        return {"subquestions": plan_list}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs", status_code=202)
async def create_research_job(request: Request, body: CreateJobRequest):
    """
    Asynchronously registers and starts a background research execution job.
    Returns 202 Accepted with job_id for reconnectable SSE streaming.
    """
    user_id = await get_current_user_id(request)
    await rate_limiter.check(f"execute_{user_id}", max_requests=5, window_seconds=60)

    if not body.topic:
        raise HTTPException(status_code=400, detail="Missing research topic")

    job = await job_manager.create_job(
        topic=body.topic,
        custom_subquestions=body.custom_subquestions,
        user_id=user_id,
        depth=body.depth,
    )
    loop = asyncio.get_running_loop()
    job_manager.start_job(job.job_id, loop)
    return {"job_id": job.job_id, "status": job.status, "topic": job.topic, "depth": job.depth}

@app.get("/api/jobs/{job_id}/stream")
async def stream_job_events(job_id: str, request: Request, last_event_id: int | None = None):
    """
    Streams Server-Sent Events (SSE) for a research job.
    Supports seamless reconnection and replay via Last-Event-ID header or query param.
    """
    header_last_id = request.headers.get("Last-Event-ID")
    resolved_last_id = 0
    if header_last_id and header_last_id.isdigit():
        resolved_last_id = int(header_last_id)
    elif last_event_id is not None:
        resolved_last_id = last_event_id
    elif request.query_params.get("last_event_id") and request.query_params.get("last_event_id").isdigit():
        resolved_last_id = int(request.query_params.get("last_event_id"))

    async def event_generator():
        async for ev in job_manager.subscribe(job_id, last_event_id=resolved_last_id):
            yield {
                "id": ev.get("id"),
                "event": ev.get("event"),
                "data": ev.get("data")
            }

    return EventSourceResponse(event_generator())

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Inspects research job status, metrics, findings, and completion report."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "topic": job.topic,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "result": job.result,
        "error": job.error,
        "event_count": len(job.events),
    }

@app.post("/api/execute")
async def execute_research(request: Request):
    """
    Step 2: Executes the research using the pre-planned questions.
    Returns a Server-Sent Events (SSE) stream of agent progress, live tokens, and final report.
    Buffered and reconnectable via JobManager.
    """
    user_id = await get_current_user_id(request)
    await rate_limiter.check(f"execute_{user_id}", max_requests=5, window_seconds=60)

    body = await request.json()
    topic = body.get("topic")
    custom_subs = body.get("custom_subquestions", [])
    
    if not topic or not custom_subs:
        raise HTTPException(status_code=400, detail="Missing topic or subquestions")

    header_last_id = request.headers.get("Last-Event-ID")
    resolved_last_id = 0
    if header_last_id and header_last_id.isdigit():
        resolved_last_id = int(header_last_id)
    elif request.query_params.get("last_event_id") and request.query_params.get("last_event_id").isdigit():
        resolved_last_id = int(request.query_params.get("last_event_id"))

    depth = body.get("depth", "standard")
    job_id = body.get("job_id") or request.query_params.get("job_id")
    job = job_manager.get_job(job_id) if job_id else None

    if not job:
        job = await job_manager.create_job(topic=topic, custom_subquestions=custom_subs, user_id=user_id, depth=depth)
        loop = asyncio.get_running_loop()
        job_manager.start_job(job.job_id, loop)

    async def event_generator():
        async for ev in job_manager.subscribe(job.job_id, last_event_id=resolved_last_id):
            yield {
                "id": ev.get("id"),
                "event": ev.get("event"),
                "data": ev.get("data")
            }

    return EventSourceResponse(event_generator())

@app.get("/api/stream")
async def stream_research_get(topic: str, request: Request, job_id: str | None = None, depth: str = "standard"):
    """
    GET SSE stream: Plans and executes end-to-end multi-agent research.
    Enables native EventSource in browsers with buffered event replayability.
    """
    if not topic:
        raise HTTPException(status_code=400, detail="Missing topic query parameter")

    user_id = await get_current_user_id(request)
    await rate_limiter.check(f"stream_{user_id}", max_requests=5, window_seconds=60)

    header_last_id = request.headers.get("Last-Event-ID")
    resolved_last_id = 0
    if header_last_id and header_last_id.isdigit():
        resolved_last_id = int(header_last_id)
    elif request.query_params.get("last_event_id") and request.query_params.get("last_event_id").isdigit():
        resolved_last_id = int(request.query_params.get("last_event_id"))

    job = job_manager.get_job(job_id) if job_id else None
    if not job:
        job = await job_manager.create_job(topic=topic, custom_subquestions=None, user_id=user_id, depth=depth)
        loop = asyncio.get_running_loop()
        job_manager.start_job(job.job_id, loop)

    async def event_generator():
        async for ev in job_manager.subscribe(job.job_id, last_event_id=resolved_last_id):
            yield {
                "id": ev.get("id"),
                "event": ev.get("event"),
                "data": ev.get("data")
            }

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

@app.post("/api/verify_citations")
async def verify_citations(request: Request, body: VerifyCitationsRequest):
    """Concurrently audits cited URLs via HTTP HEAD/GET to verify availability and extract domain metadata."""
    import requests
    from urllib.parse import urlparse

    def check_single_url(url: str):
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.head(url, timeout=3, allow_redirects=True, headers=headers)
            is_live = resp.status_code < 400
            return {
                "url": url,
                "domain": domain,
                "status": "verified" if is_live else "unreachable",
                "status_code": resp.status_code,
            }
        except Exception:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "")
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = requests.get(url, timeout=3, stream=True, headers=headers)
                is_live = resp.status_code < 400
                return {
                    "url": url,
                    "domain": domain,
                    "status": "verified" if is_live else "unreachable",
                    "status_code": resp.status_code,
                }
            except Exception:
                domain = urlparse(url).netloc.replace("www.", "") if urlparse(url).netloc else "source"
                return {
                    "url": url,
                    "domain": domain,
                    "status": "unreachable",
                    "status_code": 0,
                }

    unique_urls = list(dict.fromkeys(body.urls))[:20]
    results = await asyncio.gather(*(asyncio.to_thread(check_single_url, u) for u in unique_urls))
    return {"citations": results}

@app.post("/api/export_docx")
async def export_docx(request: Request, body: DocxRequest):
    """Converts a markdown research report into a professionally formatted Microsoft Word (.docx) document."""
    user_id = await get_current_user_id(request)
    await rate_limiter.check(f"docx_{user_id}", max_requests=10, window_seconds=60)

    import io
    import docx
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from fastapi.responses import Response

    doc = docx.Document()

    # Document Title
    title_heading = doc.add_heading("Quorum AI Research Dossier", level=0)
    title_heading.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Topic Subtitle
    sub_para = doc.add_paragraph()
    sub_run = sub_para.add_run(f"Topic: {body.topic}")
    sub_run.bold = True
    sub_run.font.size = Pt(13)
    sub_run.font.color.rgb = RGBColor(31, 111, 235)

    date_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    meta_para = doc.add_paragraph(f"Synthesized by Quorum Autonomous Multi-Agent Swarm • Date: {date_str}")
    meta_para.runs[0].font.size = Pt(9)
    meta_para.runs[0].font.color.rgb = RGBColor(120, 120, 120)

    doc.add_paragraph("-" * 60)

    # Convert Markdown to structured DOCX sections
    for raw_line in body.markdown_report.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            h = doc.add_heading(line[2:], level=1)
            h.paragraph_format.space_before = Pt(14)
            h.paragraph_format.space_after = Pt(4)
        elif line.startswith("## "):
            h = doc.add_heading(line[3:], level=2)
            h.paragraph_format.space_before = Pt(11)
            h.paragraph_format.space_after = Pt(3)
        elif line.startswith("### "):
            h = doc.add_heading(line[4:], level=3)
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(2)
        elif line.startswith(("- ", "* ")):
            doc.add_paragraph(line[2:], style='List Bullet')
        elif line[:3].replace('.', '').isdigit() and line[2:4] in ('. ', ') '):
            doc.add_paragraph(line[3:], style='List Number')
        else:
            p = doc.add_paragraph(line)
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(5)

    docx_buf = io.BytesIO()
    doc.save(docx_buf)

    clean_topic = "".join(c for c in body.topic[:35] if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    filename = f"Quorum_{clean_topic or 'Report'}.docx"

    return Response(
        content=docx_buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
