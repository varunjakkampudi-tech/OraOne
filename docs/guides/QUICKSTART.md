# Quickstart

This guide runs OraOne Product 1 on your machine: the web app, the API and the
local database.

## Prerequisites

- Bun 1.4 or later (`bun.lock` pins every web dependency)
- Node.js 22 or later (the production build runs on Node)
- Python 3.11 or later (3.12 is used in CI)
- Docker, for PostgreSQL and Redis

## 1. Start the database and cache

```bash
docker compose -f docker-compose.dev.yml up -d postgres redis
```

If another local stack already uses ports 5433 or 6379, set
`POSTGRES_HOST_PORT` and `REDIS_HOST_PORT` first, and update `backend/.env` to match.

## 2. Configure and start the API

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env`:

- set `JWT_SECRET_KEY` (generate it with the command shown in the file)
- set `ALLOW_DEV_PASSWORD_LOGIN=true` for local testing
- set `OPENROUTER_API_KEY` to enable assistant replies

Then install, migrate, seed the local accounts and start the server:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python scripts/seed_dev_users.py
.venv/Scripts/python -m uvicorn server:app --reload --port 8000
```

## 3. Start the web application

In a second terminal, from the repository root:

```bash
bun install
bun run dev
```

Open <http://localhost:5180>. The dev server forwards `/api` to port 8000.

## Local accounts

| Account           | Password          | Role                         |
| ----------------- | ----------------- | ---------------------------- |
| `varun@oraone.in` | `varun@oraone.in` | user                         |
| `admin@oraone.in` | `oraone.in`       | platform owner (super admin) |

These accounts exist only in development. Password sign-in is enabled for them
through `POST /api/auth/dev-login`, which is refused in every other environment.

Email sign-in codes are sent only when `SMTP_HOST` is configured.
