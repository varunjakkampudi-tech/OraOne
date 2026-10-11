"""Dedicated process for scheduled workflows and webhook outbox delivery.

HTTP workers must not own these loops: a Gunicorn deployment can run multiple
HTTP processes, while this process is intentionally deployed as one Compose
service and uses database row locks for safe claims.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from app.database.session import dispose_engine, init_engine
from app.services.webhook_outbox import start_outbox_worker, stop_outbox_worker
from app.services.workflow_scheduler import start_scheduler, stop_scheduler


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    init_engine()
    start_scheduler()
    start_outbox_worker()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()
    await stop_scheduler()
    await stop_outbox_worker()
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
