# OraOne authorization model

OraOne has two independent role systems:

- **Platform role** (`users.role`): `super_admin`, `admin`, `manager`, or `user`.
  This is global account administration and is resolved from PostgreSQL by the
  authenticated Cognito `sub`.
- **Organization membership role** (`organization_members.role`): `owner`,
  `admin`, `member`, or `viewer`. This controls access inside one workspace.

An organization admin is not a platform admin. Browser payloads, frontend role
checks, and arbitrary JWT claims cannot assign or elevate platform roles.

## Safe bootstrap

The initial platform administrator is promoted only through the operator CLI;
it does not create credentials or hardcode a password:

```powershell
$env:PLATFORM_BOOTSTRAP_APPROVED_SUB = '<verified-cognito-sub>'
$env:PLATFORM_BOOTSTRAP_CONFIRM = 'PROMOTE_TO_SUPER_ADMIN'
python scripts/bootstrap_platform_admin.py --cognito-sub '<verified-cognito-sub>'
```

The target must already exist in `users`, which means it must first complete a
normal Cognito login and identity hydration. The command is intentionally
fail-closed when either approval variable is missing or mismatched.

## Role changes

`PATCH /api/rbac/platform/users/{user_id}/role` is protected by a
PostgreSQL-backed platform-role dependency. Platform admins may assign only
`manager` and `user`; super administrators may additionally assign `admin`.
`super_admin` promotion is reserved for the bootstrap/platform-owner process.
Every successful change is emitted to the persisted audit-log pipeline.

The existing platform control-center routes use the same PostgreSQL role gate;
the legacy `PLATFORM_ADMIN_EMAILS` setting is not an authorization bypass.

Migration `0045_platform_roles` safely maps every legacy `users.role` value to
platform `user`. Legacy values are not sufficient evidence of global platform
authority. Organization membership rows are not rewritten, so existing
workspace owner/admin privileges and tenant isolation are preserved.

## Deployment evidence and production gate

Local verification on 11 October 2026:

- Alembic reports `0045_platform_roles (head) (mergepoint)` after applying the
  migration to the local development database.
- Backend suite: `133 passed, 2 warnings`.
- RBAC, authorization, and tenant-isolation subset: `57 passed`.
- Frontend Cognito E2E suite: `4 passed`.
- Frontend production build: passed.
- ESLint 9: 0 errors; 184 warnings remain, consisting of 179 existing
  `no-unused-vars` warnings or stale-disable warnings. No active hook or
  security-rule warnings were reported.

Production is **not verified** from this checkout. No independently verified
production backup, production database identity, or live Cognito authorization
test is available here, so `alembic upgrade head` must not be run against a
guessed or local connection.

Before deployment:

1. From the production host, record the database host/database identity and
   current Alembic revision using a read-only connection.
2. Create an encrypted `pg_dump` backup and complete
   `scripts/backup_restore_drill.py` against a disposable restore database.
3. Preserve the backup and restore evidence outside the application host.
4. Set `ALEMBIC_DATABASE_URL` explicitly to the verified deployment database,
   review the generated migration SQL, and run `alembic upgrade head`.
5. Verify the `user_role` enum, `users.role` non-null/default, Cognito-sub
   lookup, and privileged role-change audit records with non-sensitive smoke
   tests. Do not log tokens, passwords, or OTPs.

Rollback:

- If the application revision must be reverted while the schema is retained,
  deploy the previous image and keep the migration applied; old code does not
  safely understand all new role values, so freeze role changes until the
  compatible revision is restored.
- If the schema itself must be reverted, stop writes, preserve post-migration
  audit evidence, and restore the verified pre-migration database backup.
  The Alembic downgrade intentionally collapses `super_admin` to `admin` and
  `manager` to `member`, so it is not the preferred production rollback for a
  database that has used the new roles.
