# Deployment

The production stack is defined in [`docker-compose.prod.yml`](../../docker-compose.prod.yml).
It runs five services behind one public entry point:

| Service             | Image                            | Purpose                                                                   |
| ------------------- | -------------------------------- | ------------------------------------------------------------------------- |
| `proxy`             | `caddy:2`                        | TLS termination, compression, security headers. The only published ports. |
| `frontend`          | built from `frontend.Dockerfile` | Server-rendered web application (Node).                                   |
| `backend`           | built from `backend/Dockerfile`  | FastAPI API under Gunicorn. Runs migrations on start.                     |
| `workers`           | same image as `backend`          | Background jobs (`worker.py`).                                            |
| `postgres`, `redis` | pgvector and Redis               | Data and shared cache. Not published.                                     |

Caddy routes `/api/*` to the backend and everything else to the web application.

## Required secrets

Set these in the environment of the deployment, never in the repository:

- `DB_PASSWORD`
- `JWT_SECRET_KEY` (at least 32 characters)
- `OPENROUTER_API_KEY`
- `SMTP_HOST` and the SMTP credentials, so sign-in codes are delivered
- `CADDY_DOMAIN`
- `ORAONE_VERSION` (optional, used as the image tag)

## Procedure

1. Provide the secrets above, for example in `.env.production`.
2. Build and start:

   ```bash
   docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
   ```

3. Check the API and the web application:

   ```bash
   curl -fsS https://<your-domain>/api/health
   ```

4. Confirm that the development shortcuts are off: `ENVIRONMENT=production` and
   `ALLOW_DEV_PASSWORD_LOGIN` unset. Seeding development accounts must not run.

## Storage

Uploaded documents are stored on the `oraone_uploads` volume, mounted at
`/var/lib/oraone/uploads`. Back up this volume together with the database.
See [backup and restore](BACKUP-RESTORE.md).

## Release gate

Complete the [release checklist](RELEASE-CHECKLIST.md) before routing live traffic.
