# Product 1 acceptance ledger

Batch: `qa/product1-acceptance-batch1`, built on PR #2 head `ebf08f5`
(baseline `ad87035`). Evidence SHA is the batch commit created when this branch
is pushed. All runs used a **local loopback** stack: PostgreSQL 15 + pgvector
0.8.0, Redis 7, an S3-compatible store (SeaweedFS 3.80, standing in for MinIO,
whose community binaries are no longer published), the FastAPI API and the Vite
UI. Real AI inference used OpenRouter `openrouter/free` (zero token price).

Allowed statuses: PASS, FAIL, BLOCKED, NOT TESTED, NOT APPLICABLE.
"Reviewer decision" stays **PENDING** until an independent reviewer signs it.

## Verdict

**Product 1 is NOT production-ready.** Local functional, isolation and security
acceptance pass. The external release gates (identity, deployment, TLS,
monitoring, production backups) are still BLOCKED, and the WCAG contrast work
is still FAIL.

## Evidence scripts (all loopback-only, synthetic data, self-cleaning)

| Script | Result |
| --- | --- |
| `backend/scripts/verify_product_local.py` | 38 checks, 0 failures (real grounded OpenRouter answer) |
| `backend/scripts/verify_security_local.py` (new) | 93 checks, 0 failures |
| `backend/scripts/verify_local_test_account_flow.py` (new) | 14 checks, 0 failures |
| `backend/scripts/verify_storage_recovery_local.py` (new) | 15 checks, 0 failures (S3 and API restart, re-read and retrieval) |
| `backend/scripts/backup_restore_drill.py` | DRILL PASSED (row counts match) |
| `backend/scripts/api_health_smoke.py` | 169 routes, no 5xx |
| `backend/scripts/load_test_local.py` (new) | see Operations |
| `python -m pytest` (backend) | 289 passed (244 at start of batch + 45 new) |
| `npm run lint:check`, `format:check`, `build`, `test:sdk` | pass |
| `npx playwright test` (fixture suite) | 27 passed |
| `frontend/e2e/real-route-audit.mjs` (new) | see [ROUTE-ACCEPTANCE.md](ROUTE-ACCEPTANCE.md) |

## Functional ledger

| Feature | API / route | Status | Tests / evidence | Blocker |
| --- | --- | --- | --- | --- |
| Identity, OTP login, org onboarding | `/api/auth/*`, `/api/auth/identity` | PASS | product verifier; QA-account lifecycle | Production Cognito (see Identity) |
| Workspace / project management | `/api/projects`, `X-Project-Id` | PASS | product + security verifiers (foreign project → 404) | — |
| Agent create / edit / delete | `/api/agents` | PASS | security verifier (owner delete → 404 after) | — |
| Agent instructions and configuration | `PUT /api/agents/{id}` | PASS | prompt and max_tokens persisted; KB binding round trip | — |
| Model selection | `/api/ai/models`, agent `model` | PASS | `openrouter/free` pinned and used | — |
| Provider fallback | `model_router_service.ordered_chain` | PASS (unit) / NOT TESTED (live) | `test_ai_provider_fallback.py` | Only one live provider configured |
| Knowledge bases | `/api/knowledge-bases` | PASS | both verifiers; BOLA checks | — |
| Document upload and processing | `/api/documents/upload` | PASS | processed with chunks and embeddings; exe/spoofed PDF → 415 (fixed) | — |
| Website crawling and ingestion | `/api/websites` | PASS | real crawl of example.com → page stored → searchable | — |
| Embeddings and vector retrieval | `/api/knowledge/search` | PASS (hash provider) | retrieval survives restart | Production embedding provider (Bedrock) not credentialed: BLOCKED |
| RAG-grounded responses | `/api/widget/chat`, conversation messages | PASS | phrase-grounded answers via real model; one earlier playground run with the free model was not grounded, so it is model-dependent | — |
| Playground / testing | `/api/conversations/{id}/messages` | PASS | real AI reply + history persisted | — |
| Deployment configuration | `/api/agents/{id}/deploy` | PASS | product verifier | — |
| Widget install / public widget API | `/api/widgets`, `/api/widget/*`, SDK | PASS | publish, domain allow-list (foreign origin 403), session, chat, lead, escalate; SDK test | Third-party site embed not tested |
| Public REST API v1 | `/api/v1/*` | BLOCKED | invalid key 401; valid key → 402 because the free plan has `api_rpm=0` | Owner plan decision |
| Conversation storage and history | `/api/conversations` | PASS | ≥2 persisted messages; cross-tenant 404 | — |
| Customers and leads | `/api/leads`, `/api/widget/lead` | PASS | CRUD + widget capture visible to owner tenant only | — |
| Human escalation | `/api/widget/escalate` | PASS (API) / NOT TESTED (delivery) | 200 persisted | No SMTP / inbox delivery configured |
| Analytics and activity | `/api/analytics/*`, `/api/activity` | PASS (API) | 200 with real data; numeric accuracy not independently audited | — |
| Webhooks | `/api/webhooks` | PASS | create, secret rotation, private-IP target 422, cross-tenant delete 404; signing/outbox unit tests | Live delivery to external receiver NOT TESTED |
| Third-party integrations (OAuth) | `/api/integrations` | BLOCKED | list 200; legacy simulated connections fail closed | Owner OAuth credentials and consent |
| Team permissions | `/api/team/*` + all write routes | PASS (after fix) | invite → accept → viewer read-only → removal revokes; 30 regression tests | — |
| Audit logs | `/api/audit-logs` | PASS | entries present after mutations | — |
| Usage metering and quotas | `/api/usage`, `enforce_quota` | PASS (metering) / PASS (unit quotas) | usage snapshot; `test_entitlements.py` | Live quota exhaustion NOT TESTED |
| Billing / payments | `/api/billing/*` | NOT APPLICABLE | Free-access-only policy (`test_free_access_policy.py`) | — |

