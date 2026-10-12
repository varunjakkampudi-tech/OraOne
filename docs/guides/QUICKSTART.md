# Local quickstart

This guide is for a first clone of OraOne. It uses the existing development Compose stack and local self-hosted authentication. It does not configure Cognito production, Hostinger, or any paid provider.

## Prerequisites

- Git
- Python 3.11 or newer
- Node.js 20 or newer
- Yarn 1.22.22
- Docker Engine with Docker Compose v2

Verify:

```powershell
git --version
python --version
node --version
yarn --version
docker compose version
```

On Linux/macOS, use python3 where your system does not provide python.

## 1. Start local infrastructure

From the repository root:

```powershell
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml ps
```

The existing Compose file starts:

| Service | Host address | Development credentials |
| --- | --- | --- |
| PostgreSQL + pgvector | localhost:5433 | user oraone_admin, password oraone_dev_password, database oraone |
| Redis | localhost:6379 | no password |
| MinIO S3 API | http://localhost:9000 | user oraone_minio, password oraone_minio_password |
| MinIO console | http://localhost:9001 | same MinIO credentials |

The PostgreSQL port is 5433 on the host because the container listens on 5432. These are disposable local development credentials, not production secrets.

## 2. Configure and start the backend

The backend loads backend/.env automatically. Create it locally and keep it ignored.

### Windows PowerShell

From the repository root:

```powershell
$jwt = python -c "import secrets; print(secrets.token_urlsafe(48))"
@"
ENVIRONMENT=development
AUTH_PROVIDER=self_hosted
JWT_SECRET_KEY=$jwt
DB_HOST=localhost
DB_PORT=5433
DB_USER=oraone_admin
DB_PASSWORD=oraone_dev_password
DB_NAME=oraone
DATABASE_URL=postgresql+asyncpg://oraone_admin:oraone_dev_password@localhost:5433/oraone
ALEMBIC_DATABASE_URL=postgresql+psycopg2://oraone_admin:oraone_dev_password@localhost:5433/oraone
REDIS_URL=redis://localhost:6379/0
ENTITLEMENTS_CACHE_BACKEND=redis
S3_BUCKET=oraone-dev
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=oraone_minio
S3_SECRET_ACCESS_KEY=oraone_minio_password
UPLOAD_DIR=$([IO.Path]::Combine((Get-Location).Path, "backend", "uploads"))
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
FRONTEND_URL=http://localhost:3000
RUN_BACKGROUND_WORKERS=false
EMBEDDING_PROVIDER=hash
AI_ALLOW_MOCK=false
"@ | Set-Content backend/.env
```

