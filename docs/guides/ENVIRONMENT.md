# Environment configuration

This page is based on the files and loaders present in the repository. Paths are relative to the repository root.

## Tracked versus secret files

| Path | Tracked intentionally? | Contents | Handling |
| --- | --- | --- | --- |
| frontend/.env.production | Yes, deliberately | Public frontend build configuration for the same-origin deployment | Contains no backend secrets; values are bundled into the browser and must remain non-sensitive |
| backend/.env | No | Local backend secrets and local overrides | Ignored; generate from the explicit Quick Start values |
| frontend/.env | No | Local frontend overrides | Ignored; generate from the explicit Quick Start values |
| .env.production | No | Compose interpolation and deployment secrets | Ignored; never commit |
| frontend/build/ and test output | No | Generated artifacts | Ignored; never commit |

Verified repository paths include frontend/.env.production, backend/app/core/config.py, backend/app/database/session.py, and both Compose files. No `.env.example` templates are tracked; the Quick Start creates local files directly so templates cannot be mistaken for complete production configuration.

## Local backend values

The development Compose file defines PostgreSQL user oraone_admin, password oraone_dev_password, database oraone, and host mapping 5433:5432. The backend therefore needs a local DATABASE_URL using localhost:5433, plus an ALEMBIC_DATABASE_URL using the same credentials. Redis is redis://localhost:6379/0.

The backend config accepts DATABASE_URL first. The DB_* fallback path expects DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME. The template also contains a legacy DB_NAME_PG key; prefer the explicit URLs shown in the quickstart so Alembic and the application use the same database.

Local MinIO uses S3_ENDPOINT_URL=http://localhost:9000, bucket oraone-dev, access key oraone_minio, and secret oraone_minio_password. These are disposable Compose development credentials only. If S3_BUCKET is unset, the storage service falls back to UPLOAD_DIR.

## Public frontend configuration

Only REACT_APP_* values are bundled into the client. The tracked frontend/.env.production file contains:

```text
REACT_APP_ENV
REACT_APP_API_URL
REACT_APP_AUTH_PROVIDER
REACT_APP_COGNITO_DOMAIN
REACT_APP_COGNITO_CLIENT_ID
REACT_APP_COGNITO_REDIRECT_URI
```

The actual values are deployment configuration, not secrets. Do not put database passwords, provider API keys, Cognito tokens, client secrets, or access tokens in any frontend environment file.

## Authentication modes

| Mode | Required values | Use |
| --- | --- | --- |
| Local self-hosted | AUTH_PROVIDER=self_hosted and JWT_SECRET_KEY with at least 32 characters | Default first-clone development path |
| Local Cognito | AUTH_PROVIDER=cognito plus user pool, region, client, and domain | Authorized Cognito testing only |
| Production-like Compose | Cognito values, explicit database/storage secrets, domain, and provider settings | Preflight and controlled deployment preparation |
| Actual production | Verified host, DNS, backups, monitoring, live identity and provider evidence | Not established by this repository |

Generate local JWT_SECRET_KEY with Python secrets. Never reuse it in production or commit it.

## Storage and provider values

Required backend secrets stay server-side: database credentials, MinIO/S3 credentials, OpenRouter/API credentials, payment credentials, SMTP/SES credentials, and any SMS credentials. Optional integrations should remain blank until separately authorized and tested. This repository does not create AWS S3 buckets.

Cognito production uses the configured email-only user pool. Google, phone, and SMS authentication are not part of the current UI contract.
