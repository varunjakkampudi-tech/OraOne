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
| Billing, crawler, uploads, prompt injection | High | Open | Independent review and targeted tests remain required |
| Customer webhook SSRF | High | Fixed in code / infrastructure follow-up | Public-host validation, delivery-time revalidation and redirect blocking are tested; deployment egress policy remains required |
| API-key idempotency | High | Fixed in code | Public API no longer keeps a process-local replay map; centralized middleware uses the shared idempotency cache and fails closed when unavailable |
| Production mock inference | High | Fixed in code | Production-like environments reject `AI_ALLOW_MOCK=true` unconditionally |
| Payment runtime dependency | High | Configured / unverified | Stripe is now declared in runtime requirements; live sandbox Checkout/webhook lifecycle remains untested |
| Tenant AI spend ceiling | High | Open | Daily AI-message quota exists; monetary/token budget reservation and reconciliation are not yet implemented |
| Webhook delivery durability | High | Fixed in code / locally tested | Durable outbox worker performs delivery and records results; external endpoint delivery remains untested |
| Secrets in repository history | High | Open | Scan history before any public-release decision |

## Current local evidence

- Backend: `133 passed, 2 warnings` from the configured backend test root.
- Frontend E2E: `4 passed` covering Cognito entry points, PKCE/state binding,
  recovery navigation, protected API access and logout.
- Frontend production build: passed.
- Frontend ESLint: `0 errors, 0 warnings` under the strict `lint:check` gate.
  unused imports/variables and unused suppression directives, not suppressed
  security or hook errors.
- Cognito identity provisioning now requires an explicit positive
  `email_verified` signal from claims or the userinfo response.

The latest hosted CI run (12 October 2026, commit `cf4bd1f`) recorded
`135 passed, 19 skipped` backend tests, a passing API health smoke job, and
`4 passed` serial frontend E2E tests. The preceding manual Hostinger run
verified the Compose deployment and `/api/health/ready` on the VPS, but the
public domain still requires DNS cutover and an end-to-end HTTPS check.

Production database migration/backup evidence, live inbox testing, external
webhook delivery, billing-provider verification, provider usage/cost
reconciliation, and secret-history scanning remain unverified.

No production GO is allowed until Critical and High findings are fixed and
independently verified or explicitly accepted by the product owner.
