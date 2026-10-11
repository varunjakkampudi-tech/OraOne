# Contributing

Read the relevant architecture and security documentation first. Keep tenant boundaries and PostgreSQL authority intact. Do not add secrets, credentials, tokens, generated output, or local databases.

Run backend compile/tests, frontend lint/build/E2E checks relevant to the change, and scripts/validate_docs.ps1 for Markdown or metadata changes.

Reviewers expect a threat model for auth, RBAC, webhooks, storage, provider calls, and migrations. Production claims require external evidence. Do not change either license without owner/legal approval.
