"""Website crawling engine (R3).

Turns a website into searchable knowledge:

    validate → robots.txt → sitemap → recursive crawl → extract → clean →
    markdown → chunk → embed → document_chunks (RAG-ready)

Design goals
------------
* **Dependency-free extraction.** Uses ``httpx`` (already a dependency)
  for async fetching and the stdlib ``html.parser`` for a robust
  HTML→markdown conversion that strips nav/header/footer/script/style.
  No BeautifulSoup / Playwright / trafilatura required, so it deploys
  anywhere the API runs.
* **SSRF-safe.** Every URL is validated: only http(s), public DNS, no
  loopback / private / link-local / reserved IPs.
* **Incremental.** Page content is checksummed; unchanged pages are
  skipped on recrawl (no re-embedding) — a major cost saver.
* **Tenant-scoped.** Pages + chunks carry ``organization_id`` and
  ``knowledge_base_id`` so website knowledge is isolated and retrievable
  through the same RAG path as uploaded documents.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import re
import socket
import time
import urllib.robotparser
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse, urldefrag

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.crawl_frontier import CrawlFrontier, FrontierStatus
from app.database.models.crawl_job import CrawlJob, CrawlJobStatus, CrawlLog
from app.database.models.document_chunk import DocumentChunk
from app.database.models.website import CrawlMode, Website, WebsiteStatus
from app.database.models.website_page import PageStatus, WebsitePage
from app.services import crawler_queue
from app.services.document_processing import (
    ExtractedPage,
    _embed_chunks,
    chunk_pages,
    compute_checksum,
)

log = logging.getLogger("app.crawler")

USER_AGENT = "OraOneBot/1.0 (+https://oraone.in/bot)"
FETCH_TIMEOUT = 15.0
MAX_BYTES = 5 * 1024 * 1024   # 5 MB cap per page
HARD_PAGE_CAP = 100_000       # absolute ceiling regardless of user setting
MAX_WORKERS = 6               # hard ceiling on parallel workers (DB-pool aware)
DEFAULT_TARGET = 5            # initial adaptive concurrency (all workers pre-open a
                             # DB session regardless, so a high start target is a
                             # pure speed win — the controller still backs off on
                             # error/latency spikes and per-host politeness applies)
CLAIM_BATCH = 4               # URLs a worker leases from the frontier at once
HEARTBEAT_EVERY = 2.0         # seconds between adaptive-controller ticks
STALE_LEASE_SECONDS = 120     # reclaim URLs leased by a dead worker after this
# Some sites publish an enormous robots.txt Crawl-delay (e.g. ford.com asks for
# 10s). Honouring it verbatim serialises a whole-site crawl to one page every N
# seconds and looks broken. Googlebot ignores Crawl-delay outright; we honour it
# only up to this small, still-polite ceiling.
MAX_ROBOTS_CRAWL_DELAY = 2.0  # seconds


# ────────────────────────── URL validation (SSRF) ──────────────────────────

class URLValidationError(ValueError):
    """Raised when a URL fails safety/format validation."""


def _is_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _host_is_safe(host: str) -> bool:
    """Resolve ``host`` and require every address to be a public IP."""
    if not host:
        return False
    low = host.lower()
    if low in ("localhost",) or low.endswith(".local") or low.endswith(".internal"):
        return False
    # Literal IP?
    try:
        ipaddress.ip_address(host)
        return _is_public_ip(host)
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError, OSError):
        return False
    addrs = {info[4][0] for info in infos}
    return bool(addrs) and all(_is_public_ip(a) for a in addrs)


def validate_url(raw: str, *, require_safe_host: bool = True) -> str:
    """Normalise + validate a crawl URL. Returns the cleaned URL.

    Rejects non-http(s) schemes and (optionally) hosts that resolve to
    private / loopback / reserved addresses (SSRF protection).
    """
    raw = (raw or "").strip()
    if not raw:
        raise URLValidationError("URL is required.")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise URLValidationError("Only http and https URLs are supported.")
    if not parsed.hostname:
        raise URLValidationError("URL has no host.")
    if require_safe_host and not _host_is_safe(parsed.hostname):
        raise URLValidationError(
            "URL host is not reachable on the public internet (or is a private address)."
        )
    return parsed.geturl()


# ────────────────────────── HTML → markdown ──────────────────────────

_SKIP_TAGS = {
    "script", "style", "nav", "header", "footer", "aside", "form", "noscript",
    "svg", "iframe", "button", "input", "select", "option", "template", "head",
}
_BLOCK_TAGS = {"p", "div", "section", "article", "br", "tr", "blockquote"}
_HEADINGS = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### ", "h5": "##### ", "h6": "###### "}
_WS_RE = re.compile(r"[ \t\u00A0]+")
_NL_RE = re.compile(r"\n{3,}")


class _HTMLExtractor(HTMLParser):
    """Stream HTML into markdown blocks + plain text + metadata + links."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.blocks: list[str] = []
        self._buf: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self.title: Optional[str] = None
        self.description: Optional[str] = None
        self.language: Optional[str] = None
        self.canonical: Optional[str] = None
        self.links: list[str] = []
        self._list_stack: list[str] = []
        self._pre_depth = 0
        self._heading: Optional[str] = None

    # -- helpers --
    def _flush(self, prefix: str = "") -> None:
        text = "".join(self._buf).strip()
        self._buf = []
        if text:
            self.blocks.append(prefix + text)

    # -- tag handling --
    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "html" and ad.get("lang") and not self.language:
            self.language = ad["lang"][:16]
        if tag == "meta":
            name = (ad.get("name") or ad.get("property") or "").lower()
            if name in ("description", "og:description") and not self.description:
                self.description = (ad.get("content") or "")[:1024] or None
            return
        if tag == "link" and (ad.get("rel") or "").lower() == "canonical":
            href = ad.get("href")
            if href:
                self.canonical = urljoin(self.base_url, href)
            return
        if tag == "title":
            self._in_title = True
            return
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "a":
            href = ad.get("href")
            if href:
                absu, _ = urldefrag(urljoin(self.base_url, href))
                self.links.append(absu)
            return
        if tag == "pre":
            self._flush()
            self._pre_depth += 1
            self.blocks.append("```")
            return
        if tag in _HEADINGS:
            self._flush()
            self._heading = _HEADINGS[tag]
            return
        if tag in ("ul", "ol"):
            self._flush()
            self._list_stack.append(tag)
            return
        if tag == "li":
            self._flush()
            marker = "- " if (self._list_stack and self._list_stack[-1] == "ul") else "1. "
            self._buf.append(marker)
            return
        if tag in ("strong", "b"):
            self._buf.append("**")
            return
        if tag in ("em", "i"):
            self._buf.append("*")
            return
        if tag == "code" and not self._pre_depth:
            self._buf.append("`")
            return
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            return
        if tag in _SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "pre":
            self._flush()
            self.blocks.append("```")
            if self._pre_depth:
                self._pre_depth -= 1
            return
        if tag in _HEADINGS:
            self._flush(prefix=self._heading or "")
            self._heading = None
            return
        if tag in ("ul", "ol"):
            if self._list_stack:
                self._list_stack.pop()
            return
        if tag == "li":
            self._flush()
            return
        if tag in ("strong", "b"):
            self._buf.append("**")
            return
        if tag in ("em", "i"):
            self._buf.append("*")
            return
        if tag == "code" and not self._pre_depth:
            self._buf.append("`")
            return
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._in_title:
            if not self.title and data.strip():
                self.title = data.strip()[:512]
            return
        if self._skip_depth:
            return
        if self._pre_depth:
            self._buf.append(data)
        else:
            self._buf.append(data)

    def finish(self) -> None:
        self._flush(prefix=self._heading or "")


