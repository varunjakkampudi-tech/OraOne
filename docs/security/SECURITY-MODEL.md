# Security model

Browser input and client-side role state are untrusted. The API enforces every
rule that matters.

## Controls

- **Authentication:** passwordless email codes. Codes are single-use, expire after
  ten minutes and are compared in constant time. Access tokens are short-lived
  HS256 JWTs signed with `JWT_SECRET_KEY`. Refresh tokens rotate on every use.
- **Sessions:** httpOnly, SameSite=Lax cookies. The refresh cookie is scoped to
  `/api/auth`. Logout revokes the refresh token.
- **Tenant isolation:** every repository query is scoped by organization. The
  active project is validated against the caller's organization.
- **Authorization:** platform roles and organization roles are checked on the
  server for every privileged endpoint.
- **Development shortcuts:** the password sign-in endpoint is disabled outside
  `ENVIRONMENT=development`, and the seed script refuses to run elsewhere.
- **Rate limits:** sign-in and refresh endpoints are throttled per IP and per user.
- **Uploads:** stored on a volume owned by the application user. Paths are checked
  against traversal.
- **Secrets:** supplied through the environment, never committed. The secrets
  inventory returns only set or not-set flags and a masked tail. Redaction of common key
  formats exists in `security_service.redact_output`, but this review found it reached from
  the operations endpoints only, not from the chat reply path.
- **Controls and accepted risks:** the controls with their source files, and the open items,
  are listed in [SECURITY](../operations/SECURITY.md).

## Reporting

Report vulnerabilities privately using the process in [SECURITY.md](../../SECURITY.md).
