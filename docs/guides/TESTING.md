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
