# Security policy

## Scope

This policy covers the OraOne source repository and local application code. Local test results do not prove that a hosted deployment is secure.

## Private vulnerability reporting

Use the repository-scoped [GitHub private vulnerability report form](https://github.com/varunjakkampudi-tech/oraone-prod/security/advisories/new). This is the private-report endpoint for the verified repository and current GitHub remote.

The repository was checked on 14 October 2026:

- Repository: varunjakkampudi-tech/oraone-prod
- Visibility: public
- Owner: varunjakkampudi-tech
- Issues: enabled
- Private vulnerability reporting: enabled, confirmed by the authenticated GitHub API

Use the private form while signed in to GitHub. No synthetic vulnerability report
was submitted merely to test the channel. Enablement is verified; triage and
response remain operational responsibilities.

Do not use the public Issues tab for sensitive reports. Do not include passwords, OTPs, bearer tokens, provider keys, database credentials, private customer data, backup locations, or administrator bootstrap secrets.

A useful report includes the affected revision, impact, prerequisites, a minimal sanitized reproduction, suspected root cause, and a proposed mitigation. Redact secrets from logs and screenshots.

## Supported versions

This repository does not currently publish a supported-version matrix. Report against the current default branch or the exact release revision under review.

## Security boundaries

- OraOne-issued access tokens are accepted only after signature, expiry, issuer, and token-use validation (backend/app/core/security.py).
- PostgreSQL is authoritative for users, platform roles, organization memberships, tenant scope, and audit records.
- Frontend role state and request payloads are untrusted.
- Webhook destinations are validated at configuration and delivery time; redirects are disabled.
- Backend provider credentials remain server-side.
- Caddy is the intended public edge; internal services should not be directly published.
- Local MinIO, PostgreSQL, Redis, and JWT credentials are development-only unless separately secured.

## Data handling

Use synthetic data in tests and issue reports. Treat conversations, documents, leads, uploaded files, access tokens, identity claims, and provider responses as sensitive. Do not commit environment files or generated databases. Verify backups, retention, encryption, access control, and restore procedures separately before production use.

## Response expectations

Reports are triaged, reproduced, fixed, tested, and documented according to impact. Coordinated disclosure timing is agreed with the reporter. No certification, SLA, or production security guarantee is claimed by this policy.
