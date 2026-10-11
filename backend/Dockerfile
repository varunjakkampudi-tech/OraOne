# syntax=docker/dockerfile:1

# ---- Build stage: install Python deps into an isolated venv ----
FROM python:3.11-slim AS builder

WORKDIR /build

# Build tools needed for a couple of compiled deps (psycopg2, cryptography).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage: slim image, no compilers, non-root user ----
FROM python:3.11-slim AS runtime

# Only the shared library pgvector/psycopg2 need at runtime (not the -dev headers).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 oraone \
    && useradd --uid 1000 --gid oraone --shell /bin/bash --create-home oraone

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --chown=oraone:oraone . .

USER oraone

ARG APP_VERSION=v1.0.0
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.title="oraone-backend" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.description="OraOne Chat Platform — FastAPI backend"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health/ready || exit 1

# Run migrations then start the API under Gunicorn (supervises a pool of
# Uvicorn workers — auto-restarts a crashed worker, bounds hung-request
# impact via timeout, recycles workers periodically; see gunicorn.conf.py).
# Docker/Kubernetes/ECS still own the *container* lifecycle (restarts,
# rolling deploys) — Gunicorn owns process supervision inside it.
CMD ["sh", "-c", "alembic upgrade head && gunicorn server:app -c gunicorn.conf.py"]
