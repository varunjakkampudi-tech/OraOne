# OraOne — Product 1 (AI Chat Platform) completion & production readiness

## Original problem statement (summary)
Complete the existing OraOne repo (github.com/varunjakkampudi-tech/OraOne, baseline ad87035, QA fixture PR #2) and make Product 1 genuinely production-ready. Do not rebuild. Review PR #2, then CI, then cleanup with a manifest, local QA account test@oraone.in (Argon2, normal user, no prod seeding), reconcile 283 route inventory, verify real backend functionality, security/reliability regressions, perf/ops readiness, and publish a traceable acceptance ledger (PASS/FAIL/BLOCKED/NOT TESTED/N/A). Never claim production readiness prematurely. Use few credits.

## User choices
- Clone main + PR #2 into /app; install Postgres+pgvector, Redis, S3 locally; real inference with the user's OpenRouter key (in backend/.env, git-ignored); first batch = PR #2 review + CI + cleanup manifest + ledger + real smoke tests; user pushes via Save to GitHub.

## Architecture
React/Vite frontend (npm), FastAPI backend (Postgres/pgvector, Redis, S3/MinIO), widget SDK, self-hosted (dev) and Cognito (prod) auth, Caddy + Docker Compose production.

## Done (batch 1, Oct 2026)
- PR #2 seeder reviewed and verified (14-check real OTP/session lifecycle)
- Fixed: viewer RBAC write escalation (27 routes), production proxy rate-limit collapse (TRUSTED_PROXY_IPS), upload validation, brand-asset SVG XSS, dotenv override in alembic/backup scripts, cryptography CVEs, Caddy retry for worker recycling, fake 2FA toggle, sidebar contrast
- Cleanup: removed an unused repository mixin and 2 unused npm deps
- Evidence docs: docs/operations/PRODUCT1-ACCEPTANCE-LEDGER.md, ROUTE-ACCEPTANCE.md, PR-PRODUCT1-ACCEPTANCE-BATCH1.md, CLEANUP-MANIFEST addendum

## Backlog
- P0 (external): Cognito live test, production deploy/TLS/monitoring/rollback, prod backups, SMTP delivery
- P1: page-level WCAG contrast fixes, alembic model/migration drift migration, /api/v1 plan decision, Bedrock embeddings
- P2: live multi-provider fallback, OAuth integrations, adversarial prompt-injection suite