def html_to_markdown(html: str, base_url: str) -> dict:
    """Extract markdown + plain text + metadata + links from HTML."""
    ex = _HTMLExtractor(base_url)
    try:
        ex.feed(html)
        ex.finish()
    except Exception as e:  # noqa: BLE001 — never let a malformed page crash a crawl
        log.warning("html_parse_error url=%s err=%s", base_url, e)
    blocks = [b for b in ex.blocks if b.strip()]
    markdown = _NL_RE.sub("\n\n", "\n\n".join(blocks)).strip()
    # plain text = markdown minus the lightweight markers
    plain = re.sub(r"[#*`>]", "", markdown)
    plain = _WS_RE.sub(" ", plain).strip()
    return {
        "title": ex.title,
        "description": ex.description,
        "language": ex.language,
        "canonical": ex.canonical,
        "markdown": markdown,
        "text": plain,
        "links": ex.links,
    }


# ────────────────────────── classification ──────────────────────────

_CLASS_RULES = [
    ("documentation", ("/docs", "/documentation", "/api", "/reference", "/guide", "/sdk")),
    ("faq", ("/faq", "/faqs", "/help", "/support")),
    ("blog", ("/blog", "/news", "/article", "/post")),
    ("pricing", ("/pricing", "/plans")),
    ("legal", ("/privacy", "/terms", "/legal", "/cookie")),
    ("product", ("/product", "/features", "/solutions")),
    ("contact", ("/contact", "/about")),
]


def classify_url(url: str) -> Optional[str]:
    path = urlparse(url).path.lower()
    for label, needles in _CLASS_RULES:
        if any(n in path for n in needles):
            return label
    return None


# ────────────────────────── robots + sitemap ──────────────────────────

async def _fetch(client, url: str) -> tuple[int, str, str]:
    """GET a URL. Returns (status_code, content_type, text). Caps body size."""
    resp = await client.get(url, follow_redirects=True)
    ctype = resp.headers.get("content-type", "")
    raw = resp.content[:MAX_BYTES]
    try:
        text = raw.decode(resp.encoding or "utf-8", errors="replace")
    except (LookupError, TypeError):
        text = raw.decode("utf-8", errors="replace")
    return resp.status_code, ctype, text


def _load_robots(base_url: str) -> Optional[urllib.robotparser.RobotFileParser]:
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        return rp
    except Exception:  # noqa: BLE001 — robots is best-effort
        return None


_SITEMAP_LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)


