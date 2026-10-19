# OraOne OS — Engineering, Security, Testing and Operations Standards v2.1

Status: Proposed, subject to owner approval. Product contract: OraOne-OS-Master-Product-Spec-v2.1.md. Source: preserve current OraOne Git history, production configuration and useful code. Coverage: all ten portfolio modules unified in OraOne OS, including backend, frontend, widget, provider connectors, call infrastructure, workers, integrations, admin, analytics, marketplace, documentation and CI/CD.
## 1. Architecture baseline and direction
Observed: React 19 / Vite 7 / JavaScript / Tailwind 4 / React Router / TanStack Query frontend; FastAPI / Python / Pydantic / SQLAlchemy / Alembic backend; PostgreSQL + pgvector; Redis; S3-compatible object storage (MinIO, no AWS); Docker Compose / Caddy / Hostinger; Cognito auth (being replaced, no AWS: spec OS-01, D21), Stripe foundations, background workers and transactional outbox, JS widget SDK. These are repository observations, not validation. Reaudit at current SHA before changes.

Preserve first: migrations, routes, public contracts, RBAC and deployment architecture until compatibility analysis proves a change safe. Modular monolith with domain packages and separately scaled workers is the default; do not start ten backends or rewrite React/FastAPI solely for fashion. Adopt TypeScript incrementally only after owner approval and compatibility testing. Real-time voice media runs through the telephony provider's media streaming and a separately scalable voice service, not the main API process (spec section 4.4). Schema evolution is additive, backward compatible and rollback-aware. Frontend/business objects may share typed OpenAPI-generated contracts without a big-bang rewrite.

