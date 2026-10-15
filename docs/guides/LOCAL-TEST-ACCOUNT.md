# Local QA login: test@oraone.in

This **development-only** fixture creates a real, nonprivileged PostgreSQL user
using the existing Argon2 password hasher. It does **not** hardcode credentials
in the application, bypass OTP, grant admin access, run at startup, or change
the production identity-provider policy.

It is intended only for a local, disposable PostgreSQL database on loopback.
Do **not** use it on shared preview environments, staging, production, or a
local tunnel to a production database.

## Prerequisites

Follow [Quickstart](QUICKSTART.md) first: run local Postgres/Redis, migrate
the database with Alembic, and use `AUTH_PROVIDER=self_hosted` in the local
backend. A valid unique `JWT_SECRET_KEY` is still required.

### PowerShell: create the account

Run from `backend/` after configuring your local `backend/.env`:

```powershell
$env:ENVIRONMENT = "development"
$env:AUTH_PROVIDER = "self_hosted"
$env:ORAONE_LOCAL_TEST_ACK = "I_UNDERSTAND_THIS_IS_LOCAL_ONLY"
$env:ORAONE_LOCAL_TEST_PASSWORD = "test@oraone.in"

# The script uses DATABASE_URL (or DB_HOST) from your environment or backend/.env.
# Its effective DB hostname must be exactly localhost, 127.0.0.1, or ::1.
python scripts/seed_local_test_account.py

Remove-Item Env:ORAONE_LOCAL_TEST_PASSWORD
Remove-Item Env:ORAONE_LOCAL_TEST_ACK
```

Use the frontend local `/login` page:

- Email: `test@oraone.in`
- Password: `test@oraone.in`
- Complete the standard OTP step; a correct password alone never grants a session.

For development **without a configured mail provider**, the existing local
backend cache contains the OTP. With Redis configured as described in the
Quickstart, a developer who owns the local machine can retrieve the last
test-account OTP from `backend/` in a separate local terminal:

```powershell
python -c "from app.services import auth_service; print(auth_service._cache().get(auth_service._login_otp_key('test@oraone.in')) or 'No local OTP')"
```

Never paste the OTP into an issue, PR, screenshot or log. Never configure this
account on a network-accessible service.

## Safety properties

- The script refuses any environment other than exactly `development`.
- The auth mode must explicitly be `self_hosted`.
- An acknowledgement environment variable is required.
- The configured database host must be loopback.
- The seeded account's platform role is `user`, never `super_admin`.
- An existing user with different credentials, role, status or verification
  state is never overwritten.
- No account is seeded unless the operator runs the script explicitly.
- The script does not bypass or weaken the existing OTP authentication flow.
- The current application intentionally refuses self-hosted auth in
  production/staging. Do not change that as a side effect of adding this fixture.

Delete the fixture from the isolated database when no longer needed using an
approved local cleanup procedure. Never use bulk SQL deletion on a shared
database.

## Verification

```powershell
cd backend
python -m pytest tests/test_local_test_account_seed.py -q
```

These tests check the fail-closed guard. They are not a live authentication
test. Run the repository's `verify_otp_flow_local.py` and other real Product 1
verification scripts separately for end-to-end evidence.

## Verifying the fixture end to end

With the API running locally, the same opt-in variables drive a real lifecycle
check: wrong password rejected, password step returns no tokens, wrong OTP
rejected, OTP single use, `/api/auth/me` role `user`, platform admin API denied,
refresh rotation with stale-token reuse rejected, and refresh rejected after
logout:

```bash
cd backend
ENVIRONMENT=development AUTH_PROVIDER=self_hosted \
ORAONE_LOCAL_TEST_ACK=I_UNDERSTAND_THIS_IS_LOCAL_ONLY \
ORAONE_LOCAL_TEST_PASSWORD='<local password>' \
python scripts/verify_local_test_account_flow.py --base-url http://127.0.0.1:8000
```

**Local OTP behaviour:** when no `SMTP_HOST`/`EMAIL_FROM`/SES sender is
configured, the email service logs that the message was *not sent*. It never
logs the code. The 6-digit code lives only in the local Redis cache under
`login_otp:<email>` for 10 minutes and is deleted on first successful use.
