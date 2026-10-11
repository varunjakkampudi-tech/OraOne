# Environment configuration

| File | Purpose | Commit? |
| --- | --- | --- |
| backend/.env.example | Backend variable template | Yes |
| backend/.env | Local backend secrets | No |
| frontend/.env.example | Browser-safe build variables | Yes |
| frontend/.env.production | Browser build settings | No |
| .env.production | Compose interpolation | No |

Local mode uses AUTH_PROVIDER=self_hosted, a local DATABASE_URL, Redis at redis://localhost:6379/0, and a random JWT_SECRET_KEY. If S3_BUCKET is unset, uploads use UPLOAD_DIR.

Production mode uses AUTH_PROVIDER=cognito, the configured Cognito pool/region/client/domain, explicit database and MinIO credentials, a real CADDY_DOMAIN, and server-side model/payment provider values. Browser variables must never contain provider secrets or access tokens.

Storage modes are local disk, MinIO/R2/B2 through S3_ENDPOINT_URL, or an approved existing AWS S3 bucket. This repository does not create buckets.