Domain boundaries: identity-tenancy; contact/lead/opportunity; conversation and channel adapters; consent/compliance; campaign and dialing eligibility; voice runtime and media; AI gateway and knowledge; workflows/events; integrations; studio; marketplace; analytics; billing/cost; admin/feature flags/config publication; ops/telemetry; privacy/export/deletion. Each has explicit schema, API, events, ownership and test suite. No direct arbitrary cross-domain database mutation. All cross-cutting authorizations enforced server-side.
## 2. Code hygiene and dependencies
- Python: Ruff lint and format on all tracked applicable .py files; type hints for public/new code; mypy or equivalent gradual clean boundary; Pydantic validation; no blanket except, unsafe dynamic SQL, unreviewed suppressions or blocking IO in async handlers.
- Frontend: ESLint and Prettier check on all supported tracked project source/config/document formats, not only src/**/*.jsx. File-specific parsers/configs for JS/JSX/TS/TSX/JSON/YAML/CSS/Markdown; generated/minified files, lockfiles, binary assets and snapshots are deliberately excluded and documented. Do not falsely demand Prettier parse unsupported files. Enforce no new errors and a cleanup plan for existing violations.
- TypeScript migration, when approved: incremental, strict config on new modules, OpenAPI contracts, safe compatibility gates. Avoid two frameworks or duplicated validation libraries.
- Pin and inventory direct/transitive dependencies, generate an SBOM, review licenses and provenance, scan CVEs and transitive packages, deprecate/remove genuinely unused packages and legacy flows safely. A package's age alone isn't justification for removal. Test startup/build/runtime and rollback; never delete historical migrations or third-party assets requiring licenses without evaluating impact.
- Every code/module change requires consistent tests, docs and observable errors; no production debug bypass, secrets, unbounded queries, invented business data or hidden feature activations.
## 3. API, data and tenant security
- Deny by default using authenticated user + org + project + role + field/resource ownership; reject IDOR/BOLA/BFLA on read/write/search/export/import/merge/async jobs/real-time streams/widget/session URLs/attachments/call media.
- Pydantic schemas with strict size/type/enum limits, safe output encoding and content-type policy; parameterized SQL; allowlisted sorting/filtering; cursor pagination, upper bounds and indexed query plans. Input validation at boundaries, not as sole substitute for authorization.
- HTTP headers: HSTS on HTTPS domains after TLS readiness; CSP with nonces/hashes and compatible widget guidance; frame-ancestors; X-Content-Type-Options; Referrer-Policy; Permissions-Policy; secure SameSite/HttpOnly cookies; CORS origin allowlist; CSRF defense for cookie-auth mutations; clickjacking and cache-control checks. No guessed headers that break approved widget embeds.
- Structured secrets management, rotation and scoping; TLS everywhere; token encryption and expiry; request signing/webhook HMAC validation and replay defense; no user-provided arbitrary URLs without SSRF guards and egress restrictions. Upload malware scanning/sandboxing and archive bombs defense.
- PostgreSQL migrations parity and upgrade/downgrade on disposable migrated DB; backups and tested point-in-time recovery; Redis key namespace isolation; encryption and retention for object storage/media, expiring links; no sensitive raw payloads in error/log exports.
- No data training/sale/secondary reuse. Consent records per channel/purpose/time/source; DSAR access/rectification/deletion; retention and backup purge rules; processor inventory and region/data transfer review. Proof of lawful basis remains owner/legal gate.
## 4. Outbound voice, social and AI controls
- Central Action Policy Engine checks tenant actor/roles, verified sender/channel/provider permissions, customer consent/eligibility, DND/suppression, contact cadence/time zone, template/windows, call limits, recording disclosures, budget reservation, destination allowlist, feature flag and kill switches at enqueue and at execution.
- XLSX/CSV never authorizes calls: quarantine incomplete/invalid/unconsented rows; preview counts and rejection reasons; operator approves eligible subset. Idempotent campaign/outbound scheduler, cancellation, policy reevaluation, signed provider callbacks, reconciliation, and fail-closed on policy outages.
- Official Meta WhatsApp/Instagram APIs only; provider adapter capability matrix. Voice provider selected by verified telecom permissions, geography, rates, recording/AI requirements. Scripts cannot bypass provider account limitations; prohibited cold robocalls and fake identities are excluded.
- Model is an untrusted recommender: typed tool allowlists, prompt-injection regression, grounded RAG, human escalation, deterministic approval for sending/calling/publishing, budget/latency limits, versioned prompts, provider retention settings and evaluation. No unsafe automatic claims about caller sentiment, consent, purchase or delivery.
- Transactional outbox, idempotent workers, backpressure, bounded retries/DLQ, causal trace events, poison-message handling, replay tests, safe worker shutdown. Exactly-once external delivery cannot be assumed; design for at-least-once delivery with side-effect idempotency.
## 5. UI/UX, accessibility, browser and SDK
- Premium shared OraOne design system: stable logo, tokens, navigation, density, data tables, search/command palette, role-aware modules, loading/empty/error/offline/overquota/permission states, clear status and undo where safe. Distinguish alpha/beta/available/future modules.
- Responsive at 320, 360, 390, 768, 1024, 1280, 1440, 1920 widths; keyboard/touch and screen reader; WCAG 2.2 AA, automated axe and recorded manual keyboard/assistive tech testing, 200/400% zoom, focus management, contrast, reduced motion and localization.
- Playwright Chromium, Firefox, WebKit; actual Safari and mobile device tests when available. End-to-end scenarios include admin config, website embed on a foreign origin and partner-domain CSP, social/telephony approved mocks, resilience/failure messages and time-zone behavior.
- Widget loader versioned and independently tested for compatibility, script installation/removal, consent disclosure, performance overhead, domain allowlist and security headers.
## 6. CI/CD and deployments
Mandatory GitHub Actions trigger matrix:

| Trigger | Required execution |
|---|---|
| Every development push | Ruff/format, ESLint/Prettier all applicable files, type checks, backend and frontend unit, widget SDK, dependency+SBOM+license and secret scans, builds |
| Every development integration | All above + real disposable PostgreSQL/Redis/MinIO fixture integration, migrations and model parity, tenant denial, API contracts, admin/config tests, critical Chromium E2E, smoke/sanity, coverage |
| Every major module | Relevant functional + negative/abuse/failure/recovery, all-browser E2E, accessibility, performance and security review |
| Nightly | Full regression and module matrix, all engines, fault recovery, prompt-injection, quotas, integration mocks, localization, accessibility, security audit |
| workflow_dispatch manual | Allowlisted tests: unit/integration/smoke/sanity/critical/regression/E2E/a11y/responsive/security/dependency/secret/DB/calling simulator/voice/WhatsApp/Instagram/workflows/marketplace/admin/analytics/load/restore/all; environment restricted to CI/staging; browser and module selection |
| Staging before deployment | Build provenance, migration, secrets/deps/CI, disposable dry-run, critical flows; environment guard and approval |
| Staging after deployment | Smoke/sanity/API/DB/Redis/object-storage/worker/queue/chat/widget/lead/admin and enabled-channel mock or test-account flows; critical E2E; rollback and incident verification |
| Owner manual production from main | deploy-hostinger.yml only, explicit typed confirmation, protected GitHub production environment with required reviewers, exact SHA and immutable artifact, all applicable launch gates green, backed-up DB, safe migration, deployment, postdeploy smoke/sanity/critical test, observability check and tested rollback; no auto-deploy on push |

