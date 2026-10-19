# ==============================================================================
# Quorum AI Multi-Agent Platform - Production Backend Dockerfile
# Multi-stage lightweight, security-hardened Python 3.11 image
# ==============================================================================

# Stage 1: Build & wheels generation
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Stage 2: Final Runtime
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install pre-compiled wheels from builder
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Create dedicated non-root security user
RUN groupadd -g 1001 quorum && \
    useradd -u 1001 -g quorum -s /bin/bash -m quorum && \
    mkdir -p /app/.chroma_db /app/data && \
    chown -R quorum:quorum /app

# Copy application code with proper ownership
COPY --chown=quorum:quorum . .

USER quorum

EXPOSE 8000

# Native Python container healthcheck against /api/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; sys_exit = 0 if urllib.request.urlopen('http://localhost:8000/api/health').getcode() == 200 else 1; exit(sys_exit)"

# Launch Uvicorn ASGI server with production concurrency
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
