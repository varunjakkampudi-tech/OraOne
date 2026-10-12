# Deployment

This describes the production-like Compose artifact. It does not claim Hostinger, DNS, TLS, or Cognito live traffic is configured.

1. Provision an approved host and firewall with only SSH and 80/443 exposed.
2. Clone the intended repository and record the Git SHA.
3. Supply operator-managed .env.production and backend/.env; never commit them.
4. Run docker compose --env-file .env.production -f docker-compose.prod.yml config.
5. Review missing interpolation, public ports, and provider settings.
6. Back up the target database before migrations.
7. Verify database identity before applying migrations.
8. Start the stack and check health.
9. Run auth, tenant-isolation, widget, webhook, billing, and AI smoke tests.

Caddy terminates TLS and routes /api/* to FastAPI. Other services remain private.

## Manual GitHub deployment

Production deployment is intentionally manual. Run the **Manual Hostinger deployment** workflow from the GitHub Actions UI, select `main`, and type `DEPLOY`. The job rejects every other branch and verifies the exact fetched SHA plus `/api/health/ready` after Compose starts.

The protected `production` environment must contain `HOSTINGER_HOST`, `HOSTINGER_USER`, `HOSTINGER_SSH_KEY`, and `HOSTINGER_KNOWN_HOSTS`. The deployment host keeps `.env.production` and `backend/.env` outside Git; the workflow never accepts secrets as workflow inputs and never prints them.

Keep previous image tags and Git SHA. Roll back by redeploying the previous image while preserving a compatible schema. Reverse migrations only with a reviewed down migration and verified backup.

## Hostinger deployment

<!-- diagram: docs/diagrams/deployment.mmd -->
```mermaid
flowchart TB
  DNS[oraone.in DNS] --> HTTPS[Public HTTPS traffic]
  HTTPS --> Caddy[Caddy on Hostinger VPS]
  subgraph PrivateNetwork[Private Compose network]
    Caddy --> Frontend[Frontend container]
    Caddy --> Backend[Backend container]
    Backend --> Worker[Worker container]
    Backend --> DB[(PostgreSQL volume)]
    Backend --> Redis[(Redis volume)]
    Backend --> Minio[(MinIO volume)]
    Worker --> DB
    Worker --> Redis
  end
  Backend -. outbound token/API requests .-> Cognito[External Cognito service]
  Backend -. outbound model requests .-> OpenRouter[External OpenRouter service]
  Volumes[Persistent Docker volumes] -. persist .-> DB
  Volumes -. persist .-> Redis
  Volumes -. persist .-> Minio
```
