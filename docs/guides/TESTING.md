# Testing

## Required local gates

Backend:

~~~powershell
cd backend
python -m compileall -q app server.py
python -m pytest -q
~~~

Frontend:

~~~powershell
cd frontend
npx eslint "src/**/*.{js,jsx}"
yarn build
npx playwright test
~~~

Documentation:

~~~powershell
cd ..
powershell -ExecutionPolicy Bypass -File scripts/validate_docs.ps1
~~~

A mock test proves behavior under fixtures. A browser test proves the local browser flow exercised by that test. Real inbox, external webhook, payment sandbox, provider, production database, and deployment tests must be reported separately. Skipped or historical checks are not current verification. Never log passwords, OTPs, bearer tokens, or provider secrets.

## Documentation-specific evidence

The repository validator checks relative links, GitHub-style anchors, code-fence pairing, source-to-embed parity, diagram count, diagram structure, and tracked secret-like paths. The ten Mermaid sources were additionally parsed on this branch with Mermaid 11.12.0 and JSDOM 26.1.0 in an isolated temporary environment; those packages are not application dependencies. No Mermaid renderer or CI workflow is added to the repository.
