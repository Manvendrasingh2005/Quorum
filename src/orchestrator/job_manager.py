"""
Job Manager — Asynchronous task execution and event buffering engine.

Provides:
- UUID-based asynchronous research job dispatching
- Sliding-window event buffering for SSE stream replayability
- Reconnectable event streams via Last-Event-ID
- Multi-subscriber broadcast architecture (multiple tabs / reconnections)
- Automatic lifecycle management (queued -> running -> completed/failed)
"""
import asyncio
import time
import uuid
import json
from typing import AsyncGenerator
from dataclasses import dataclass, field
from src.orchestrator.supervisor import Supervisor
from src.observability.telemetry import telemetry_store


def parse_agent_log(msg: str) -> dict:
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


@dataclass
class JobEvent:
    id: int
    event: str
    data: str


@dataclass
class ResearchJob:
    job_id: str
    topic: str
    user_id: str = "anonymous"
    custom_subquestions: list[str] | None = None
    depth: str = "standard"
    status: str = "queued"  # queued, running, completed, failed, cancelled
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    events: list[JobEvent] = field(default_factory=list)
    subscribers: set = field(default_factory=set)
    result: dict | None = None
    error: str | None = None
    _event_counter: int = 0


class JobManager:
    """Thread-safe and asyncio-friendly manager for background research execution."""
    def __init__(self, ttl_seconds: int = 7200):
        self.jobs: dict[str, ResearchJob] = {}
        self.ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()

    def get_job(self, job_id: str) -> ResearchJob | None:
        return self.jobs.get(job_id)

    async def create_job(
        self,
        topic: str,
        custom_subquestions: list[str] | None = None,
        user_id: str = "anonymous",
        depth: str = "standard",
    ) -> ResearchJob:
        async with self._lock:
            self._cleanup_stale_jobs()
            job_id = str(uuid.uuid4())
            job = ResearchJob(
                job_id=job_id,
                topic=topic,
                user_id=user_id or "anonymous",
                custom_subquestions=custom_subquestions,
                depth=depth or "standard",
                status="queued",
            )
            self.jobs[job_id] = job
            telemetry_store.record_job_created()
            return job

    def _cleanup_stale_jobs(self):
        now = time.time()
        expired = [
            jid for jid, job in self.jobs.items()
            if now - job.created_at > self.ttl_seconds and job.status in ("completed", "failed", "cancelled")
        ]
        for jid in expired:
            self.jobs.pop(jid, None)

    def _broadcast_event(self, job: ResearchJob, event_name: str, data: str):
        job._event_counter += 1
        event = JobEvent(id=job._event_counter, event=event_name, data=data)
        job.events.append(event)

        # Dispatch to active subscribers
        dead_subscribers = set()
        for q in job.subscribers:
            try:
                q.put_nowait(event)
            except Exception:
                dead_subscribers.add(q)
        job.subscribers.difference_update(dead_subscribers)

    def start_job(self, job_id: str, loop: asyncio.AbstractEventLoop):
        """Dispatches job execution to a background worker thread."""
        job = self.jobs.get(job_id)
        if not job or job.status != "queued":
            return

        job.status = "running"

        def on_status_callback(msg: str):
            parsed = parse_agent_log(msg)
            loop.call_soon_threadsafe(
                self._broadcast_event,
                job,
                "agent_log",
                json.dumps(parsed),
            )

        def on_chunk_callback(chunk: str):
            loop.call_soon_threadsafe(
                self._broadcast_event,
                job,
                "report_chunk",
                json.dumps({"chunk": chunk}),
            )

        def run_worker():
            try:
                supervisor = Supervisor(
                    on_status=on_status_callback,
                    on_report_chunk=on_chunk_callback,
                    user_id=job.user_id,
                )
                if job.custom_subquestions:
                    res = supervisor.execute_research_async(job.topic, job.custom_subquestions, depth=job.depth)
                else:
                    res = supervisor.run_async(job.topic, depth=job.depth)

                result_dict = {
                    "type": "done",
                    "report": res.report,
                    "metrics": res.metrics,
                    "findings": [f.model_dump() for f in res.findings],
                }

                def mark_completed():
                    job.status = "completed"
                    job.completed_at = time.time()
                    job.result = result_dict
                    self._broadcast_event(job, "agent_log", json.dumps(result_dict))
                    telemetry_store.record_job_completed(success=True)

                loop.call_soon_threadsafe(mark_completed)

            except Exception as e:
                def mark_failed(err_msg: str):
                    job.status = "failed"
                    job.completed_at = time.time()
                    job.error = err_msg
                    self._broadcast_event(job, "error", json.dumps({"error": err_msg}))
                    telemetry_store.record_job_completed(success=False)

                loop.call_soon_threadsafe(mark_failed, str(e))

        loop.run_in_executor(None, run_worker)

    async def subscribe(
        self,
        job_id: str,
        last_event_id: int = 0,
    ) -> AsyncGenerator[dict, None]:
        """
        Yields buffered events since last_event_id, then streams live events
        as they occur. Handles client disconnects and reconnections seamlessly.
        """
        job = self.jobs.get(job_id)
        if not job:
            yield {
                "event": "error",
                "data": json.dumps({"error": f"Job {job_id} not found"}),
            }
            return

        # 1. Replay buffered events matching criteria
        for ev in job.events:
            if ev.id > last_event_id:
                yield {
                    "id": str(ev.id),
                    "event": ev.event,
                    "data": ev.data,
                }

        # 2. If the job is already finished, nothing more to stream!
        if job.status in ("completed", "failed", "cancelled"):
            return

        # 3. Register subscriber queue for live events
        q: asyncio.Queue[JobEvent] = asyncio.Queue()
        job.subscribers.add(q)

        try:
            while True:
                ev = await q.get()
                yield {
                    "id": str(ev.id),
                    "event": ev.event,
                    "data": ev.data,
                }
                # Check for completion
                if ev.event == "error":
                    break
                if ev.event == "agent_log":
                    try:
                        parsed = json.loads(ev.data)
                        if parsed.get("type") == "done":
                            break
                    except Exception:
                        pass
        finally:
            job.subscribers.discard(q)


job_manager = JobManager()
