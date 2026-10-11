"""Async SQLAlchemy engine + session management.

The engine is created lazily on first use so the FastAPI app can boot
even when the database is unreachable (e.g. RDS sitting in a private VPC
the preview pod can't see). Routes that actually need the DB will fail
fast with a clear error; everything else keeps working.
"""
from __future__ import annotations

import contextlib
import logging
import os
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

log = logging.getLogger(__name__)


def _build_url() -> str:
    """Prefer DATABASE_URL; otherwise compose from DB_* parts."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    name = os.environ.get("DB_NAME")
    if not all([host, user, password, name]):
        raise RuntimeError(
            "Postgres is not configured. Set DATABASE_URL or DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME."
        )
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def init_engine(echo: bool = False) -> AsyncEngine:
    """Create the engine + sessionmaker. Idempotent."""
    global engine, AsyncSessionLocal
    if engine is not None:
        return engine
    url = _build_url()
    engine = create_async_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        # Fail fast (5 s) instead of waiting on a private-VPC IP for 60+ s.
        connect_args={"timeout": 5},
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    log.info("Postgres engine initialised (url=%s)", _redact(url))
    return engine


def _redact(url: str) -> str:
    """Hide password in a SQLAlchemy URL for logs."""
    try:
        from sqlalchemy.engine.url import make_url
        u = make_url(url)
        return str(u.set(password="***" if u.password else None))
    except Exception:
        return "<unparseable>"


async def dispose_engine() -> None:
    """Cleanly close the pool on shutdown."""
    global engine, AsyncSessionLocal
    if engine is not None:
        await engine.dispose()
        engine = None
        AsyncSessionLocal = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an `AsyncSession`."""
    if AsyncSessionLocal is None:
        init_engine()
    assert AsyncSessionLocal is not None  # narrow for type-checkers
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@contextlib.asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Standalone session for background tasks; commits on success, rolls back on error."""
    if AsyncSessionLocal is None:
        init_engine()
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
