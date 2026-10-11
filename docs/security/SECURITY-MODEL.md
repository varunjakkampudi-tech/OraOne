# Security model

Browser input and frontend role state are untrusted. Cognito access tokens are accepted only after JWKS, issuer, expiry, client, and token-use validation. PostgreSQL is authoritative for users, roles, memberships, and audit records.

Remote model, payment, webhook, and storage providers are failure-prone external systems. Caddy is the intended public edge; internal services should not be directly reachable.

Controls include email-only Cognito UI, tenant-scoped repositories, webhook destination validation, delivery-time revalidation, redirect blocking, durable outbox state, production rejection of explicit mock inference, and no committed environment secrets.

Independent review remains required for prompt injection, uploads/crawling, secret history, deployment egress, real providers, and production recovery.
