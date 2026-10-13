# Testing

## Required local gates

Backend:

~~~powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m compileall -q app server.py
python -m pytest -q
~~~

Frontend:

~~~powershell
cd frontend
npm ci
npm run lint:check
npm run format:check
npm run build
npm run test:sdk
npm run test:e2e
~~~

Documentation:

~~~powershell
cd ..
powershell -ExecutionPolicy Bypass -File scripts/validate_docs.ps1
~~~

A mock test proves behavior under fixtures. A browser test proves the local browser flow exercised by that test. Real inbox, external webhook, payment sandbox, provider, production database, and deployment tests must be reported separately. Skipped or historical checks are not current verification. Never log passwords, OTPs, bearer tokens, or provider secrets.

Use Node.js 24 with npm for frontend checks. Backend database tests require a reachable, migrated disposable PostgreSQL database configured through `DATABASE_URL` and `ALEMBIC_DATABASE_URL`; Redis must also be reachable. Review skipped tests explicitly. Never point test commands at a production database.

## Hosted checks and dated evidence

Application CI runs on pushes to `main` and pull requests targeting `main`. The backend test job starts isolated PostgreSQL/pgvector and Redis services, migrates the CI-only `oraone_test` database, then runs pytest. Frontend CI runs strict lint, formatting, production build, widget SDK tests, and serial browser tests. The quality workflow rejects uncommitted autofixes using repository-root pathspecs. Workflow configuration alone is not passing execution evidence.

The 14 October 2026 audit found successful hosted application/quality runs at `ca4204b`, but no runs for the audited UI checkpoint `ef6ba4d`. Historical local counts in `docs/design/UI_INTEGRATION.md` remain dated local evidence; they are not results of these workflow changes. New CI results must identify their tested SHA and run URL.

## Documentation-specific evidence

The repository validator checks relative links, GitHub-style anchors, code-fence pairing, source-to-embed parity, diagram count, diagram structure, and tracked secret-like paths. The ten Mermaid sources were additionally parsed on this branch with Mermaid 11.12.0 and JSDOM 26.1.0 in an isolated temporary environment; those packages are not application dependencies. No Mermaid renderer or CI workflow is added to the repository.
