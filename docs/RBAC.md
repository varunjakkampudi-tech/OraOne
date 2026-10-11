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

Migration `0045_platform_roles` safely maps legacy global roles: `owner` and
`admin` become platform `admin`, while `member` becomes platform `user`.
Organization membership rows are not rewritten, preserving workspace
privileges and tenant isolation.