No agent autonomously dispatches a production workflow, modifies production secrets or bypasses environment review. Production deployments are owner-only. A green CI build never proves live-provider or commercial readiness. A failed gate blocks; collect redacted evidence, fix and rerun. GitHub Actions branch protection and required check names must match real workflow behavior. Permissions minimal, actions pinned to reviewed immutable SHAs, secrets limited by environment, artifact retention specified, untrusted PR workflows not allowed to see privileged secrets. Nightly runs must actually execute once before marked verified. Distinguish deploy configuration from actual Hostinger/remote system validation.
### 6.1 Observed CI baseline (commit 10a6fdd)

- `application-checks.yml` and `frontend-lint.yml` run only on pushes and pull requests to `main`. Development-branch, nightly, and manual triggers must be added
- `frontend-lint.yml` runs `lint:fix` and `format`, fails if they change any file under `frontend/src`, then runs `lint:check` and `format:check`. Keep this pattern; extend it beyond `frontend/src` to the other supported tracked files (section 2)
- `deploy-hostinger.yml` is manual (`workflow_dispatch`), runs only on `main`, needs a typed DEPLOY confirmation, and uses the `production` environment. Record whether that environment has required reviewers; if not, that is an owner action
- Actions are pinned by tag; new and changed workflows pin by full commit SHA
- No coverage, dependency audit, SBOM, license, or secret scanning observed

### 6.2 Definition of done commands

Use the repository's real script names once confirmed; these are the expected checks:
1. `ruff check` and `ruff format --check` (backend)
2. ESLint with zero warnings and Prettier check on all supported tracked formats (frontend and widget)
3. Type checks: mypy on changed backend modules (once adopted); TypeScript checks on any approved TypeScript
4. `pytest` with coverage thresholds (section 7)
5. Alembic upgrade, downgrade, and model parity on a disposable migrated database
6. Tenant and role denial suite
7. Widget SDK tests
8. Critical Playwright journeys on Chromium; all three engines at module completion and nightly
9. Accessibility and responsive checks on changed screens
10. Dependency, SBOM, license, and secret scans with no unaccepted high or critical findings
11. Frontend, widget, and backend container builds
12. Feature flag defaults: gated modules, live channels, outbound sending, and calling off

### 6.3 Autonomous mode

When OraOne-OS-Autonomous-Goal-v2.1.md runs an agent loop:
- Pull-request requirements apply as development-branch integration requirements, using the mapping in Goal section 1.1. Every applicable check runs; no threshold is reduced
- Per-change human approval is replaced by an independent review in a separate agent session; if it cannot run, it is never claimed and the limitation is recorded in `blocker.txt`
- The agent never pushes to `main`, never dispatches `deploy-hostinger.yml` or any `production` environment job, and never changes production configuration or secrets
- Owner review before promotion is required for: authentication and sessions, tenancy and RBAC, the policy and consent engine, migrations touching personal data, outbound messaging and calling, billing and cost caps, admin config publication, and deletion and data rights

