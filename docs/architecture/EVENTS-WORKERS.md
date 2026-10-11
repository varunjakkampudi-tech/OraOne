# Events and workers

Business events needing asynchronous delivery are persisted into an outbox. The worker claims pending work, delivers webhook endpoints with bounded retries, records per-endpoint results, and applies terminal handling for exhausted attempts.

Webhook destinations are validated at create/update time and revalidated before delivery. Redirects are disabled. Deployment egress controls remain defense in depth.

The worker is separate from the API container in the production-like Compose file. Do not hold a database transaction open while waiting on remote HTTP. Required evidence includes connection failures, HTTP 5xx, timeout, partial fan-out, restart, and duplicate-delivery behavior.

## Webhook outbox sequence

<!-- diagram: docs/diagrams/webhook-outbox.mmd -->
```mermaid
sequenceDiagram
  participant B as Business operation
  participant T as Database transaction
  participant O as Outbox row
  participant W as Worker
  participant E as Endpoint
  participant D as Delivery state
  B->>T: Commit business change
  T->>O: Persist event atomically
  W->>O: Claim pending event
  W->>E: Deliver with stable idempotency key
  E-->>W: Success, HTTP failure, timeout, or connection error
  W->>D: Persist per-endpoint result and attempts
  D-->>W: Retry while bounded
  D-->>W: Dead-letter or terminal failure after exhaustion
```
