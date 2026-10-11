# Security policy

## Scope

This policy covers the OraOne source repository and local application code. Local test results do not prove that a hosted deployment is secure.

## Private vulnerability reporting

Use the repository-scoped [GitHub private vulnerability report form](https://github.com/varunjakkampudi-tech/OraOne/security/advisories/new) when it is available. This URL is the canonical private-report endpoint for the verified repository, owner, and current GitHub remote.

The repository metadata was checked on 2026-10-11 and confirmed:

- Repository: varunjakkampudi-tech/OraOne
- Visibility: public
- Owner: varunjakkampudi-tech
- Issues: enabled
- Security-advisory feature availability: not exposed by the metadata response

Therefore, the URL is actionable but private-reporting enablement is not independently verified from this checkout. The repository owner must open the link while signed in and enable/confirm private vulnerability reporting before treating it as an active channel. Until then, do not publish vulnerability details in a public issue; contact the verified repository owner through an authorized private GitHub channel.

Do not use the public Issues tab for sensitive reports. Do not include passwords, OTPs, bearer tokens, provider keys, database credentials, private customer data, backup locations, or administrator bootstrap secrets.

A useful report includes the affected revision, impact, prerequisites, a minimal sanitized reproduction, suspected root cause, and a proposed mitigation. Redact secrets from logs and screenshots.

## Supported versions

This repository does not currently publish a supported-version matrix. Report against the current default branch or the exact release revision under review.

## Security boundaries

- Cognito access tokens are accepted only after issuer, JWKS signature, expiry, client binding, and token-use validation.
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
