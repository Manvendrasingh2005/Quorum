"""Structured logging, OpenTelemetry-compatible tracing, and runtime metrics for Quorum."""

import time
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from threading import Lock
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class JSONFormatter(logging.Formatter):
    """Custom logging formatter that emits JSON lines for log aggregators (Datadog, Grafana, CloudWatch)."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "quorum-ai",
        }

        # Include custom structured attributes if provided
        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread", "threadName",
            }:
                log_payload[key] = value

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, default=str)

def get_structured_logger(name: str = "quorum") -> logging.Logger:
    """Creates a preconfigured logger emitting structured JSON events."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

structured_logger = get_structured_logger("quorum.telemetry")

class TelemetryStore:
    """Thread-safe in-memory metrics and telemetry registry."""

    def __init__(self):
        self._lock = Lock()
        self.start_time = time.time()
        self.total_requests = 0
        self.http_status_codes: Dict[int, int] = {}
        self.total_jobs_created = 0
        self.total_jobs_completed = 0
        self.total_jobs_failed = 0
        self.critic_evaluations = 0
        self.critic_rejections = 0
        self.critic_approvals = 0
        self.agent_runs: Dict[str, int] = {
            "Planner": 0,
            "Researcher": 0,
            "Critic": 0,
            "Writer": 0,
        }
        self.agent_total_duration_ms: Dict[str, float] = {
            "Planner": 0.0,
            "Researcher": 0.0,
            "Critic": 0.0,
            "Writer": 0.0,
        }

    def record_request(self, status_code: int):
        with self._lock:
            self.total_requests += 1
            self.http_status_codes[status_code] = self.http_status_codes.get(status_code, 0) + 1

    def record_job_created(self):
        with self._lock:
            self.total_jobs_created += 1

    def record_job_completed(self, success: bool = True):
        with self._lock:
            if success:
                self.total_jobs_completed += 1
            else:
                self.total_jobs_failed += 1

    def record_critic_verdict(self, is_approval: bool):
        with self._lock:
            self.critic_evaluations += 1
            if is_approval:
                self.critic_approvals += 1
            else:
                self.critic_rejections += 1

    def record_agent_span(self, agent_name: str, duration_ms: float):
        with self._lock:
            normalized_name = "Researcher" if "Researcher" in agent_name else agent_name
            if normalized_name in self.agent_runs:
                self.agent_runs[normalized_name] += 1
                self.agent_total_duration_ms[normalized_name] += duration_ms

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            uptime_seconds = int(time.time() - self.start_time)
            rejection_rate = (
                round((self.critic_rejections / self.critic_evaluations) * 100, 2)
                if self.critic_evaluations > 0
                else 0.0
            )

            agent_metrics = {}
            for agent, count in self.agent_runs.items():
                total_ms = self.agent_total_duration_ms[agent]
                avg_ms = round(total_ms / count, 1) if count > 0 else 0.0
                agent_metrics[agent] = {
                    "runs": count,
                    "avg_latency_ms": avg_ms,
                    "total_latency_ms": round(total_ms, 1),
                }

            return {
                "uptime_seconds": uptime_seconds,
                "uptime_human": f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s",
                "http_requests": {
                    "total": self.total_requests,
                    "status_distribution": self.http_status_codes,
                },
                "research_jobs": {
                    "created": self.total_jobs_created,
                    "completed": self.total_jobs_completed,
                    "failed": self.total_jobs_failed,
                    "active": max(0, self.total_jobs_created - (self.total_jobs_completed + self.total_jobs_failed)),
                },
                "critic_audits": {
                    "total_evaluations": self.critic_evaluations,
                    "approvals": self.critic_approvals,
                    "rejections": self.critic_rejections,
                    "rejection_rate_percent": rejection_rate,
                },
                "agent_telemetry": agent_metrics,
            }

telemetry_store = TelemetryStore()

def get_telemetry_metrics() -> Dict[str, Any]:
    """Exposes structured runtime metrics snapshot for API clients."""
    return telemetry_store.snapshot()

class AgentSpan:
    """Context manager for tracing agent execution duration, errors, and emitting telemetry spans."""

    def __init__(self, agent: str, trace_id: Optional[str] = None, topic: Optional[str] = None):
        self.agent = agent
        self.trace_id = trace_id or str(uuid.uuid4())
        self.topic = topic
        self.start_time: float = 0.0
        self.duration_ms: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        structured_logger.info(
            f"Agent span started: {self.agent}",
            extra={
                "event": "agent_start",
                "agent": self.agent,
                "trace_id": self.trace_id,
                "topic": self.topic,
            },
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000.0
        telemetry_store.record_agent_span(self.agent, self.duration_ms)

        if exc_type is not None:
            structured_logger.error(
                f"Agent span failed: {self.agent} ({str(exc_val)})",
                extra={
                    "event": "agent_failure",
                    "agent": self.agent,
                    "trace_id": self.trace_id,
                    "latency_ms": round(self.duration_ms, 2),
                    "error": str(exc_val),
                },
            )
        else:
            structured_logger.info(
                f"Agent span completed: {self.agent} in {self.duration_ms:.1f}ms",
                extra={
                    "event": "agent_complete",
                    "agent": self.agent,
                    "trace_id": self.trace_id,
                    "latency_ms": round(self.duration_ms, 2),
                },
            )

class TelemetryMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware that logs HTTP requests with structured JSON and X-Correlation-ID."""

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        start_time = time.perf_counter()

        response: Optional[Response] = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            telemetry_store.record_request(500)
            structured_logger.error(
                f"{request.method} {request.url.path} - 500 Internal Error ({str(exc)})",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "latency_ms": round(duration_ms, 2),
                    "trace_id": trace_id,
                    "error": str(exc),
                },
            )
            raise exc

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        telemetry_store.record_request(status_code)

        # Skip spamming logs for frequent health checks
        if request.url.path != "/api/health":
            structured_logger.info(
                f"{request.method} {request.url.path} - {status_code} ({duration_ms:.1f}ms)",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": round(duration_ms, 2),
                    "trace_id": trace_id,
                },
            )

        response.headers["x-correlation-id"] = trace_id
        return response