## Security and reliability

| Control | Status | Evidence |
| --- | --- | --- |
| Tenant isolation / broken-object authorization | PASS | 14 cross-tenant read/update/delete probes → 404; list excludes foreign data |
| Organization RBAC | PASS (fixed) | **Defect:** a `viewer` could create/update agents, KBs, documents, websites and leads. Fixed with `require_permission` on 27 write routes |
| Platform RBAC | PASS | user role → `/api/super-admin/me` 403, admin stats denied |
| Session, refresh rotation, revocation | PASS | rotated refresh reuse 401; refresh after logout 401; OTP single-use |
| Authentication rate limiting | PASS | 429 at the 11th login attempt per minute |
| Proxy-aware rate limiting (production) | PASS (fixed config) | **Defect:** Compose had no `TRUSTED_PROXY_IPS`, so behind Caddy every client shared one bucket. Default now trusts private Docker ranges |
| CORS (management vs public widget) | PASS | foreign origin gets no ACAO on `/api/agents`; widget origin allow-list enforced |
| CSRF / cookies | PASS (unit) | `test_auth_cookies.py` (HttpOnly, SameSite) |
| Security headers | PASS | API: nosniff, DENY, referrer policy, CSP |
| File-upload validation | PASS (fixed) | **Defect:** any file type was accepted. Allow-list + signature checks added |
| Brand-asset stored XSS | PASS (fixed) | **Defect:** SVG/typed images trusted the client content-type and were served same-origin. Signature checks + `CSP: sandbox` + nosniff added |
| SSRF / crawler controls | PASS | loopback, metadata IP, RFC1918, `file://` rejected for crawler, URL source and webhooks |
| Prompt-injection resistance | PASS (limited) | system-prompt canary not leaked on a direct override probe; not an adversarial red-team |
| Provider timeouts / retry / idempotency | PASS (unit) | provider error translation; `test_idempotency_concurrency.py` |
| Webhook signing / outbox recovery | PASS (unit) | `test_webhook_security.py`, `test_webhook_outbox.py` |
| Sensitive-data redaction | PASS (unit) | `test_email_log_privacy.py`; scripts never print OTPs or answers |
| Dependency audit | PASS (fixed) | `pip-audit`: cryptography 46.0.7 had 4 advisories → pinned `>=50.0.2,<51`; npm audit 0 |
| Secret scan | PASS | gitleaks (history + tree): only `YOUR_API_KEY` doc placeholders; local `.env` is git-ignored |
| Production auth guard | PASS (unchanged) | `test_production_fail_closed.py`; self-hosted auth still refused in staging/production |

## Operations

| Gate | Status | Evidence / blocker |
| --- | --- | --- |
| Migrations from empty DB | PASS | `alembic upgrade head` on two fresh databases |
| Migration ↔ model parity | FAIL (MEDIUM) | `alembic check` reports drift: server defaults, several FKs/indexes, `widgets.public_key` unique. Needs a reviewed migration |
| Migrations honor explicit env | PASS (fixed) | **Defect:** `alembic/env.py`, `bootstrap_db.py` and `backup_restore_drill.py` loaded `.env` with `override=True`, so they could migrate or restore the wrong database |
| Backup and restore | PASS (local) | restore drill; production encrypted backups BLOCKED |
| Object-storage persistence and restart | PASS (local) | S3 + API restart, re-process reads stored bytes |
| Load (local, 4 vCPU, 4 gunicorn workers) | PASS (indicative) | 60 s × 40 conc: ~64 rps, 0 errors, p95 1.3–2.4 s (generator on the same host) |
| Soak through Caddy with retry policy | PASS | 180 s × 10 conc, 19,177 req, 39 forced worker recycles, 0 errors. Without Caddy, recycling dropped 23 of ~21k requests, so `lb_try_duration` was added |
| Accessibility (WCAG 2.2 AA) | FAIL (improving) | axe critical/serious: 74 → 42 of 276 routes after token, contrast and label fixes. Remaining: mostly `#64748B` on tinted chips and status pills |
| Responsive layout | PASS | 0 of 276 routes overflow horizontally at 390, 768 or 1440 px; 0 API 5xx; 0 navigation timeouts ([ROUTE-ACCEPTANCE.md](ROUTE-ACCEPTANCE.md)) |
| Production identity (Cognito) | BLOCKED | External gate: live pool, hosted UI, logout, refresh, user migration |
| Production deploy, TLS, DNS, monitoring, rollback | BLOCKED | No release authorization; public deployment untouched |
| Real email delivery (OTP, invites, escalation) | BLOCKED | SMTP/SES credentials not provided |
