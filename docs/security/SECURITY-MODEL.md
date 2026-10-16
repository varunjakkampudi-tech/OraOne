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
- **Secrets:** supplied through the environment, never committed. The secret
  scanner in the assistant output filter redacts common key formats.

## Reporting

Report vulnerabilities privately using the process in [SECURITY.md](../../SECURITY.md).
