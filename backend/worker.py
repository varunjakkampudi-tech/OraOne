"""Dedicated process for scheduled workflows and webhook outbox delivery.

HTTP workers must not own these loops: a Gunicorn deployment can run multiple
HTTP processes, while this process is intentionally deployed as one Compose
service and uses database row locks for safe claims.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

from app.database import session as db_session
from app.database.session import dispose_engine, init_engine
from app.services.ops_service import prune_error_events
from app.services.webhook_outbox import start_outbox_worker, stop_outbox_worker
from app.services.workflow_scheduler import start_scheduler, stop_scheduler


PRUNE_INTERVAL_SECONDS = 24 * 60 * 60


async def _prune_error_events_daily(stop_event: asyncio.Event) -> None:
    """Delete error records past their retention period, once a day."""
    log = logging.getLogger("app.worker")
    while not stop_event.is_set():
        try:
            async with db_session.AsyncSessionLocal() as session:
                removed = await prune_error_events(session)
                await session.commit()
            log.info("error_events_pruned removed=%s", removed)
        except Exception:  # noqa: BLE001 - a failed prune must not stop the worker
            log.exception("error_events_prune_failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=PRUNE_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    init_engine()
    start_scheduler()
    start_outbox_worker()
    stop_event = asyncio.Event()
    prune_task = asyncio.create_task(_prune_error_events_daily(stop_event))
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Windows event loops do not implement add_signal_handler.
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop_event.set))
    try:
        await stop_event.wait()
    finally:
        stop_event.set()
        await prune_task
        await stop_scheduler()
        await stop_outbox_worker()
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
