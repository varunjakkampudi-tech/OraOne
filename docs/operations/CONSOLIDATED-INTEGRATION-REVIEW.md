# OraOne consolidated integration: review and acceptance

Date: 2026-10-15
Source baseline: main `ad87035170741b27202d0fdfbf171b674232862d`
Included history: `emergent` `0a60921d2d3f791f327438acb0dc65e0f85a66d8`, including every commit of existing draft PR #2.
Target: one reviewed PR into `main`, preserving existing history. **Do not merge PR #2 separately**: it is already an ancestor of this integration.

## Scope confirmed

- Retain all Emergent Batch 1 work: local-only QA login seed and OTP tests, 27 viewer-write permission guards, strict upload/type checks, safer branding delivery, dotenv precedence fixes, dependency updates, proxy retry, UI design refinements and cleanup evidence.
- Retain Batch 2 design/accessibility improvements and their original source/history.
- Make API-key RPM counters shared and atomic across workers using the existing Redis-backed cache, with fail-closed 503 if quota infrastructure is unavailable and no usage metering on denied requests.
- Use verified Cognito subjects and signed access-token cookies for user-specific API rate-limit buckets. Login/recovery remain IP-scoped to prevent identity rotation abuse.
- Reject unmetered API traffic on Redis failure in production/staging, preserving best-effort local development behavior.
- Fix the real-route audit classification: session verification/identity error screens must count as failures, not functional routes or successful aliases. Record authentication HTTP responses and fail audit execution on such errors.

## Evidence boundaries

- GitHub CI on the exact integrated commit must pass before this PR can be marked ready.
- Emergent's local evidence includes 289 backend tests, 27 Playwright fixture checks and live local API checks. Those reports must not be treated as independently re-executed production verification.
- The prior route report recorded 118/276 destinations with an authentication failure heading and 146/276 destinations with browser errors. It must be rerun using this stricter audit tool; the old report is retained as historical evidence.
- The old route report's claim of `functional` denotes rendered content, **not** functional acceptance against every API.
- The production Auth provider remains Cognito; the seeded `test@oraone.in` account is restricted to loopback development and does not provide a production backdoor.

## Remaining release blockers (not fixed/waived by this PR)

1. **Database migration ↔ model parity:** Emergent's `alembic check` reported drift on indexes, defaults and constraints; reconcile against a disposable migrated PostgreSQL before authoring a reviewed migration. Never guess the DDL from a markdown description.
2. **Production identity:** owner-controlled Cognito user-pool configuration and live signup, refresh, recovery and logout tests.
3. **Live email:** SES/SMTP credentials and real OTP, invitation, escalation delivery.
4. **Deployment and disaster recovery:** domain/TLS, externally reachable Hostinger deployment, monitoring, rollback, off-host encrypted backups and timed restore.
5. **External integrations:** provider authorizations, real webhook delivery, browser-embedded widget in third-party origin, embeddings/provider fallback and quota exhaustion.
6. **Accessibility:** manual keyboard and assistive-technology audit after automated axe.
7. **API plans:** `/api/v1` free-plan entitlement is intentionally disabled at `api_rpm=0`; do not expose a paid API until pricing, distributed quota and usage/cost gates pass.
8. **Security:** test signed-caller throttling under Cognito, high concurrency across workers, Redis outages and DoS response behavior in a production-equivalent environment.

## Reviewer merge procedure

1. Confirm this PR includes the PR #2 commit history and Emergent branch via commit ancestry.
2. Confirm current main SHA and PR mergeability; if main advances, refresh integration branch and rerun checks.
3. Require application checks and frontend lint/format checks to pass on the exact PR head.
4. Inspect the diff, absence of secrets, and critical permission/auth configuration.
5. Merge **only this PR** into main (squash or merge as appropriate to release policy).
6. Close PR #2 as superseded if it remains open; do not merge separately.
7. Verify main contains the resulting commit and rerun protected checks.
8. Remove obsolete branches through GitHub's branch deletion controls after confirming the merge and any Emergent synchronization requirements. Branch deletion is separate from merging.

**Status:** this PR consolidates code, not a declaration of public production readiness.
