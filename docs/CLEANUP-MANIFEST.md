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

1. Configure/test email-only Cognito login, verification, logout, refresh,
   expiry, and migration of existing users.
2. Run credentialed OpenRouter inference and verify quotas, accounting,
   timeout/retry behavior, and provider failure behavior.
3. Run migrations, backups, restore, and restart recovery against disposable
   PostgreSQL/Redis/MinIO infrastructure.
4. Independently review crawling, uploads, webhooks, billing, tenant
   isolation, and prompt-injection controls.
5. Provision Hostinger, DNS, TLS, secrets, monitoring, and rollback storage.

## Product 1 acceptance batch 1 (PR #2 follow-up)

Method: a fresh static import graph from `src/index.js` (static, re-export,
literal dynamic `import()`, CSS `url()`). It reached 176/176 frontend files
with zero unresolved imports, so no frontend source deletions were justified.
Backend: a module importer scan over `app/`, `scripts/`, `tests/`, `server.py`
and `worker.py`. No `importlib`/`__import__` dynamic loading exists in `app/`.

| Item | Action | Evidence |
| --- | --- | --- |
| `backend/app/database/repositories/project_scoped.py` | Removed | Zero importers, not exported from `repositories/__init__.py`, no tests/scripts/docs references, no dynamic loading |
| `oidc-client-ts`, `react-oidc-context` (frontend deps) | Removed | Not imported by `src/`, `packages/`, `e2e/` or config. Cognito uses `src/lib/cognito.js`. Build, lint, SDK and browser suites pass after removal |
| `tailwind.config.js` content glob `./public/index.html` | Corrected to `./index.html` | Vite serves the root `index.html`; the old path did not exist |
| Settings → Two-factor toggle | Replaced with a "Planned" status | No backend MFA exists; the toggle only flipped local state and showed "2FA enabled" |
| Settings → Notifications copy | Clarified | Preferences persist only in `localStorage`; copy now says so |
| `frontend/yarn.lock` (untracked, environment-generated) | Removed | The repository uses npm with `package-lock.json` |
| `public/favicon-16.png` | Retained | Unreferenced brand asset variant; kept to preserve branding |
| `app/services/security_service.py`, `user_service.py` | Retained | Imported via `from app.services import …` (scanner false positive) |
| `vulture` findings (`cls` in Pydantic validators) | Retained | Framework-required signatures |
