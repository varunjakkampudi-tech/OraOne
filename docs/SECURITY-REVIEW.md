# OraOne principal security review

This is a repository review, not a penetration test or certification.

| Finding | Severity | State | Evidence / next action |
|---|---:|---|---|
| Development database password fallback in production Compose | Critical | Fixed | Required `DB_PASSWORD` substitution |
| Development MinIO credential fallback in production Compose | Critical | Fixed | Required MinIO substitutions |
| Direct publication of stateful/app service ports | High | Fixed | Only Caddy publishes host ports |
| Legacy EC2/Pages deployment paths | High | Fixed | Workflows and EC2 stack removed |
| HS256-only authentication | High | Partial | Cognito JWKS path added; live cutover remains |
| Documented local admin default | High | Fixed in template | Empty values now required; no DB mutation performed |
| Unsafe AI fallback in production | High | Open | Disable/isolate and verify provider failure behavior |
| Billing, SSRF/crawler, uploads, webhooks, prompt injection | High | Open | Independent review and targeted tests required |
| Secrets in repository history | High | Open | Scan history before destination migration |

No production GO is allowed until Critical and High findings are fixed and
independently verified or explicitly accepted by the product owner.