Create the virtual environment and install dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
alembic upgrade head
python -m compileall -q app server.py
python -m uvicorn server:app --reload --port 8000
```

If PowerShell blocks activation, invoke the interpreter directly as backend\.venv\Scripts\python.exe. Do not weaken system execution policy globally.

### Linux/macOS

From the repository root:

```bash
JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" python3 - <<'PY'
from pathlib import Path
import os
p = Path("backend/.env")
p.write_text("""ENVIRONMENT=development
AUTH_PROVIDER=self_hosted
JWT_SECRET_KEY={jwt}
DB_HOST=localhost
DB_PORT=5433
DB_USER=oraone_admin
DB_PASSWORD=oraone_dev_password
DB_NAME=oraone
DATABASE_URL=postgresql+asyncpg://oraone_admin:oraone_dev_password@localhost:5433/oraone
ALEMBIC_DATABASE_URL=postgresql+psycopg2://oraone_admin:oraone_dev_password@localhost:5433/oraone
REDIS_URL=redis://localhost:6379/0
ENTITLEMENTS_CACHE_BACKEND=redis
S3_BUCKET=oraone-dev
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=oraone_minio
S3_SECRET_ACCESS_KEY=oraone_minio_password
UPLOAD_DIR=/tmp/oraone-uploads
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
FRONTEND_URL=http://localhost:3000
RUN_BACKGROUND_WORKERS=false
EMBEDDING_PROVIDER=hash
AI_ALLOW_MOCK=false
""".format(jwt=os.environ["JWT_SECRET_KEY"]))
PY
cd backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
alembic upgrade head
python -m compileall -q app server.py
python -m uvicorn server:app --reload --port 8000
```

The shell variable and generated backend file contain a local secret. Do not paste either into an issue or commit them.

## 3. Configure and start the frontend

Open a second terminal at the repository root:

```powershell
@"
REACT_APP_ENV=development
REACT_APP_API_URL=http://localhost:8000
REACT_APP_AUTH_PROVIDER=self_hosted
REACT_APP_COGNITO_DOMAIN=
REACT_APP_COGNITO_CLIENT_ID=
REACT_APP_COGNITO_REDIRECT_URI=http://localhost:3000/auth/callback
"@ | Set-Content frontend/.env
cd frontend
npm ci
$env:PORT = "3000"
npm start
```

Linux/macOS:

```bash
cat > frontend/.env <<'EOF'
REACT_APP_ENV=development
REACT_APP_API_URL=http://localhost:8000
REACT_APP_AUTH_PROVIDER=self_hosted
REACT_APP_COGNITO_DOMAIN=
REACT_APP_COGNITO_CLIENT_ID=
REACT_APP_COGNITO_REDIRECT_URI=http://localhost:3000/auth/callback
EOF
cd frontend
npm ci
PORT=3000 npm start
```

The frontend uses http://localhost:8000 from the generated frontend/.env and runs at http://localhost:3000. If port 3000 is occupied, use port 3001 and set CORS_ORIGINS and FRONTEND_URL in backend/.env to include http://localhost:3001.

## 4. Verify the local stack

```powershell
docker compose -f docker-compose.dev.yml ps
Invoke-WebRequest http://localhost:8000/api/health/ready
Invoke-WebRequest http://localhost:9000/minio/health/live
```

Then run the repository gates from their documented working directories:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_docs.ps1
cd backend
python -m pytest -q
cd ..\frontend
npx eslint "src/**/*.{js,jsx}"
npm run build
npx playwright test
```

The browser E2E suite starts the frontend itself. A live Cognito inbox test, external webhook, payment provider, or deployed host is not part of this local quickstart.

## 5. Stop and reset

Safe stop; named volumes are preserved:

```powershell
docker compose -f docker-compose.dev.yml down
```

The same command works on Linux/macOS.

Warning: 'docker compose ... down -v' deletes the local PostgreSQL, Redis, and MinIO volumes and all data in them. Use it only when the local data is disposable and you have confirmed the exact Compose project and volumes. Never use it against a production or customer database.

## Configuration modes

| Mode | Identity | Data/services | Evidence |
| --- | --- | --- | --- |
| Local self-hosted | AUTH_PROVIDER=self_hosted | Development Compose and local fallback/provider settings | This guide |
| Local Cognito | AUTH_PROVIDER=cognito | Same local services plus authorized Cognito values | Requires an authorized pool and email test |
| Production-like Compose | AUTH_PROVIDER=cognito | Private Compose network and operator-supplied secrets | Config preflight only |
| Actual production | Cognito and deployed infrastructure | Verified host, DNS, backups, monitoring, and rollback | Not established by this checkout |


## Startup flow

<!-- diagram: docs/diagrams/local-development-startup.mmd -->
```mermaid
flowchart TD
  Prereq[Git, Python 3.11+, Node 20+, Yarn, Docker Compose] --> Docker[Start dev Compose]
  Docker --> DB[(PostgreSQL pgvector on 5433)]
  Docker --> Redis[(Redis on 6379)]
  Docker --> Minio[(MinIO API 9000 and console 9001)]
  Prereq --> BackendDeps[Create backend virtualenv and install requirements]
  BackendDeps --> Env[Copy backend .env and set local values]
  Env --> Alembic[Run alembic upgrade head]
  Alembic --> API[Start FastAPI on 8000]
  Prereq --> FrontendDeps[Install frontend dependencies]
  FrontendDeps --> UI[Start React on 3000 or 3001]
  API --> Validate[Run tests, lint, build, and docs validation]
  UI --> Validate
```
