# OraOne Product 1: delivery scope and production acceptance

**Audit baseline:** `ad87035170741b27202d0fdfbf171b674232862d` (14 October 2026).
This document is a work plan, **not** certification of production readiness.
The repository's `README.md`, `docs/design/PRODUCT1_CLOSURE.md`, and
`docs/operations/RELEASE-CHECKLIST.md` remain source evidence.

## Observed current state

- One production-target frontend (`frontend/`), React/Vite, FastAPI backend,
  PostgreSQL/pgvector, Redis, MinIO, and the published website widget SDK.
- `frontend/e2e/route-inventory.json` contains **283** reference destinations,
  not 283 distinct real backend modules. Compatibility/preview routes are
  intentionally present. The older 272-path product brief is not exhaustive.
- Earlier import-graph cleanup removed 65 unreachable files; don't re-delete
  retained, dynamically imported, SDK, migration, or future-product assets
  without fresh reachability and dependency evidence.
- GitHub application and frontend-lint workflows succeeded at the baseline SHA.
  Browser-route tests mostly use contract-shaped fixtures, not real services.
- `AUTH_PROVIDER=self_hosted` is supported for local development only.
  `app.core.config.Settings` explicitly requires Cognito in staging/production.
- Products 2–9 and OraOne OS are **planned preview surfaces**, not production
  features. Only Product 1 is the current functional delivery target.

## Delivery streams

### 1. Repository hygiene (non-destructive)

Establish clean baseline, lockfile and dependency audit, exact import graph
(ESM and dynamic imports), duplicate component/CSS inventory, dead asset scan,
documentation/route reconciliation, and source-generated artifact isolation.
Remove files only with import/call-site references, migration/SDK/worker use,
and browser regression evidence. Preserve Git history, migration chains,
record-scoped URLs, test IDs, and the exact approved OraOne logo.

### 2. UI coverage and brand acceptance

Inventory **all current reachable routes**, plus the 283 reference URLs.
Classify each URL as live functional, alias/redirect, empty/error state,
preview-only, admin-restricted, or unsupported. Test each relevant visual
state at 320, 390, 768, 1024, 1440 and 1920 pixels. Compare canonical
screens against approved Brand, Marketing, Auth V3, Onboarding, Dashboard and
Admin references. Do not advertise preview products as available or invent
prices, certifications, customer data, or integration status.

### 3. Product 1 functional acceptance

Record real persisted evidence for all supported operations:

- Workspace onboarding, accounts, membership, RBAC, session revocation.
- Agent CRUD, agent-scoped knowledge binding, prompts, model configuration,
  testing, versioning, publishing and widget install.
- Document/website intake, parsing, embedding, retrieval quality, source
  provenance, fail/retry/partial status, deletion, tenant containment.
- Public embed across allowed origins; secure widget rate limits and CORS;
  conversation continuity, grounded answers and escalation boundaries.
- Inbox pagination/deep links, conversations, lead capture, contact profiles,
  activity and analytics with consistent actual persisted data.
- Integration OAuth/token lifecycle, explicit unavailable state, webhooks,
  idempotency and error retries.
- Usage metering, quotas, accurate plan/entitlement enforcement, no paid
  billing claims without a verified provider.
- Platform and tenant authorization separation, user/admin negative tests,
  audit history, privacy and deletion workflows.

For each capability distinguish real live-endpoint checks from mock-only E2E.

### 4. Identity decision and local QA

The opt-in seeded `test@oraone.in` account is **only for developer machines**,
never production or shared staging. Its password is supplied at execution,
Argon2-hashed in the local DB, and the ordinary OTP step stays enabled.

**Production conflict:** the current backend deliberately fails startup in
production/staging unless Cognito is configured. Owner must choose a supported
production authentication path before GO:
- finish and live-test the existing Cognito configuration; or
- explicitly approve a separately engineered, independently reviewed
  production self-hosted identity project (sessions, cookies, CSRF, recovery,
  verified email, abuse controls, account takeover, audit and incident response).

Skipping Cognito **setup now** is compatible with continued local development.
It is **not** authorization to disable the production security gate.

### 5. External release/operations

Complete credentialed inference and quotas, real email delivery, external
integrations and webhook retries, container secrets, network egress/SSRF
defenses, RBAC/tenant negative tests, security scans, database migration
review, backups **and timed restores**, observability/alerts, rollback drill,
TLS/DNS, capacity/load testing, privacy/legal reviews, actual production
deployment checks. Test the final immutable commit and pinned container images.

## Acceptance ledger

For each task require:

`ID | requirement | route/API | current state | dependency | test | evidence SHA | reviewer | verdict`

Allowed verdicts: PASS, FAIL, BLOCKED, NOT TESTED, NOT APPLICABLE.
Unverified external integrations remain BLOCKED or NOT TESTED, not PASS.

**Definition of production GO:** the current release checklist and this
ledger contain no unresolved Critical/High issues, all required verified
operations are green on the same release SHA, and operator-controlled external
gates are signed off. Repo cleanup or 283 route smoke renders alone are
insufficient.

## Suggested execution order

1. Inventory + no-regression baseline; fix P0/P1 defects first.
2. Local tester fixture and auth negative tests, without changing production.
3. Primary Product 1 happy path, actual API and browser smoke.
4. Knowledge/inference/widget reliability and security.
5. Inbox/lead/analytics + tenant isolation.
6. UX/visual parity, marketing/auth/onboarding/admin shells.
7. Observability, load, security, backup/restore, staged deploy/rollback.

Use small, risk-bounded PRs; keep future-product design previews isolated.
No bulk deletion or direct `main` edits. Publish verified status, not a
percent-complete estimate inferred from route count.
