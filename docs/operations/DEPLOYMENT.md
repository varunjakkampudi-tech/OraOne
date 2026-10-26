# Production deployment

This guide deploys the production stack defined in
[`docker-compose.prod.yml`](../../docker-compose.prod.yml) on one server. Every
variable named here is listed in [CONFIGURATION](CONFIGURATION.md). Values are
never written in this document.

## What runs

| Container         | Image source                                              | Role                                                                                                                                                             |
| ----------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OraOne-proxy`    | `caddy:2.11.7-alpine` with [`Caddyfile`](../../Caddyfile) | The only public entry point. Ports 80 and 443. Obtains the TLS certificate for `CADDY_DOMAIN`. Sends `/api/*` to the backend and everything else to the web app. |
| `OraOne-frontend` | [`frontend.Dockerfile`](../../frontend.Dockerfile)        | Web application (Node server on port 8080). Not published.                                                                                                       |
| `OraOne-backend`  | [`backend/Dockerfile`](../../backend/Dockerfile)          | API under Gunicorn (port 8000). Not published. Runs `alembic upgrade head`, then starts.                                                                         |
| `OraOne-workers`  | same image as backend                                     | Runs `worker.py`: the workflow scheduler and the webhook outbox. No HTTP port.                                                                                   |
| `OraOne-migrate`  | same image as backend                                     | One-shot. Runs `alembic upgrade head`. The API and workers start only after it exits with code 0.                                                                |
| `OraOne-postgres` | `pgvector/pgvector:pg16`                                  | Database. Not published.                                                                                                                                         |
| `OraOne-redis`    | `redis:7.4.11-alpine`                                     | Shared cache, rate limits, sign-in codes. Not published.                                                                                                         |

The production host (Hostinger VPS, DNS, firewall, the `/opt/oraone` layout and rollback status)
is described in [HOSTINGER-DEPLOYMENT](../HOSTINGER-DEPLOYMENT.md). The image tags above are
those in `docker-compose.prod.yml`.

Only Caddy publishes ports. The `scripts/` folder is excluded from the backend image
(see `backend/.dockerignore`), so run operator scripts from a checkout of the repository,
not inside a container.

## Before you start

1. **A domain name.** Create a DNS record for the public host name. Point it at the
   server. Ports 80 and 443 must be reachable from the internet, because Caddy uses
   them to obtain the certificate.
2. **Accounts you will need.** These are needed for the features you enable:
   - PostgreSQL is in the stack. No external account is needed.
   - An OpenRouter account, for AI replies (required; the startup check refuses to start without it).
   - An SMTP mail account, for sign-in codes (required in practice).
   - A Twilio account, for SMS, WhatsApp, AI Voice and outbound calls (optional).
   - A Meta developer app, for WhatsApp Cloud API and Instagram (optional).
   - Google Cloud OAuth clients, for Google Drive, Google Calendar and Google Sheets (optional).
   - Slack, Notion and HubSpot OAuth apps (optional).
   - An ElevenLabs account, for more natural spoken replies on AI Voice (optional).
   - A Stripe account (optional; billing stays off unless enabled).
3. **A server** with Docker and Docker Compose, and a clone of this repository at the
   release you are deploying. Check the release tag or commit before you build.

## Step 1: write the two environment files on the server

Compose reads two files:

- **`.env.production`** (passed with `--env-file`) supplies the values Compose uses to
  build the stack: `DB_PASSWORD`, `OPENROUTER_API_KEY`, `TRUSTED_PROXY_IPS`,
  `CADDY_DOMAIN`, and optionally `ORAONE_VERSION`.
- **`backend/.env`** is read by the migrate, backend and workers containers through
  `env_file`. It holds the application settings: `JWT_SECRET_KEY`, `FRONTEND_URL`,
  `APP_URL`, `CORS_ORIGINS`, `SMTP_*`, `OPENROUTER_*`, `UPLOAD_DIR` and the optional
  provider settings. Start from [`backend/.env.example`](../../backend/.env.example),
  then change the values for production.

Set these in production (see [CONFIGURATION](CONFIGURATION.md) sections 1 to 5):

- `ENVIRONMENT=production`. Compose also forces this value, so the stack always runs in production mode.
- `JWT_SECRET_KEY`: at least 32 characters, random. Generate it with
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `CORS_ORIGINS`: the exact public origin of the web app, for example `https://<your-domain>`.
- `FRONTEND_URL` and `APP_URL`: the same public origin. Without them, links point to `localhost`.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_SSL`.
- `UPLOAD_DIR`: set this to a directory the container user can write, for example the path the volume uses (`/var/lib/oraone/uploads`). Compose already sets it.
- `ALLOW_DEV_PASSWORD_LOGIN`: leave unset or `false`.
- `ORAONE_FREE_ACCESS_ONLY`: leave at the default unless billing is intended.
- `INTEGRATIONS_ENCRYPTION_KEY`: set it explicitly (a Fernet key) if you use integrations, so that rotating `JWT_SECRET_KEY` does not make stored integration tokens unreadable.
- Provider settings only if you use that feature: the Twilio, Meta and Google groups.
  For Twilio, `PUBLIC_API_BASE_URL` must be `https://<your-domain>` and is required by the startup check.

Keep both files out of Git. Do not paste them into chat, tickets or logs.

## Step 2: check the interpolation without printing secrets

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
```

Use `--quiet`. Without it, `docker compose config` prints the resolved configuration,
including passwords and keys, so do not run it without `--quiet` in a shared terminal
or log.

If a required variable is missing, Compose stops with a message that names it.

## Step 3: build and start

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Startup order, enforced by Compose:

1. `postgres` and `redis` start. Both must report healthy.
2. `migrate` runs `alembic upgrade head`. The stack waits until it exits with code 0. If it fails, nothing else starts. Read its logs with `docker compose ... logs migrate`.
3. `backend` and `workers` start. The backend's own start command also runs `alembic upgrade head`, which does nothing when the schema is current.
4. `frontend` starts.
5. `proxy` (Caddy) starts once `backend` and `frontend` exist.

If the API refuses to start, the log names the missing settings by name and not their values, for example
`Refusing to start: incomplete configuration for a production-like environment. Missing or invalid settings (values not shown): ...`.
Fix the named settings and run the same command again. The startup checks are described in section "Startup checks" below.

## Step 4: verify

Replace `<your-domain>` with the public host name.

```bash
curl -fsS https://<your-domain>/api/health          # liveness: {"status":"ok",...}
curl -fsS https://<your-domain>/api/health/ready    # readiness: 200 when database and cache are reachable
```

- `/api/health` only reports that the process is up.
- `/api/health/ready` returns 503 with a body that lists each check when the database is unreachable, Redis is missing or unreachable, or another required dependency is down. The backend container's health check uses this endpoint.

Then check the other containers:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=100 backend workers
```

Confirm, in the logs, that the backend does not report `Redis unavailable` or `not initialised`.

Finally, confirm that development shortcuts are off:

- `ENVIRONMENT` is `production` in the running container.
- `ALLOW_DEV_PASSWORD_LOGIN` is unset or `false`.
- No development accounts were seeded. The seed script refuses to run outside development, so this should hold.

## Step 5: confirm the proxy address for rate limits

The API trusts `X-Forwarded-For` only when the request comes from an address listed in
`TRUSTED_PROXY_IPS`. Find the proxy container's address on the Compose network:

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' OraOne-proxy
```

Put that address (or a CIDR range that contains it) in `TRUSTED_PROXY_IPS` in
`.env.production`. The address can change when the proxy container is recreated. After
a recreation, repeat this check. A symptom of a wrong value is that rate limits affect
all users at once. See [RUNBOOK](RUNBOOK.md).

## Step 6: connect the provider webhooks

Provider webhooks need a public HTTPS URL that reaches the proxy. The application
builds the signed URLs from `PUBLIC_API_BASE_URL` (Twilio), so that value must match
the public origin exactly, with `https://` and no trailing path.

| Provider                                   | Console URL to configure (replace `<public-origin>`)                              | Server settings                                                                         |
| ------------------------------------------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Twilio messaging (SMS, WhatsApp)           | `<public-origin>/api/channels/twilio/inbound`                                     | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `PUBLIC_API_BASE_URL`                        |
| Twilio voice (inbound calls)               | `<public-origin>/api/voice/inbound`; speech turns use `/api/voice/gather`         | same, plus `TWILIO_PHONE_NUMBER` for outbound calls                                     |
| Twilio call status                         | `<public-origin>/api/voice/status` (set by the application when it places a call) | same                                                                                    |
| Meta WhatsApp Cloud API                    | `<public-origin>/api/channels/meta/inbound`                                       | `META_WHATSAPP_APP_SECRET`, `META_WHATSAPP_VERIFY_TOKEN`, `META_WHATSAPP_ACCESS_TOKEN`  |
| Meta Instagram                             | `<public-origin>/api/channels/meta_instagram/inbound`                             | `META_WHATSAPP_APP_SECRET`, `META_WHATSAPP_VERIFY_TOKEN`, `META_INSTAGRAM_ACCESS_TOKEN` |
| Inbound email (your mail provider's relay) | `<public-origin>/api/channels/email/inbound` with header `X-Email-Inbound-Secret` | `EMAIL_INBOUND_SECRET`                                                                  |

OAuth providers (Google Drive, Google Calendar, Google Sheets, Slack, Notion, HubSpot) need
a registered redirect URI that matches the server setting exactly:

| Provider                                               | Redirect URI to register                           | Server setting                                             |
| ------------------------------------------------------ | -------------------------------------------------- | ---------------------------------------------------------- |
| Google Drive                                           | `<public-origin>/api/integrations/google/callback` | `GOOGLE_REDIRECT_URI`                                      |
| Google Calendar, Google Sheets, Slack, Notion, HubSpot | `<public-origin>/api/integrations/oauth/callback`  | `<PREFIX>_REDIRECT_URI` (for example `SLACK_REDIRECT_URI`) |

The default redirect values point to `localhost`. Set each one you use. See
[CONFIGURATION](CONFIGURATION.md), sections 9 and 13.

Notes:

- Meta's console handshake (GET) returns the challenge only when the verify token matches `META_WHATSAPP_VERIFY_TOKEN`.
- The Twilio signature covers the full URL, including the query string. Configure Twilio with the exact URLs the application generates.
- Provider consoles have their own requirements, for example for app review and HTTPS certificates. Those are outside this repository. Check the provider's current documentation.
- Telegram is served at `<public-origin>/api/channels/telegram/<bot-token>/inbound`. The bot token is part of the URL path. The repository's `Caddyfile` does not enable access logging. Keep any proxy logs that you add private.

## Startup checks

`backend/app/core/startup_checks.py` runs when the API starts, and refuses to start
when `ENVIRONMENT` is `production`, `prod` or `staging` and any of these is missing:

- `JWT_SECRET_KEY`, at least 32 characters.
- If any `TWILIO_*` setting is set: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `PUBLIC_API_BASE_URL` starting with `https://`.
- If `META_WHATSAPP_ACCESS_TOKEN` or `META_INSTAGRAM_ACCESS_TOKEN` is set: `META_WHATSAPP_APP_SECRET`.
- `OPENROUTER_API_KEY`.

Separately, `CORS_ORIGINS` is required in these environments and is checked when the
app is built. The check does not run in development, so local runs need no provider secrets.

Not checked at startup (set them yourself, see CONFIGURATION section 16): database
URL, Redis, SMTP, `FRONTEND_URL`, `APP_URL`, `UPLOAD_DIR`, `GOOGLE_REDIRECT_URI`,
`TRUSTED_PROXY_IPS` (Compose requires it, the application does not).

## Storage and backups

Uploaded documents are stored on the `oraone_uploads` volume, mounted at
`/var/lib/oraone/uploads` in both the backend and workers containers. Back up this
volume together with the database. See [backup and restore](BACKUP-RESTORE.md).

**Check ownership before accepting uploads.** The application runs as user `oraone`
(UID 1000). The storage code refuses an upload directory that is not owned by the
process user on Linux. `backend/Dockerfile` does not create `/var/lib/oraone/uploads`,
so a newly created named volume may be owned by root. Confirm it after the first start:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend ls -ld /var/lib/oraone/uploads
```

The owner should be UID 1000 (`oraone`). If it is not, fix the ownership of the volume
on the host (or in a one-off container run as root) before users upload documents. This
was not tested against a running stack in this review.

The Caddy certificates are stored on `oraone_caddy_data`. Losing that volume makes
Caddy request new certificates, which can hit Let's Encrypt limits if repeated.

## Updating

1. Check out the new release on the server and confirm the commit.
2. Run the same `up -d --build` command. Compose rebuilds the images, runs `migrate`, then restarts the services in order.
3. Repeat the checks in Step 4.

Set `ORAONE_VERSION` to a new tag if you want the image tags to change with the release.
Read the [release checklist](RELEASE-CHECKLIST.md) before routing live traffic.
A rollback procedure is not written in this repository. Plan it before the release.

## Release gate

Complete the [release checklist](RELEASE-CHECKLIST.md) before routing live traffic.
The checks in this document confirm that the stack starts. They do not prove that
provider webhooks, email delivery or backups work. Test each one before launch.
