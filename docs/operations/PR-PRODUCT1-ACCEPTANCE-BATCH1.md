# PR: Product 1 acceptance batch 1: QA fixture review, RBAC and upload hardening, ops evidence

Base: `main` @ `ad87035` plus PR #2 (`ebf08f5`). Branch: `qa/product1-acceptance-batch1`.
Merge PR #2 first, or merge this PR, which contains it. Do not force-push `main`.

## Problem and root cause

| # | Severity | Problem | Root cause |
| --- | --- | --- | --- |
| 1 | HIGH | An invited `viewer` could create/update agents, KBs, documents, folders, websites, leads and channel configs | 27 write handlers resolved org membership but never checked the RBAC permission matrix |
| 2 | HIGH | In production, every client behind Caddy would share a single rate-limit bucket (10 logins/min and 120 API calls/min for all users combined) | `TRUSTED_PROXY_IPS` was never set, so `request.client.host` was always Caddy |
| 3 | HIGH | Knowledge upload accepted any file (e.g. `.exe`, spoofed PDF) | No extension allow-list or content-signature check at the boundary |
| 4 | MEDIUM | Brand-asset upload trusted the client content-type; SVG was served from the app origin without a sandbox (stored XSS vector) | Missing signature validation and response CSP |
| 5 | MEDIUM | `alembic`, `bootstrap_db.py` and `backup_restore_drill.py` silently replaced explicit env vars with `backend/.env` values | `load_dotenv(..., override=True)`, unlike the API, worker and pytest |
| 6 | MEDIUM | `cryptography 46.0.7`: 4 published advisories (PYSEC-2026-3552/3553/3554, GHSA-537c-gmf6-5ccf) | Upper pin `<47` |
| 7 | MEDIUM | Gunicorn worker recycling dropped in-flight requests (23 of ~21k in a 5-min soak) | No proxy retry policy |
| 8 | MEDIUM | Settings showed a working "2FA" toggle that did nothing server-side | UI-only state |
| 9 | LOW | Sidebar labels and badges below WCAG AA contrast; toggle buttons without an accessible name | Design tokens / missing `aria-label` |

## Changes

- `backend/app/api/**`: `dependencies=[Depends(require_permission(...))]` on the 27 write routes (`agents.write`, `kb.write`, `kb.delete`, `leads.write`, `integrations.manage`, `settings.manage`).
- `backend/app/services/document_processing.py`: `validate_upload()`; `knowledge/routes.py` returns 415 for it.
- `backend/app/api/branding/routes.py`: image signature checks; assets served with `CSP: default-src 'none'; sandbox` and `nosniff`.
- `backend/alembic/env.py`, `scripts/bootstrap_db.py`, `scripts/backup_restore_drill.py`: `override=False`.
- `backend/requirements.txt`: `cryptography>=50.0.2,<51.0`.
- `docker-compose.prod.yml`: `TRUSTED_PROXY_IPS` (overridable default: private Docker ranges).
- `Caddyfile`: `lb_try_duration 5s`, `lb_try_interval 250ms` for `/api/*`.
- Removed the unused `ProjectScopedRepository` and the unused `oidc-client-ts` / `react-oidc-context` packages.
- Frontend: honest 2FA and notifications states, sidebar contrast, toggle `aria-label`, Tailwind content glob.
- New tests: `tests/test_rbac_write_guards.py` (30), `tests/test_upload_validation.py` (15).
- New loopback-only verifiers: `verify_local_test_account_flow.py`, `verify_security_local.py`, `verify_storage_recovery_local.py`, `load_test_local.py`, `frontend/e2e/real-route-audit.mjs`.
- Docs: acceptance ledger, route acceptance, cleanup manifest addendum, env and QA-account guides.

## Tests executed

See `docs/operations/PRODUCT1-ACCEPTANCE-LEDGER.md`. In summary: backend 289 passed; Ruff clean; ESLint and Prettier clean; build OK; SDK 1/1; Playwright 27/27; real-API verifiers 38 + 93 + 14 + 15 checks with 0 failures; API smoke 169 routes with no 5xx; backup/restore drill passed; pip-audit and npm audit clean; gitleaks only placeholders.

## Known limitations

Cognito production login, production deploy/TLS/monitoring/rollback, SMTP delivery, third-party OAuth, the Bedrock embedding provider and live multi-provider fallback are **not** verified. Page-level colour contrast still fails axe on many routes. `alembic check` reports model/migration drift that needs a reviewed migration. `/api/v1` is plan-gated (402) on the free plan, pending an owner decision.

## Security implications

Write access is now strictly permission-matrix based. Integrations relying on viewers writing (none known) would receive 403. Trusting private proxy ranges is safe only while the backend port stays unpublished.

## Rollback

Revert this PR's merge commit. No migrations are added. For a faster partial rollback of the proxy change, set `TRUSTED_PROXY_IPS=` (empty) in the deployment environment, and remove the `lb_*` lines from the `Caddyfile`.
