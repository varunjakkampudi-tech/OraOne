# Authentication and RBAC

Cognito mode uses the existing email-only user pool and authorization-code flow. The backend validates issuer, JWKS signature, expiry, token_use=access, and client binding, then maps the Cognito sub to the PostgreSQL user.

Self-hosted auth remains useful for local development. Google, phone, and SMS sign-in are not part of the current UI or identity contract.

PostgreSQL is authoritative for platform roles: super_admin, admin, manager, and user. Organization membership roles are tenant-scoped. Browser role fields and unvalidated claims cannot grant privileges. Privileged role changes are server-side and audit logged.

Protected request sequence: validate bearer token, resolve user by Cognito sub, reject disabled or missing users, resolve organization scope, apply endpoint permission, query scoped records, and audit privileged mutations.

See RBAC.md for bootstrap and migration procedures. Live Cognito and production database evidence are not present in this checkout.

## Cognito authentication sequence

<!-- diagram: docs/diagrams/cognito-auth-sequence.mmd -->
```mermaid
sequenceDiagram
  participant B as Browser
  participant C as Cognito Hosted Login
  participant F as React frontend
  participant A as FastAPI
  participant J as Cognito JWKS
  participant D as PostgreSQL
  B->>F: Start email authentication
  F->>F: Create state and PKCE transaction
  F->>C: Authorization request
  C-->>F: Authorization code callback
  F->>F: Validate state and bind transaction
  F->>C: Exchange code with PKCE verifier
  C-->>F: Tokens
  F->>A: Establish session with access token
  A->>J: Request JWKS on cache miss
  J-->>A: Return JWKS document
  A->>A: Verify issuer, signature, expiry, token_use, client
  A->>D: Resolve Cognito sub and membership
  D-->>A: User and RBAC scope
  A-->>F: HttpOnly session result
  F->>A: Refresh or logout
  A-->>F: Rotate or clear session cookies
```

## Tenant and platform authorization

<!-- diagram: docs/diagrams/tenant-rbac.mmd -->
```mermaid
flowchart TB
  Token[Validated Cognito subject] --> User[PostgreSQL user mapping]
  User --> Platform[Platform role]
  User --> Membership[Organization membership]
  Platform --> Super[Platform super_admin]
  Platform --> Admin[Platform admin]
  Platform --> Manager[Platform manager]
  Platform --> PlatformUser[Platform user]
  Membership --> Owner[Organization owner]
  Membership --> OrgAdmin[Organization admin]
  Membership --> Member[Organization member]
  Membership --> Viewer[Organization viewer]
  Platform --> Policy[Platform permission]
  Membership --> Scope[Tenant scope]
  Policy --> Query[Scoped repository query]
  Scope --> Query
  Query --> Audit[Audit privileged mutation]
```
