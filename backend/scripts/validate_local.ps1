$ErrorActionPreference = "Stop"

Write-Host "[1/5] Python compilation"
& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m compileall -q "$PSScriptRoot\.."
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed ($LASTEXITCODE)." }

Write-Host "[2/5] Docker Compose syntax"
docker compose -f "$PSScriptRoot\..\..\docker-compose.dev.yml" config --quiet
if ($LASTEXITCODE -ne 0) { throw "Docker Compose validation failed ($LASTEXITCODE)." }

Write-Host "[3/5] Database migrations"
Push-Location "$PSScriptRoot\.."
try { & .\.venv\Scripts\python.exe -m alembic upgrade head } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Database migration failed ($LASTEXITCODE)." }

Write-Host "[4/5] Backend tests"
Push-Location "$PSScriptRoot\.."
try { & .\.venv\Scripts\python.exe -m pytest -q } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Backend tests failed ($LASTEXITCODE)." }

Write-Host "[5/5] Frontend production build"
Push-Location "$PSScriptRoot\..\..\frontend"
try { $env:CI = "true"; $env:GENERATE_SOURCEMAP = "false"; yarn build } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed ($LASTEXITCODE)." }

Write-Host "Local validation passed."
