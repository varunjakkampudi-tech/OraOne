# Release checklist

- [ ] Diff reviewed; no secrets, generated output, or unrelated changes.
- [ ] Documentation and relative-link validation pass.
- [ ] Backend compile and full tests pass.
- [ ] Frontend lint, production build, and browser E2E pass.
- [ ] Alembic target identity, backup, SQL review, and rollback plan verified.
- [ ] Cognito email registration, verification, recovery, logout, refresh, and protected API live-tested.
- [ ] PostgreSQL RBAC and tenant isolation tested with authorized identities.
- [ ] External webhook success, failure, restart, and idempotency tested.
- [ ] Provider, quota, billing, and payment sandbox behavior verified.
- [ ] MinIO persistence and restore tested.
- [ ] Secret-history, dependency license/SBOM, and repository governance checks complete.
- [ ] Deployment health, TLS, monitoring, and rollback tested.

Local tests cannot check external boxes. Record blocked gates explicitly.