async def discover_sitemap_urls(
    client, base_url: str, limit: int, extra_roots: Optional[list[str]] = None
) -> list[str]:
    """Discover page URLs from sitemaps.

    Reads any ``Sitemap:`` directives declared in robots.txt (``extra_roots`` —
    what Googlebot does) *and* the conventional ``/sitemap.xml`` /
    ``/sitemap_index.xml`` locations, following one level of sitemap-index
    nesting. Aggregates across all of them up to ``limit`` (a site may split its
    URLs across several sitemaps, e.g. ford.com's parts/accessories sitemaps).
    """
    parsed = urlparse(base_url)
    roots: list[str] = []
    for r in list(extra_roots or []) + [
        f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
    ]:
        if r and r not in roots:
            roots.append(r)

    found: list[str] = []
    seen_child: set[str] = set()
    for root in roots:
        if len(found) >= limit:
            break
        try:
            status, ctype, text = await _fetch(client, root)
        except Exception:  # noqa: BLE001
            continue
        if status != 200 or ("xml" not in ctype and "<loc>" not in text):
            continue
        for loc in _SITEMAP_LOC_RE.findall(text):
            loc = loc.strip()
            if loc.endswith(".xml"):
                if loc in seen_child:
                    continue
                seen_child.add(loc)
                try:
                    s2, _c2, t2 = await _fetch(client, loc)
                    if s2 == 200:
                        found.extend(u.strip() for u in _SITEMAP_LOC_RE.findall(t2))
                except Exception:  # noqa: BLE001
                    continue
            else:
                found.append(loc)
            if len(found) >= limit:
                break
    # de-dupe, preserve order
    out: list[str] = []
    s: set[str] = set()
    for u in found:
        if u not in s:
            s.add(u)
            out.append(u)
    return out[:limit]


# ────────────────────────── scope rules ──────────────────────────

def _same_site(url: str, base: str, allowed_domains: list[str]) -> bool:
    h = urlparse(url).hostname or ""
    bh = urlparse(base).hostname or ""
    if not h:
        return False
    if h == bh:
        return True
    if allowed_domains and any(h == d or h.endswith("." + d) for d in allowed_domains):
        return True
    # allow subdomains of the base registrable host by default
    return h.endswith("." + bh) or bh.endswith("." + h)


def _path_allowed(url: str, include: list[str], exclude: list[str]) -> bool:
    path = urlparse(url).path or "/"
    if exclude and any(path.startswith(p) for p in exclude):
        return False
    if include:
        return any(path.startswith(p) for p in include)
    return True


_NON_PAGE_EXT = (
    ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".mp4",
    ".mp3", ".css", ".js", ".ico", ".woff", ".woff2", ".ttf", ".xml", ".json",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".dmg", ".exe",
)


def _looks_like_page(url: str) -> bool:
    path = urlparse(url).path.lower()
    return not path.endswith(_NON_PAGE_EXT)


# ────────────────────────── orchestration ──────────────────────────

def _auth_headers(auth: dict) -> tuple[dict, Optional[tuple]]:
    """Build (headers, basic_auth) from a website auth_config dict."""
    headers: dict[str, str] = {"User-Agent": USER_AGENT}
    basic = None
    if not auth:
        return headers, basic
    atype = (auth.get("type") or "").lower()
    if atype in ("bearer", "token") and auth.get("token"):
        headers["Authorization"] = f"Bearer {auth['token']}"
    elif atype == "basic" and auth.get("username"):
        basic = (auth.get("username", ""), auth.get("password", ""))
    elif atype == "cookie" and auth.get("value"):
        headers["Cookie"] = auth["value"]
    elif atype in ("api_key", "header") and auth.get("header"):
        headers[auth["header"]] = auth.get("value", "")
    return headers, basic


async def _add_log(session: AsyncSession, job: CrawlJob, url: Optional[str], status: str, level: str, message: str) -> None:
    session.add(
        CrawlLog(
            job_id=job.id,
            website_id=job.website_id,
            url=(url or "")[:2048] or None,
            status=status[:40] if status else None,
            level=level,
            message=(message or "")[:4000] or None,
        )
    )


def _maker():
    """Return the async sessionmaker, initialising the engine on first use."""
    from app.database.session import AsyncSessionLocal, init_engine

    if AsyncSessionLocal is None:
        init_engine()
    from app.database.session import AsyncSessionLocal as Maker

    return Maker


# ────────────────────────── distributed engine ──────────────────────────


class _Engine:
    """Shared, mutable state for one distributed crawl.

    All workers + the controller live in a single asyncio event loop, so plain
    Python attributes are safe to share without locks (mutations never span an
    ``await``). Each worker still owns its **own** DB session/connection — the
    frontier table is the only coordination point.
    """

    def __init__(self, *, website, job_id, mode, base, base_path, include,
                 exclude, allowed, max_pages, max_depth, robots, robots_delay,
                 politeness, render_js, max_workers):
        self.website = website
        self.job_id = job_id
        self.website_id = website.id
        self.org_id = website.organization_id
        self.mode = mode
        self.base = base
        self.base_path = base_path
        self.include = include
        self.exclude = exclude
        self.allowed = allowed
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.robots = robots
        self.robots_delay = robots_delay        # seconds (robots Crawl-delay)
        self.politeness = politeness             # seconds (user crawl_delay_ms)
        self.render_js = render_js
        self.max_workers = max_workers
        # live, adaptive state
        self.target = min(DEFAULT_TARGET, max_workers)
        self.processed = 0                       # pages fetched (counts to cap)
        self.inflight = 0
        self.chunks_total = 0
        self.recent: deque = deque(maxlen=40)    # (ok: bool, latency: float)
        self.host_last: dict[str, float] = {}
        self.control = CrawlJobStatus.crawling   # crawling | paused | cancelled
        self.stop = asyncio.Event()
        self.render_warned = False
        # Buffered counter deltas, flushed to the shared crawl_jobs row in a
        # short, single-row transaction (see ``_bump`` / ``_flush_counts``).
        # Holding the hot crawl_jobs row lock across a worker's whole batch —
        # alongside frontier/page row locks — caused cross-worker deadlocks.
        self._pending = {"completed": 0, "failed": 0, "skipped": 0, "chunks": 0}


