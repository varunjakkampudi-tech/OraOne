# Local quickstart

Prerequisites: Docker Engine with Compose v2, Python 3.11+, Node.js 20+, and Yarn 1.22.22.

## Infrastructure

~~~powershell
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml ps
~~~

This starts PostgreSQL/pgvector, Redis, and MinIO. Local ports are PostgreSQL 5433, Redis 6379, MinIO API 9000, and MinIO console 9001.

## Backend

~~~powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m uvicorn server:app --reload --port 8000
~~~

Use AUTH_PROVIDER=self_hosted and a random development JWT_SECRET_KEY. Never copy production Cognito or provider secrets.

## Frontend

~~~powershell
cd frontend
yarn install --frozen-lockfile
$env:PORT = "3001"
yarn start
~~~

Use http://localhost:3001 if port 3000 is occupied. The frontend API URL should point to the local backend.

Stopping Compose preserves named volumes. A volume reset is destructive; remove only the named OraOne volumes after confirming local data is disposable.