## 7. Security audit and remediation
- OWASP Top 10 Web, API Top 10, LLM Top 10; dependency/vuln scan, SAST, secret history, SBOM/license, DAST on isolated staging, auth and business logic abuse, file parsing, session/cookie/header/CSP, rate limit/DoS, webhooks replay, network isolation, backup exfiltration, provider token leak and marketplace supply-chain threat modeling.
- Each finding: severity, exploitability, affected version, reproduction evidence, root cause, change, regression tests, independent review, verification and owner acceptance if any. Confirmed critical/high security issues block affected release; only owner may document a residual acceptance when lawful and defensible. Never silently waive.
- Coverage goal: changed backend ≥80% lines and ≥70% branches; new frontend tests measured and thresholds defined after baseline; 100% tested critical policy decision branches including denies (not a substitute for adversarial tests). All available unit/integration/critical path suites green.
## 8. Operational resilience and observability
- Trace IDs propagate browser/widget → API → outbox/worker → provider webhooks → lead/call and admin events. Structured allowlist telemetry with hashed tenant/user IDs and bounded retention; never log raw prompts, transcripts, call audio, private message bodies, password/token data or full phone lists.
- Searchable error fingerprints, alerts, traces and authorized redacted admin log export with approval/audit. Publish runbooks for incident categories, feature kill switches, recovery, backup/restore, compromised token, abusive campaign, social account suspension and telephony provider outage. Measured detect/acknowledge/mitigate targets, never guaranteed fixes in seconds.
- Hostinger VPS capacity reviewed for CPU/RAM/storage/network/region, quotas and external media provider requirements; per-service limits, Caddy TLS, non-public databases, DNS controls, security patching, independent alert path, off-host encrypted backups and validated restore. No destructive tests on production.
## 9. Admin configuration publication and beta release
- Version every config and feature flag with draft → validate → stage/test → approve → publish → monitor → rollback. RBAC, separation-of-duties for sensitive global actions, reason/ticket, audit, protected secret handling and exact environment/tenant targeting.
- Feature flags support tenant/user/cohort/environment and dependencies; closed beta experiments must pass every applicable security, privacy, compliance and platform gate. A product module not approved for external provider access remains off even for beta.
- Content/marketplace/social publishing is distinct from code deployment; admin publication never implies GitHub deploy permission, third-party posting permission or provider template approval.
## 10. Documentation and acceptance
- Keep current documentation paths as canonical when possible. Maintain comprehensive feature/screen/journey/provider-rights/test/evidence/gap matrices and PROGRESS.md, QUALITY_AUDIT.md, actionable blocker.txt.
- Public docs and oraone.in must accurately distinguish available, beta, planned and illustrative demos; remove dummy numbers, quotes, logos, fake functional screens and test-only data before production readiness.
- Test every currently enabled product with: happy path, edge cases, invalid input, tenant/role denial, consent/DND, concurrency/replay, provider outage, cost cap, data deletion, accessibility, mobile, three browsers and restore/failback. Track NOT_DUE only for modules explicitly not in target release.
- Definition of done: actual code + tests + CI exact SHA + manual accessibility evidence where required + independent audit + operational evidence + docs + security review + no critical/high blockers for activated functions. Deployment, provider verification and user acceptance have separate evidence levels.
## 11. Owner-exclusive authority
Owner must approve full OS spec and vendors/pricing/telecom compliance, social app permissions, real campaigns/contacts, marketing publication scopes, legal/privacy policies, payment setup, production credentials/infrastructure, release gates, production merge and manual Hostinger deployment. Autonomous agent can build/validate in dev and isolated staging; no real calls or unsolicited outreach without validated permission and explicit owner approval.

---

## Amendment 2026-10-20 — No AWS, no repository names (owner decision, global CR-02)
- Amazon Cognito and all other AWS services are removed from scope because of cost. Identity is application-managed in the FastAPI backend: secure `HttpOnly` session cookies with rotation, Argon2id password hashing and/or email one-time codes, TOTP MFA and step-up for privileged roles, session and device revocation. Object storage uses an S3-compatible, non-AWS service (MinIO on the owner's host or another approved provider).
- New decision **D21**: choose the replacement sign-in method(s) and the email delivery provider, and approve the migration plan for any existing Cognito users (re-verification by email, no password export). Until D21, build the application-managed identity behind a flag and keep existing Cognito code paths untouched but marked for removal; record the migration as READY_FOR_OWNER.
- Removing Cognito code follows the proven-unused deletion rule and lands only with passing authentication, session, tenancy and MFA tests (gate G04).
- Documents and commit messages never contain repository names or repository links.
