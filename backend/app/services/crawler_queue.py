"""Distributed crawl frontier operations (R3+).

Thin, transaction-safe helpers over the :class:`CrawlFrontier` table that let
any number of workers cooperate on a single crawl without a shared in-memory
queue:

* :func:`enqueue` — add discovered URLs (idempotent per job via ``ON CONFLICT``).
* :func:`claim_batch` — atomically lease pending URLs with ``FOR UPDATE SKIP
  LOCKED`` so two workers never grab the same URL.
* :func:`mark` — settle a leased URL (done/error/skipped).
* :func:`stats` / :func:`pending_count` — progress for the UI + finalisation.
* :func:`requeue_stale` — recover URLs leased by a worker that died.

All functions take an :class:`AsyncSession` and never commit — the caller owns
the transaction boundary so claims + updates stay atomic.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.crawl_frontier import CrawlFrontier, FrontierStatus


async def enqueue(
    session: AsyncSession,
    *,
    job_id: uuid.UUID,
    website_id: uuid.UUID,
    organization_id: uuid.UUID,
    items: list[tuple[str, int]],
) -> int:
    """Insert ``(url, depth)`` pairs, ignoring URLs already queued for this job.

    Returns the number of rows actually inserted. Uses Postgres
    ``INSERT … ON CONFLICT (job_id, url) DO NOTHING`` so re-discovering a URL is
    a cheap no-op — this is what makes link-following safe across many workers.
    """
    if not items:
        return 0
    # De-dupe within the batch first (a single statement can't touch the same
    # conflict target twice).
    seen: set[str] = set()
    rows: list[dict] = []
    for url, depth in items:
        if url in seen:
            continue
        seen.add(url)
        rows.append(
            {
                "id": uuid.uuid4(),
                "job_id": job_id,
                "website_id": website_id,
                "organization_id": organization_id,
                "url": url[:2048],
                "host": (urlparse(url).hostname or "")[:255] or None,
                "depth": depth,
                "status": FrontierStatus.pending,
            }
        )
    if not rows:
        return 0
    stmt = pg_insert(CrawlFrontier).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_crawl_frontier_job_url")
    result = await session.execute(stmt)
    return int(result.rowcount or 0)


async def claim_batch(
    session: AsyncSession,
    *,
    job_id: uuid.UUID,
    worker_id: str,
    limit: int,
) -> list[tuple[uuid.UUID, str, int]]:
    """Atomically lease up to ``limit`` pending URLs for ``worker_id``.

    Uses ``FOR UPDATE SKIP LOCKED`` so concurrent workers grab disjoint sets of
    URLs with no contention. Returns ``[(frontier_id, url, depth), …]``.
    """
    if limit <= 0:
        return []
    pick = (
        select(CrawlFrontier.id)
        .where(CrawlFrontier.job_id == job_id)
        .where(CrawlFrontier.status == FrontierStatus.pending)
        .order_by(CrawlFrontier.depth.asc(), CrawlFrontier.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    ids = (await session.scalars(pick)).all()
    if not ids:
        return []
    now = datetime.now(timezone.utc)
    await session.execute(
        update(CrawlFrontier)
        .where(CrawlFrontier.id.in_(ids))
        .values(
            status=FrontierStatus.claimed,
            claimed_by=worker_id[:64],
            claimed_at=now,
            attempts=CrawlFrontier.attempts + 1,
        )
    )
    rows = (
        await session.execute(
            select(CrawlFrontier.id, CrawlFrontier.url, CrawlFrontier.depth)
            .where(CrawlFrontier.id.in_(ids))
        )
    ).all()
    return [(r.id, r.url, r.depth) for r in rows]


async def mark(
    session: AsyncSession,
    *,
    frontier_id: uuid.UUID,
    status: str,
    error: str | None = None,
) -> None:
    """Settle a leased URL into a terminal state."""
    await session.execute(
        update(CrawlFrontier)
        .where(CrawlFrontier.id == frontier_id)
        .values(status=status, error=(error or None) and error[:1000])
    )


async def stats(session: AsyncSession, job_id: uuid.UUID) -> dict[str, int]:
    """Return counts grouped by status: ``{pending, claimed, done, error, skipped, total}``."""
    rows = (
        await session.execute(
            select(CrawlFrontier.status, func.count())
            .where(CrawlFrontier.job_id == job_id)
            .group_by(text("1"))
        )
    ).all()
    out = {s: 0 for s in FrontierStatus.ALL}
    for status_val, n in rows:
        out[status_val] = int(n)
    out["total"] = sum(out[s] for s in FrontierStatus.ALL)
    return out


async def pending_count(session: AsyncSession, job_id: uuid.UUID) -> int:
    n = await session.scalar(
        select(func.count())
        .select_from(CrawlFrontier)
        .where(CrawlFrontier.job_id == job_id)
        .where(CrawlFrontier.status.in_((FrontierStatus.pending, FrontierStatus.claimed)))
    )
    return int(n or 0)


async def requeue_stale(
    session: AsyncSession, *, job_id: uuid.UUID, older_than_seconds: int = 120
) -> int:
    """Return URLs leased long ago (a crashed worker) back to ``pending``."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
    result = await session.execute(
        update(CrawlFrontier)
        .where(CrawlFrontier.job_id == job_id)
        .where(CrawlFrontier.status == FrontierStatus.claimed)
        .where(CrawlFrontier.claimed_at < cutoff)
        .values(status=FrontierStatus.pending, claimed_by=None, claimed_at=None)
    )
    return int(result.rowcount or 0)


__all__ = [
    "enqueue",
    "claim_batch",
    "mark",
    "stats",
    "pending_count",
    "requeue_stale",
]
