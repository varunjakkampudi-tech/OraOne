"""Agent → website crawl provisioning.

Bridges the agent-builder "website URL" field to the existing website-crawler
pipeline: when a chat agent is deployed with a website, we auto-create a
knowledge base, register the site, and kick off a background crawl. The
crawled content lands as DocumentChunks under that KB — and because an agent
with no explicit KB link falls back to *all* active org KBs at answer time
(see ``agent_runtime._linked_kb_ids``), the agent immediately answers from it.
"""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.crawl_job import CrawlJob, CrawlJobStatus, CrawlTrigger
from app.database.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
from app.database.models.website import Website, WebsiteStatus
from app.services.website_crawler import URLValidationError, run_crawl, validate_url

log = logging.getLogger("app.agent_website")


async def _existing_website(session: AsyncSession, *, organization_id, base_url: str) -> Optional[Website]:
    return await session.scalar(
        select(Website)
        .where(Website.organization_id == organization_id)
        .where(Website.base_url == base_url)
        .where(Website.deleted_at.is_(None))
    )


async def provision_website_crawl(
    session: AsyncSession,
    agent: Agent,
    website_url: str,
    background: BackgroundTasks,
) -> Optional[Website]:
    """Best-effort: create KB + Website + start crawl for ``agent``'s site.

    Returns the ``Website`` when a crawl was started, else ``None`` (already
    crawled, invalid URL, or a soft failure). Never raises — deploying an
    agent must not fail just because the optional crawl couldn't start.
    """
    url = (website_url or "").strip()
    if not url:
        return None
    try:
        base_url = validate_url(url)
    except URLValidationError as e:
        log.warning("agent %s website crawl skipped — invalid URL %r: %s", agent.id, url, e)
        return None

    # Don't re-register/re-crawl the same site for this org on every re-deploy.
    if await _existing_website(session, organization_id=agent.organization_id, base_url=base_url):
        return None

    host = urlparse(base_url).hostname or base_url
    kb = KnowledgeBase(
        organization_id=agent.organization_id,
        project_id=agent.project_id,
        name=f"{agent.name} — {host}"[:160],
        description=f"Auto-crawled from {base_url} for agent “{agent.name}”.",
        status=KnowledgeBaseStatus.active,
    )
    session.add(kb)
    await session.flush()

    website = Website(
        organization_id=agent.organization_id,
        project_id=agent.project_id,
        knowledge_base_id=kb.id,
        name=host[:200],
        base_url=base_url,
        status=WebsiteStatus.crawling,
    )
    session.add(website)
    await session.flush()

    job = CrawlJob(
        website_id=website.id,
        organization_id=agent.organization_id,
        status=CrawlJobStatus.queued,
        trigger=CrawlTrigger.manual,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background.add_task(run_crawl, job.id)
    log.info("agent %s deploy triggered crawl job %s for %s", agent.id, job.id, base_url)
    return website