async def _log(session, *, job_id, website_id, url, status, level, message) -> None:
    session.add(
        CrawlLog(
            job_id=job_id,
            website_id=website_id,
            url=(url or "")[:2048] or None,
            status=(status or "")[:40] or None,
            level=level,
            message=(message or "")[:4000] or None,
        )
    )


def _bump(engine: "_Engine", **deltas) -> None:
    """Buffer job counter increments in memory (no DB I/O, no locks).

    Mutations never span an ``await`` so this is safe to call from any worker
    on the shared engine without a lock. The buffered totals are written to the
    ``crawl_jobs`` row by :func:`_flush_counts`.
    """
    for key in ("completed", "failed", "skipped", "chunks"):
        if deltas.get(key):
            engine._pending[key] += deltas[key]


def _is_deadlock(err: BaseException) -> bool:
    """True if ``err`` wraps a Postgres deadlock (asyncpg DeadlockDetectedError)."""
    orig = getattr(err, "orig", None)
    name = type(orig).__name__ if orig is not None else type(err).__name__
    return "DeadlockDetected" in name or "deadlock detected" in str(err).lower()


async def _flush_counts(engine: "_Engine") -> None:
    """Flush buffered counter deltas to the shared ``crawl_jobs`` row.

    Runs in its **own** short-lived transaction that touches only the single
    job row — it never holds frontier/page locks — so concurrent flushes (even
    across processes) can only serialize, not deadlock. A deadlock-retry guard
    covers the rare contention with the controller's telemetry update; on final
    failure the deltas are returned to the buffer for the next flush.
    """
    pending = engine._pending
    if not any(pending.values()):
        return
    # Snapshot + reset synchronously (no await in between → no lost increments).
    snapshot = dict(pending)
    for key in pending:
        pending[key] = 0

    values = {}
    if snapshot["completed"]:
        values["pages_completed"] = CrawlJob.pages_completed + snapshot["completed"]
    if snapshot["failed"]:
        values["pages_failed"] = CrawlJob.pages_failed + snapshot["failed"]
    if snapshot["skipped"]:
        values["pages_skipped"] = CrawlJob.pages_skipped + snapshot["skipped"]
    if snapshot["chunks"]:
        values["chunks_created"] = CrawlJob.chunks_created + snapshot["chunks"]

    Maker = _maker()
    for attempt in range(5):
        try:
            async with Maker() as session:  # type: ignore[misc]
                await session.execute(
                    update(CrawlJob).where(CrawlJob.id == engine.job_id).values(**values)
                )
                await session.commit()
            return
        except DBAPIError as e:
            if _is_deadlock(e) and attempt < 4:
                await asyncio.sleep(0.05 * (2 ** attempt))
                continue
            # Give the increments back so the next flush retries them, then bail
            # — counter telemetry must never abort the crawl.
            for key, val in snapshot.items():
                engine._pending[key] += val
            log.warning("counter_flush_failed job=%s err=%s", engine.job_id, e)
            return
        except Exception as e:  # noqa: BLE001 — telemetry must not kill the crawl
            for key, val in snapshot.items():
                engine._pending[key] += val
            log.warning("counter_flush_error job=%s err=%s", engine.job_id, e)
            return


async def run_crawl(job_id) -> None:
    """Public entry point — seed + run a distributed crawl for ``job_id``."""
    Maker = _maker()
    async with Maker() as session:  # type: ignore[misc]
        await _seed_and_run(session, job_id)


