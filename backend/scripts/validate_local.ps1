$ErrorActionPreference = "Stop"

Write-Host "[1/5] Python compilation"
& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m compileall -q "$PSScriptRoot\.."

Write-Host "[2/5] Docker Compose syntax"
docker compose -f "$PSScriptRoot\..\..\docker-compose.dev.yml" config --quiet

Write-Host "[3/5] Database migrations"
Push-Location "$PSScriptRoot\.."
try { & .\.venv\Scripts\python.exe -m alembic upgrade head } finally { Pop-Location }

Write-Host "[4/5] Backend tests"
Push-Location "$PSScriptRoot\.."
try { & .\.venv\Scripts\python.exe -m pytest -q } finally { Pop-Location }

Write-Host "[5/5] Frontend production build"
Push-Location "$PSScriptRoot\..\..\frontend"
try { $env:CI = "true"; $env:GENERATE_SOURCEMAP = "false"; yarn build } finally { Pop-Location }

Write-Host "Local validation passed."
