$ErrorActionPreference = "Stop"

Write-Host "[1/5] Python compilation"
& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m compileall -q "$PSScriptRoot\..\app" "$PSScriptRoot\..\scripts" "$PSScriptRoot\..\server.py" "$PSScriptRoot\..\worker.py"
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed ($LASTEXITCODE)." }

Write-Host "[2/5] Docker Compose syntax"
docker compose -f "$PSScriptRoot\..\..\docker-compose.dev.yml" config --quiet
if ($LASTEXITCODE -ne 0) { throw "Docker Compose validation failed ($LASTEXITCODE)." }

Write-Host "[3/5] Database migrations"
Push-Location "$PSScriptRoot\.."
try {
  & .\.venv\Scripts\python.exe -c "import os, sys; from dotenv import load_dotenv; from urllib.parse import urlsplit; load_dotenv('.env'); valid = os.getenv('ENVIRONMENT', 'development') == 'development' and urlsplit(os.getenv('DATABASE_URL', '')).hostname in {'localhost', '127.0.0.1'}; sys.exit(0 if valid else 'Local validation refuses a non-development or non-loopback database')"
  if ($LASTEXITCODE -ne 0) { throw "Development database guard failed ($LASTEXITCODE)." }
  & .\.venv\Scripts\python.exe -m alembic upgrade head
  if ($LASTEXITCODE -ne 0) { throw "Database migration failed ($LASTEXITCODE)." }
} finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Database migration failed ($LASTEXITCODE)." }

Write-Host "[4/5] Backend tests"
Push-Location "$PSScriptRoot\.."
try { & .\.venv\Scripts\python.exe -m pytest -q } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Backend tests failed ($LASTEXITCODE)." }

Write-Host "[5/5] Frontend production build"
Push-Location "$PSScriptRoot\..\..\frontend"
try { npm run build } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed ($LASTEXITCODE)." }

Write-Host "Local validation passed."