async def _seed_and_run(session: AsyncSession, job_id) -> None:
    import httpx

    job = await session.get(CrawlJob, job_id)
    if job is None:
        return
    website = await session.get(Website, job.website_id)
    if website is None or website.deleted_at is not None:
        job.status = CrawlJobStatus.failed
        job.error = "Website not found."
        job.finished_at = datetime.now(timezone.utc)
        await session.commit()
        return

    base = website.base_url
    mode = website.crawl_mode
    include = list(website.include_paths or [])
    exclude = list(website.exclude_paths or [])
    allowed = list(website.allowed_domains or [])
    max_pages = min(website.max_pages or HARD_PAGE_CAP, HARD_PAGE_CAP)
    max_depth = website.max_depth if mode in (CrawlMode.entire, CrawlMode.folder) else 0
    base_path = urlparse(base).path or "/"
    max_workers = website.max_concurrency or MAX_WORKERS
    max_workers = max(1, min(max_workers, MAX_WORKERS))

    headers, basic = _auth_headers(website.auth_config or {})
    # robots.txt is blocking network I/O — load it off the event loop.
    robots = await asyncio.to_thread(_load_robots, base) if website.respect_robots else None
    robots_delay = 0.0
    if robots is not None:
        try:
            cd = robots.crawl_delay(USER_AGENT)
            requested = float(cd) if cd else 0.0
            robots_delay = min(requested, MAX_ROBOTS_CRAWL_DELAY)
            if requested > MAX_ROBOTS_CRAWL_DELAY:
                await _add_log(
                    session, job, None, "robots", "info",
                    f"robots.txt requested Crawl-delay {requested:g}s — capped to "
                    f"{MAX_ROBOTS_CRAWL_DELAY:g}s to keep the crawl responsive.",
                )
        except Exception:  # noqa: BLE001
            robots_delay = 0.0
    politeness = max(0.0, (website.crawl_delay_ms or 0) / 1000.0)

    # ── resume detection: a paused job keeps its frontier, so just continue ──
    already = await session.scalar(
        select(func.count()).select_from(CrawlFrontier).where(CrawlFrontier.job_id == job_id)
    )
    resuming = bool(already)

    job.status = CrawlJobStatus.crawling
    job.started_at = job.started_at or datetime.now(timezone.utc)
    job.worker_count = max_workers
    job.heartbeat_at = datetime.now(timezone.utc)
    website.status = WebsiteStatus.crawling
    website.error = None
    await session.commit()

    try:
        if resuming:
            # return any rows leased by the previous (now-stopped) run.
            await crawler_queue.requeue_stale(session, job_id=job_id, older_than_seconds=0)
            await session.commit()
        else:
            async with httpx.AsyncClient(
                timeout=FETCH_TIMEOUT, headers=headers, auth=basic, max_redirects=5
            ) as client:
                seeds: list[tuple[str, int]] = []
                # Sitemaps declared in robots.txt (what Googlebot reads) take
                # priority over guessing /sitemap.xml — many big sites split
                # their URLs across several declared sitemaps.
                robots_sitemaps: list[str] = []
                if robots is not None:
                    try:
                        robots_sitemaps = [s for s in (robots.site_maps() or []) if s]
                    except Exception:  # noqa: BLE001
                        robots_sitemaps = []
                if mode == CrawlMode.sitemap:
                    urls = await discover_sitemap_urls(client, base, max_pages, extra_roots=robots_sitemaps)
                    seeds = [(u, 0) for u in (urls or [base])]
                elif mode == CrawlMode.single:
                    seeds = [(base, 0)]
                else:
                    sm = await discover_sitemap_urls(client, base, max_pages, extra_roots=robots_sitemaps)
                    seeds = [(base, 0)] + [(u, 1) for u in sm]
                await crawler_queue.enqueue(
                    session,
                    job_id=job_id,
                    website_id=website.id,
                    organization_id=website.organization_id,
                    items=seeds,
                )
                await session.commit()

        engine = _Engine(
            website=website, job_id=job_id, mode=mode, base=base, base_path=base_path,
            include=include, exclude=exclude, allowed=allowed, max_pages=max_pages,
            max_depth=max_depth, robots=robots, robots_delay=robots_delay,
            politeness=politeness, render_js=bool(website.render_js), max_workers=max_workers,
        )

        controller = asyncio.create_task(_controller(engine, headers, basic))
        workers = [
            asyncio.create_task(_worker(i, engine, headers, basic))
            for i in range(max_workers)
        ]
        await asyncio.gather(*workers)
        engine.stop.set()
        await controller

        await _finalize(session, job_id, engine)
    except Exception as e:  # noqa: BLE001
        log.exception("crawl_failed site=%s err=%s", job.website_id, e)
        await session.rollback()
        fresh_job = await session.get(CrawlJob, job_id)
        fresh_site = await session.get(Website, job.website_id)
        if fresh_job is not None:
            fresh_job.status = CrawlJobStatus.failed
            fresh_job.error = f"{type(e).__name__}: {e}"[:1000]
            fresh_job.finished_at = datetime.now(timezone.utc)
        if fresh_site is not None:
            fresh_site.status = WebsiteStatus.failed
            fresh_site.error = f"{type(e).__name__}: {e}"[:1000]
        await session.commit()


