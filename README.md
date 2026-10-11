# OraOne

OraOne is a multitenant AI chat platform for website agents, knowledge-grounded answers, lead capture, workflows, integrations, billing, and an embeddable widget.

This is the authoritative setup and operations guide. Local validation is not production approval; see `docs/CLEANUP-MANIFEST.md` and `docs/SECURITY-REVIEW.md`.

## Architecture

Browser/widget -> Caddy :443 (oraone.in) -> React static app and FastAPI :8000. FastAPI uses PostgreSQL + pgvector, Redis, and MinIO/S3-compatible storage. FastAPI uses AWS Cognito JWKS for production identity and OpenRouter for server-side AI inference.

Docker Compose on a Hostinger VPS is the intended deployment. Caddy is the only public application entry point; stateful and app service ports are private. AWS EC2 and GitHub Pages are not deployment targets.

## Stack and structure

- `frontend/`: React/CRACO application and production widget assets.
- `backend/`: FastAPI, SQLAlchemy, Alembic, providers, services, and tests.
- `docker-compose.dev.yml`: local PostgreSQL/pgvector, Redis, and MinIO.
- `docker-compose.prod.yml`: private service network and Caddy edge.
- `Caddyfile`: TLS termination and `/api/*` reverse proxy routing.
- `docs/`: architecture and evidence records; this README is authoritative.

## Prerequisites

Docker Engine 24+ with Compose v2, Python 3.11+, Node 20+ with Yarn classic, and PostgreSQL with pgvector when Docker is not used.

## Environment variables

Copy `backend/.env.example` to `backend/.env`; never commit it. Local development uses `AUTH_PROVIDER=self_hosted` and a random 32+ character `JWT_SECRET_KEY`. Production must use `AUTH_PROVIDER=cognito` with `COGNITO_USER_POOL_ID`, `COGNITO_REGION`, and `COGNITO_CLIENT_ID`.

Production also requires operator-managed `DB_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `S3_BUCKET`, `CADDY_DOMAIN`, and values listed in `backend/.env.example`. `OPENAI_API_KEY` is the server-side OpenRouter credential. Never put Cognito or OpenRouter secrets in the frontend.

## Local installation

Run `docker compose -f docker-compose.dev.yml up -d`, create a Python 3.11+ virtual environment in `backend`, install `backend/requirements.txt`, copy `backend/.env.example` to `backend/.env`, set a random JWT secret and local database URLs, run `alembic upgrade head`, and start `uvicorn server:app --reload --port 8000`. In `frontend`, run `yarn install --frozen-lockfile` and `yarn start`. The local frontend is `http://localhost:3000`; the API is `http://localhost:8000`.

## Docker production-like stack

Prepare a real `backend/.env` and operator environment. Run `docker compose -f docker-compose.prod.yml config` as a mandatory preflight, then `docker compose -f docker-compose.prod.yml up -d --build` and `docker compose -f docker-compose.prod.yml ps`. The preflight must fail when required secrets or Cognito values are missing. Do not use development defaults in production.

## Database, backups, and recovery

Run `alembic upgrade head` only after reviewing migration SQL and confirming the target database. Use `backend/scripts/backup_restore_drill.py` against a disposable environment. Keep encrypted backups outside the VPS and record retention, restore timing, and recovery evidence.

## Cognito

Configure a user pool, app client, email sign-in, and Google identity provider with callback/logout URLs for the deployed domain. The API verifier fetches rotating JWKS keys and validates RS256 signature, issuer, expiry, `token_use=access`, and `client_id`, then resolves the subject through the existing organization/RBAC model. Existing users must be mapped and tested before local auth is disabled. Live login, refresh, logout, expiry, and OAuth tests remain release gates.

## OpenRouter and RAG

The backend uses the OpenAI-compatible provider interface pointed at `https://openrouter.ai/api/v1`; credentials remain server-side. Configure model selection, embeddings, quotas, usage accounting, timeouts, and retry policy in the backend. Credentialed inference and cost-limit evidence are required before production approval.

## Testing and formatting

Run `python -m pytest -q` and `python -m compileall -q app server.py` in `backend`, then set `CI=true` and run `yarn build` in `frontend`. Database-dependent tests may require Compose services. Report skipped tests as skipped, never as passing integration evidence. Keep formatting-only changes separate from behavior changes.

## Hostinger deployment

Provision a supported VPS, Docker, a firewall allowing only SSH and 80/443, DNS for `oraone.in`, and operator-managed secrets. Clone the private repository, create `backend/.env`, run the Compose config preflight, apply migrations, and start the stack. Verify `/api/health/ready`, TLS, frontend routing, Cognito login, tenant isolation, a real AI request, logs, backup, and restart recovery. Hostinger access, DNS, OAuth, payment accounts, and production credentials are external blockers in this checkout.

## Manual release and rollback

Review the diff and run complete local validation; build tagged images and record Git SHA and image digests; back up and verify the database; apply migrations and start the new revision; run health, auth, tenant-isolation, billing/webhook, widget, and AI smoke tests. On failure, restore prior image tags and use the approved reversible migration procedure. Never reset or destructively rewrite production data.

## Production status

This repository is a release candidate, not a production GO. Open high-risk gates include live Cognito cutover, credentialed OpenRouter usage/cost control, independent SSRF/upload/webhook/prompt-injection review, billing verification, secret-history scanning, and Hostinger backup/rollback validation.
