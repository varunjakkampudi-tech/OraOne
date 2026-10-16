# Authentication and authorization

OraOne authenticates users itself. There is no external identity provider.

## Sign-in

Sign-in is passwordless:

1. `POST /api/auth/email-code/request` emails a six-digit code. An unknown address
   creates an account with an unusable random password, so the code is the only
   way in. The response is identical for known and unknown addresses.
2. `POST /api/auth/email-code/verify` checks the code. A code is single-use and
   expires after ten minutes. On success the API sets two httpOnly cookies and
   returns the same tokens for API clients.

Sessions use short-lived access tokens (15 minutes by default) and rotating
refresh tokens (30 days by default). `POST /api/auth/refresh` rotates the pair.
`POST /api/auth/logout` ends one session. `POST /api/auth/logout-all` ends every
session for the caller.

### Development sign-in

`POST /api/auth/dev-login` accepts a password. It exists only for local testing
with the seeded accounts. It returns `404` unless **both** `ENVIRONMENT=development`
and `ALLOW_DEV_PASSWORD_LOGIN=true`. It is refused in staging and production.

Seed the local accounts with `python scripts/seed_dev_users.py` (development only).

## Identity and tenancy

- The access token's `sub` claim is the user's `auth_subject`.
- `GET /api/auth/identity` provisions the user, a personal organization and a
  default project on first call. The call is idempotent.
- Every business request is scoped server-side by organization and project.
  The browser never chooses a tenant. The project is selected with the
  `X-Project-Id` header, which the server validates against the caller's
  organization.

## Roles

Platform roles (`super_admin`, `admin`, `manager`, `user`) are stored on the user
and gate the staff console. Organization roles (`owner`, `admin`, `member`,
`viewer`) are stored on the membership and gate workspace actions. Both are
enforced by the API. Frontend checks only affect what is shown.

## Rate limits

Sign-in and refresh endpoints are rate-limited per client IP and per verified
user. The limits are configurable through `RATE_LIMIT_*` variables.