async def _controller(engine: "_Engine", headers, basic) -> None:
    """Adaptive concurrency + control signals + live telemetry.

    Every tick it: (1) reads the live job/website status so a pause or cancel
    from the API propagates to the workers, (2) reclaims URLs leased by a dead
    worker, (3) nudges ``target`` concurrency up/down from the rolling error
    rate + latency, and (4) writes progress (frontier size, concurrency) back
    to the ``crawl_jobs`` row for the UI.
    """
    Maker = _maker()
    async with Maker() as session:  # type: ignore[misc]
        while not engine.stop.is_set():
            try:
                await asyncio.sleep(HEARTBEAT_EVERY)
                # (1) control signals — fresh scalar reads see other sessions' commits
                jstatus = await session.scalar(
                    select(CrawlJob.status).where(CrawlJob.id == engine.job_id)
                )
                wstatus = await session.scalar(
                    select(Website.status).where(Website.id == engine.website_id)
                )
                if jstatus == CrawlJobStatus.cancelled:
                    engine.control = CrawlJobStatus.cancelled
                elif jstatus == CrawlJobStatus.paused or wstatus == WebsiteStatus.paused:
                    engine.control = CrawlJobStatus.paused
                # (2) recover stale leases
                await crawler_queue.requeue_stale(
                    session, job_id=engine.job_id, older_than_seconds=STALE_LEASE_SECONDS
                )
                # flush buffered page counters so the UI sees live progress
                await _flush_counts(engine)
                # (3) adapt concurrency
                recent = list(engine.recent)
                if recent:
                    err_rate = sum(1 for ok, _ in recent if not ok) / len(recent)
                    avg_lat = sum(lat for _, lat in recent) / len(recent)
                else:
                    err_rate, avg_lat = 0.0, 0.0
                st = await crawler_queue.stats(session, engine.job_id)
                pending = st["pending"] + st["claimed"]
                if err_rate > 0.30 or avg_lat > 8.0:
                    engine.target = max(1, engine.target - 1)
                elif err_rate < 0.10 and avg_lat < 3.0 and pending > engine.target:
                    engine.target = min(engine.max_workers, engine.target + 1)
                # (4) telemetry
                await session.execute(
                    update(CrawlJob)
                    .where(CrawlJob.id == engine.job_id)
                    .values(
                        concurrency=engine.target,
                        frontier_size=pending,
                        pages_total=min(st["total"], engine.max_pages),
                        heartbeat_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()
            except Exception as e:  # noqa: BLE001 — never let telemetry kill a crawl
                log.warning("controller_tick_error job=%s err=%s", engine.job_id, e)
                await session.rollback()


async def _worker(index: int, engine: "_Engine", headers, basic) -> None:
    """One crawl worker: claims URLs from the frontier and processes them."""
    import httpx

    Maker = _maker()
    worker_id = f"w{index}-{os.getpid()}"
    async with Maker() as session:  # type: ignore[misc]
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT, headers=headers, auth=basic, max_redirects=5
        ) as client:
            while not engine.stop.is_set():
                if engine.control in (CrawlJobStatus.paused, CrawlJobStatus.cancelled):
                    break
                # adaptive parking: only the first ``target`` workers fetch.
                if index >= engine.target:
                    await asyncio.sleep(0.2)
                    continue
                # respect the page cap (count in-flight to avoid overshoot).
                if engine.processed + engine.inflight >= engine.max_pages:
                    if engine.inflight == 0:
                        engine.stop.set()
                    await asyncio.sleep(0.1)
                    continue

                claimed = await crawler_queue.claim_batch(
                    session, job_id=engine.job_id, worker_id=worker_id, limit=CLAIM_BATCH
                )
                await session.commit()
                if not claimed:
                    pending = await crawler_queue.pending_count(session, engine.job_id)
                    if pending == 0 and engine.inflight == 0:
                        engine.stop.set()
                        break
                    await asyncio.sleep(0.25)
                    continue

                for fid, url, depth in claimed:
                    if engine.control in (CrawlJobStatus.paused, CrawlJobStatus.cancelled):
                        # hand the URL back so a resume can pick it up.
                        await crawler_queue.mark(
                            session, frontier_id=fid, status=FrontierStatus.pending
                        )
                        continue
                    try:
                        await _process_one(engine, session, client, fid, url, depth)
                    except Exception as e:  # noqa: BLE001 — one bad URL must not kill the worker
                        await session.rollback()
                        await crawler_queue.mark(
                            session, frontier_id=fid, status=FrontierStatus.error, error=str(e)
                        )
                        _bump(engine, failed=1)
                        await _log(
                            session, job_id=engine.job_id, website_id=engine.website_id,
                            url=url, status="error", level="error", message=str(e)[:500],
                        )
                await session.commit()
                await _flush_counts(engine)


async def _politeness(engine: "_Engine", url: str) -> None:
    """Per-host rate limiting: honour the larger of user delay / robots Crawl-delay."""
    delay = max(engine.politeness, engine.robots_delay)
    if delay <= 0:
        return
    host = urlparse(url).hostname or ""
    now = time.monotonic()
    last = engine.host_last.get(host, 0.0)
    wait = last + delay - now
    if wait > 0:
        await asyncio.sleep(wait)
        now = time.monotonic()
    engine.host_last[host] = now


async def _fetch_page(engine: "_Engine", client, url: str) -> tuple[int, str, str]:
    """Fetch a page, optionally rendering JavaScript first (graceful fallback)."""
    if engine.render_js:
        html = await _render_html(engine, url)
        if html is not None:
            return 200, "text/html", html
    return await _fetch(client, url)


async def _render_html(engine: "_Engine", url: str) -> Optional[str]:
    """Render a page with a headless browser if Playwright is installed.

    Returns ``None`` (so the caller falls back to static fetch) when no renderer
    is available or rendering fails — JS rendering is a best-effort enhancement,
    never a hard dependency.
    """
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except Exception:  # noqa: BLE001
        if not engine.render_warned:
            log.warning(
                "js_render_unavailable site=%s — install Playwright to enable JS "
                "rendering; falling back to static HTML.", engine.website_id
            )
            engine.render_warned = True
        return None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page(user_agent=USER_AGENT)
                await page.goto(url, wait_until="networkidle", timeout=int(FETCH_TIMEOUT * 1000))
                return await page.content()
            finally:
                await browser.close()
    except Exception as e:  # noqa: BLE001
        log.warning("js_render_failed url=%s err=%s", url, e)
        return None


async def _process_one(engine: "_Engine", session, client, fid, url: str, depth: int) -> None:
    """Validate scope → fetch → extract → persist → enqueue links for one URL."""
    url, _ = urldefrag(url)
    base, mode = engine.base, engine.mode

    # ── scope / safety filters ──
    if not _looks_like_page(url) or not _same_site(url, base, engine.allowed):
        await crawler_queue.mark(session, frontier_id=fid, status=FrontierStatus.skipped)
        return
    if mode == CrawlMode.folder and not (urlparse(url).path or "/").startswith(engine.base_path):
        await crawler_queue.mark(session, frontier_id=fid, status=FrontierStatus.skipped)
        return
    if not _path_allowed(url, engine.include, engine.exclude):
        await crawler_queue.mark(session, frontier_id=fid, status=FrontierStatus.skipped)
        await _log(session, job_id=engine.job_id, website_id=engine.website_id, url=url,
                   status="excluded", level="info", message="Skipped by include/exclude rules.")
        return
    if engine.robots is not None and not engine.robots.can_fetch(USER_AGENT, url):
        await crawler_queue.mark(session, frontier_id=fid, status=FrontierStatus.skipped)
        await _log(session, job_id=engine.job_id, website_id=engine.website_id, url=url,
                   status="robots", level="info", message="Disallowed by robots.txt.")
        return
    try:
        validate_url(url)
    except URLValidationError as e:
        await crawler_queue.mark(session, frontier_id=fid, status=FrontierStatus.skipped)
        await _log(session, job_id=engine.job_id, website_id=engine.website_id, url=url,
                   status="unsafe", level="warn", message=str(e))
        return

    # ── fetch (with politeness) ──
    await _politeness(engine, url)
    engine.inflight += 1
    t0 = time.monotonic()
    try:
        payload = await _fetch_page(engine, client, url)
        fetch_ok = True
    except Exception as e:  # noqa: BLE001
        payload, fetch_ok = e, False
    finally:
        engine.inflight -= 1
    latency = time.monotonic() - t0

    if not fetch_ok:
        engine.recent.append((False, latency))
        await crawler_queue.mark(session, frontier_id=fid, status=FrontierStatus.error, error=str(payload))
        _bump(engine, failed=1)
        await _log(session, job_id=engine.job_id, website_id=engine.website_id, url=url,
                   status="fetch_error", level="error", message=str(payload)[:500])
        return

    status_code, ctype, text = payload  # type: ignore[misc]
    if status_code != 200 or "html" not in ctype.lower():
        engine.recent.append((False, latency))
        await crawler_queue.mark(session, frontier_id=fid, status=FrontierStatus.error)
        _bump(engine, failed=1)
        await _log(session, job_id=engine.job_id, website_id=engine.website_id, url=url,
                   status=str(status_code), level="warn",
                   message=f"Skipped (status={status_code}, type={ctype[:60]}).")
        return

    engine.recent.append((True, latency))
    engine.processed += 1
    extracted = html_to_markdown(text, url)

    # follow links (entire / folder modes) — enqueue into the durable frontier.
    if mode in (CrawlMode.entire, CrawlMode.folder) and depth < engine.max_depth:
        seen: set[str] = set()
        links: list[tuple[str, int]] = []
        for link in extracted.get("links") or []:
            link, _ = urldefrag(link)
            if link and link not in seen:
                seen.add(link)
                links.append((link, depth + 1))
        if links:
            await crawler_queue.enqueue(
                session, job_id=engine.job_id, website_id=engine.website_id,
                organization_id=engine.org_id, items=links,
            )

    markdown = extracted["markdown"]
    if not markdown or len(markdown) < 40:
        await crawler_queue.mark(session, frontier_id=fid, status=FrontierStatus.done)
        _bump(engine, skipped=1)
        await _log(session, job_id=engine.job_id, website_id=engine.website_id, url=url,
                   status="empty", level="info", message="No meaningful content extracted.")
        return

    checksum = compute_checksum(markdown.encode("utf-8"))
    n_chunks = await _persist_page(session, engine.website, url, depth, extracted, checksum)
    await crawler_queue.mark(session, frontier_id=fid, status=FrontierStatus.done)
    if n_chunks < 0:
        _bump(engine, skipped=1)
        await _log(session, job_id=engine.job_id, website_id=engine.website_id, url=url,
                   status="unchanged", level="info", message="Content unchanged; embeddings reused.")
    else:
        engine.chunks_total += n_chunks
        _bump(engine, completed=1, chunks=n_chunks)
        await _log(session, job_id=engine.job_id, website_id=engine.website_id, url=url,
                   status="crawled", level="info", message=f"Indexed ({n_chunks} chunks).")


async def _finalize(session: AsyncSession, job_id, engine: "_Engine") -> None:
    """Write the terminal job/website state once all workers have stopped."""
    # Drain any counter deltas still buffered in memory before the terminal write.
    await _flush_counts(engine)
    website = await session.get(Website, engine.website_id)
    if website is None:
        return
    now = datetime.now(timezone.utc)

    # Job columns are mutated concurrently by the controller/workers in their own
    # sessions, so this session's cached row is stale. Build the terminal state
    # and persist it with an explicit UPDATE rather than ORM dirty-tracking
    # (which would skip columns whose stale in-memory value already matches).
    job_values: dict = {"concurrency": 0}

    if engine.control == CrawlJobStatus.cancelled:
        website.status = WebsiteStatus.ready if website.pages_count else WebsiteStatus.pending
        job_values["status"] = CrawlJobStatus.cancelled
        job_values["finished_at"] = now
    elif engine.control == CrawlJobStatus.paused:
        website.status = WebsiteStatus.paused
        job_values["status"] = CrawlJobStatus.paused
        job_values["heartbeat_at"] = now
    else:
        # completed — prune pages that no longer exist on the site.
        seen = set(
            (
                await session.scalars(
                    select(CrawlFrontier.url)
                    .where(CrawlFrontier.job_id == job_id)
                    .where(CrawlFrontier.status.in_(tuple(FrontierStatus.TERMINAL)))
                )
            ).all()
        )
        await _mark_deleted_pages(session, website, seen)
        website.status = WebsiteStatus.ready
        website.last_crawled_at = now
        website.next_crawl_at = _next_crawl_at(website.crawl_frequency)
        job_values["status"] = CrawlJobStatus.completed
        job_values["finished_at"] = now

    live = await session.scalar(
        select(func.count(WebsitePage.id))
        .where(WebsitePage.website_id == website.id)
        .where(WebsitePage.status != PageStatus.deleted)
    )
    website.pages_count = int(live or 0)
    job_values["frontier_size"] = await crawler_queue.pending_count(session, job_id)
    await session.execute(
        update(CrawlJob).where(CrawlJob.id == job_id).values(**job_values)
    )
    await session.commit()
    log.info(
        "crawl_finalized site=%s status=%s pages=%d chunks=%d",
        website.id, job_values["status"], website.pages_count, engine.chunks_total,
    )


async def _persist_page(
    session: AsyncSession,
    website: Website,
    url: str,
    depth: int,
    extracted: dict,
    checksum: str,
) -> int:
    """Upsert a WebsitePage + its chunks. Returns chunk count, or -1 if
    the page was unchanged (skipped)."""
    existing = await session.scalar(
        select(WebsitePage)
        .where(WebsitePage.website_id == website.id)
        .where(WebsitePage.url == url)
    )

    if existing is not None and existing.checksum == checksum and existing.status != PageStatus.deleted:
        existing.last_crawled_at = datetime.now(timezone.utc)
        existing.status = PageStatus.crawled
        return -1

    markdown = extracted["markdown"]
    plain = extracted["text"]
    word_count = len(re.findall(r"[A-Za-z0-9']+", plain))
    title = extracted["title"] or url
    classification = classify_url(url)

    page = existing
    if page is None:
        page = WebsitePage(
            website_id=website.id,
            organization_id=website.organization_id,
            knowledge_base_id=website.knowledge_base_id,
            url=url,
            version=1,
        )
        session.add(page)
        await session.flush()
    else:
        page.version = (page.version or 1) + 1

    page.title = title[:512]
    page.description = (extracted.get("description") or None)
    page.content = plain
    page.markdown = markdown
    page.checksum = checksum
    page.status = PageStatus.crawled
    page.status_code = 200
    page.language = extracted.get("language")
    page.content_type = "text/html"
    page.classification = classification
    page.word_count = word_count
    page.depth = depth
    page.last_crawled_at = datetime.now(timezone.utc)
    page.page_metadata = {
        "canonical": extracted.get("canonical"),
        "links_found": len(extracted.get("links") or []),
    }

    # chunk + embed
    epage = ExtractedPage(page=1, text=markdown, section=title)
    chunks = chunk_pages([epage], source_file=url)
    embeddings = _embed_chunks([c.content for c in chunks])

    await session.execute(
        delete(DocumentChunk).where(DocumentChunk.website_page_id == page.id)
    )
    for c, emb in zip(chunks, embeddings):
        meta = dict(c.metadata)
        meta.update({
            "url": url,
            "title": title,
            "source_type": "website",
            "classification": classification,
        })
        session.add(
            DocumentChunk(
                website_page_id=page.id,
                organization_id=website.organization_id,
                project_id=website.project_id,
                knowledge_base_id=website.knowledge_base_id,
                chunk_index=c.index,
                content=c.content,
                chunk_metadata=meta,
                embedding=emb,
            )
        )
    page.chunk_count = len(chunks)
    return len(chunks)


async def _mark_deleted_pages(session: AsyncSession, website: Website, seen: set[str]) -> None:
    """Pages that exist in the DB but weren't seen this crawl are marked
    deleted and their chunks removed from search."""
    rows = (
        await session.scalars(
            select(WebsitePage)
            .where(WebsitePage.website_id == website.id)
            .where(WebsitePage.status != PageStatus.deleted)
        )
    ).all()
    for page in rows:
        if page.url not in seen:
            page.status = PageStatus.deleted
            page.chunk_count = 0
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.website_page_id == page.id)
            )


def _next_crawl_at(frequency: str) -> Optional[datetime]:
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    delta = {
        "hourly": timedelta(hours=1),
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30),
    }.get(frequency)
    return (now + delta) if delta else None


__all__ = [
    "validate_url",
    "URLValidationError",
    "html_to_markdown",
    "classify_url",
    "discover_sitemap_urls",
    "run_crawl",
]
