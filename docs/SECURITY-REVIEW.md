# OraOne principal security review

This is a repository review, not a penetration test or certification.

| Finding | Severity | State | Evidence / next action |
|---|---:|---|---|
| Development database password fallback in production Compose | Critical | Fixed | Required `DB_PASSWORD` substitution |
| Development MinIO credential fallback in production Compose | Critical | Fixed | Required MinIO substitutions |
| Direct publication of stateful/app service ports | High | Fixed | Only Caddy publishes host ports |
| Legacy EC2/Pages deployment paths | High | Fixed | Workflows and EC2 stack removed |
| HS256-only authentication | High | Fixed in code / live cutover unverified | Cognito JWKS validation and email-only session flow are implemented; production live cutover remains untested |
| Documented local admin default | High | Fixed in template | Empty values now required; no DB mutation performed |
| Unsafe AI fallback in production | High | Fixed in code / live provider unverified | Production-like environments reject explicit mock inference; credentialed provider failure behavior still needs live verification |
| Billing, crawler, uploads, prompt injection | High | Partially verified | Free-access billing is disabled and targeted SSRF/security tests pass; live provider, egress and adversarial prompt-injection validation remain unverified |
| Customer webhook SSRF | High | Fixed in code / infrastructure follow-up | Public-host validation, delivery-time revalidation and redirect blocking are tested; deployment egress policy remains required |
| API-key idempotency | High | Fixed in code | Public API no longer keeps a process-local replay map; centralized middleware uses the shared idempotency cache and fails closed when unavailable |
| Distributed auth/rate-limit state fallback | High | Fixed in code / runtime unverified | Production-like environments now fail closed when Redis is missing or unreachable; local development may still use in-process state |
| Production mock inference | High | Fixed in code | Production-like environments reject `AI_ALLOW_MOCK=true` unconditionally |
| Payment runtime dependency | High | Disabled by policy | Free-access mode rejects paid checkout and Stripe webhooks; no payment integration is required for the current product policy |
| Tenant AI spend ceiling | High | Open | Daily AI-message quota exists; monetary/token budget reservation and reconciliation are not yet implemented |
| Webhook delivery durability | High | Fixed in code / locally tested | Durable outbox worker performs delivery, records one row per endpoint/event identity and retries failures; external endpoint delivery remains untested |
| Backend dependency vulnerabilities | High | Fixed locally / hosted install unverified | Dependency floors were raised; current local `pip-audit` reports no known vulnerabilities. Re-run in the production build environment before release |
| RBAC migration privilege preservation | High | Fixed in code / production unverified | Legacy owner/admin values map to platform admin; production backup, migration and rollback remain unverified |
| Secrets in repository history | High | Open | Scan history before any public-release decision |

## Current local evidence

- Backend: `159 passed` from the configured backend test root, including post-fix webhook/OAuth coverage.
- Frontend E2E: `5 passed` covering Cognito entry points, PKCE/state binding,
  recovery navigation, protected API access and logout.
- Frontend production build: passed.
- Frontend ESLint: `0 errors, 0 warnings` under the strict `lint:check` gate.
  unused imports/variables and unused suppression directives, not suppressed
  security or hook errors.
- Cognito identity provisioning now requires an explicit positive
  `email_verified` signal from claims or the userinfo response.

The latest hosted CI evidence before the current working changes recorded
passing backend, lint/format, build and serial E2E gates. The current source
also includes durable webhook event identity, one-time OAuth state consumption,
and the role-preserving migration correction; these changes require a fresh
hosted run before release.

Production database migration/backup evidence, live inbox testing, external
webhook delivery, billing-provider verification, provider usage/cost
reconciliation, and secret-history scanning remain unverified.

No production GO is allowed until Critical and High findings are fixed and
independently verified or explicitly accepted by the product owner.
