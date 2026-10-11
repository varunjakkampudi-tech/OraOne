# OraOne cleanup and migration manifest

Baseline: 2026-10-11. This evidence log does not claim that external services
or production deployment are complete.

| Area | Status | Evidence / remaining gate |
|---|---|---|
| GitHub Actions | Complete | CI, Pages, and EC2 workflows removed |
| EC2 infrastructure | Complete | Obsolete CloudFormation stack removed |
| Setup duplication | Complete | `LOCAL_SETUP.md` removed; root README is authoritative |
| Demo seed/test harness | Complete | Untracked demo KB seed and fake widget host removed |
| Production secrets | Complete | Compose requires operator-provided values |
| Public service ports | Complete | Only Caddy publishes 80/443 |
| Cognito | Partial | JWKS verifier added; user-pool/OAuth cutover and live token test remain |
| OpenRouter | Partial | Existing provider retained; credentialed inference and cost evidence remain |
| Database/cache/storage | Partial | PostgreSQL/pgvector, Redis, and MinIO retained; VPS drills remain |
| Frontend redesign | Deferred | Await approved design folder |

## Retained deliberately

The production widget, customer-facing marketing preview, migrations,
backup/restore tooling, security tests, PostgreSQL, pgvector, Redis, MinIO,
Cognito-compatible identity columns, and OpenRouter-compatible inference code
remain because they are product or operational dependencies.

## Remaining release gates

1. Configure/test Cognito login, Google OAuth, logout, refresh, expiry, and
   migration of existing users.
2. Run credentialed OpenRouter inference and verify quotas, accounting,
   timeout/retry behavior, and provider failure behavior.
3. Run migrations, backups, restore, and restart recovery against disposable
   PostgreSQL/Redis/MinIO infrastructure.
4. Independently review crawling, uploads, webhooks, billing, tenant
   isolation, and prompt-injection controls.
5. Provision Hostinger, DNS, TLS, secrets, monitoring, and rollback storage.
