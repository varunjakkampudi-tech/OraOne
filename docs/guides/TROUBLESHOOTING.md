# Troubleshooting

## Database or migration

Confirm Docker health, inspect DATABASE_URL, and run Alembic from backend. Never point local commands at a production URL without an approved backup and target identity check.

## Authentication

Confirm the Cognito domain, client ID, callback, and API URL agree. The backend must use the same pool region and issuer. Failed identity hydration must not be treated as an authenticated session.

## Uploads

Check whether S3_BUCKET is intentionally unset for local fallback or whether MinIO endpoint and credentials are valid. Confirm UPLOAD_DIR is writable and database records are tenant-scoped.

## Workers and webhooks

Check Redis and worker health, inspect outbox state, and verify destination validation. External delivery failure is not proof of success; use durable retry and dead-letter evidence.
