# Troubleshooting

For production problems (webhooks, calls, messages, quotas, widgets, integrations), see the
[runbook](../operations/RUNBOOK.md). Settings are listed in [CONFIGURATION](../operations/CONFIGURATION.md).

## Sign-in code never arrives

Sign-in codes are sent only when `SMTP_HOST` is configured. Without it, no code is sent, and
the sign-in request returns HTTP 503 instead of a success message. The same 503 is returned when a
send fails. Check `backend/.env`, then restart the API. In local development,
use the developer sign-in panel (or `POST /api/auth/dev-login`) with the seeded accounts.

## Assistant replies fail with a provider error

Set `OPENROUTER_API_KEY` in `backend/.env` and restart the API. Also check that no
other `OPENROUTER_API_KEY` is set in your operating-system environment, because the
environment value takes precedence over the file.

## Dashboard shows "could not load"

The API is probably not running. Check <http://127.0.0.1:8000/api/health>. The web
dev server forwards `/api` to `API_PROXY_TARGET`, which defaults to port 8000.

## Uploads fail

`UPLOAD_DIR` must be writable and owned by the user that runs the API. It must not be
a symbolic link.

## Database errors after an update

Run `alembic upgrade head` from the `backend` folder. Confirm the database is at the
latest revision with `alembic current`.

## Port already in use

Change `POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`, the API port or the web port, and update
the matching `.env` values.
