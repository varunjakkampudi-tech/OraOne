"""Gunicorn configuration — process supervision for the FastAPI app.

Replaces bare `uvicorn --workers N` with Gunicorn managing a pool of
Uvicorn worker processes: automatic worker restarts on crash, graceful
reloads, and a single place to tune concurrency/timeouts for production.
Docker still owns the container lifecycle (restart policy, health checks);
Gunicorn owns process-level supervision inside the container.
"""

from __future__ import annotations

import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
worker_class = "uvicorn.workers.UvicornWorker"

# Default to (2 * CPU) + 1, the standard Gunicorn sizing formula, capped at 8
# so a single container doesn't accidentally spawn dozens of DB connections.
_default_workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
workers = int(os.environ.get("GUNICORN_WORKERS", str(_default_workers)))

# Restart a worker if it doesn't finish a request within this many seconds —
# prevents one hung request (e.g. a stuck upstream AI call) from wedging a
# worker forever. Generous because document processing/AI calls are slow.
timeout = int(os.environ.get("GUNICORN_TIMEOUT_SECONDS", "120"))

# Recycle workers periodically to bound the impact of any slow memory leak
# (jitter avoids every worker restarting at the same instant).
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "2000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "200"))

graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT_SECONDS", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE_SECONDS", "5"))

# Gunicorn's access log writes the raw request line, which includes
# path-borne credentials (Telegram bot token, share tokens). Disabled by
# default; the app's structured access log records route templates only.
accesslog = "-" if os.environ.get("GUNICORN_RAW_ACCESS_LOG") == "1" else None
errorlog = "-"  # stderr
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
