# System overview

Caddy is the edge entry point in the production-like Compose file. It routes /api/* to FastAPI and all other paths to the frontend. The backend owns authentication, authorization, tenant resolution, persistence, provider calls, uploads, and public API limits.

PostgreSQL with pgvector is the system of record. Redis provides cache, rate limits, distributed idempotency, and coordination where configured. MinIO or another S3-compatible service stores documents and branding assets. Local disk is the development fallback.

The development Compose file publishes local stateful ports. The production-like file keeps backend, worker, PostgreSQL, Redis, and MinIO private and publishes only Caddy.

Provider failures must remain visible and must not become a production claim through a local fallback. Outbox work is persisted before delivery; external delivery and recovery drills remain release gates.

## Deployment topology

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

## Product 1 system architecture

<!-- diagram: docs/diagrams/product1-system-architecture.mmd -->
```mermaid
flowchart LR
  Visitor[Website visitor] --> Widget[Embeddable widget]
  Operator[Business operator] --> Browser[React dashboard]
  Widget --> Edge[Caddy edge]
  Browser --> Edge
  Edge --> Frontend[React frontend]
  Edge --> API[FastAPI backend]
  API --> Cognito[Cognito email identity]
  API --> Router[OpenAI-compatible provider]
  API --> DB[(PostgreSQL and pgvector)]
  API --> Redis[(Redis)]
  API --> Minio[(MinIO or S3-compatible storage)]
  API -. enqueues durable work .-> Outbox[(Transactional outbox)]
  Worker[Independent worker process] --> Outbox
  Worker --> DB
  Worker --> Redis
  Worker --> Minio
  API --> Integrations[Configured integrations and webhooks]
  External[External provider services] --> Integrations
```
