# Configuration reference

This page lists the environment variables the repository reads: what each one does,
whether it is required, what happens when it is missing, and whether the admin
configuration console can change it. It was built by searching the source
(`backend/app`, `backend/server.py`, `backend/worker.py`, `backend/gunicorn.conf.py`,
`backend/alembic`, `backend/scripts`, `src/`, `vite.config.ts`, `playwright.config.ts`,
`e2e/`, the Dockerfiles and the Compose files).

The main list is grouped the way `backend/app/core/config_registry.py` groups it. That
module is the registry the console and the startup loader use. The last sections cover
names the code reads that the registry does not list. Values are never shown here.
Use placeholders such as `<random-48-chars>`, and keep real values in the server's
secret store or environment file.

This is the single source of truth for environment variables. [docs/CONFIGURATION.md](../CONFIGURATION.md)
and [guides/ENVIRONMENT.md](../guides/ENVIRONMENT.md) only point here.

Checked against commit `e6f8237` on branch `feat/product1-launch` (clean working tree when written).
All 93 keys in `backend/app/core/config_registry.py` appear in this page, and no name here is
missing from the code. Section 13 lists names the code reads without a registry entry.

## How to read the tables

- **Required** means the process refuses to start, or the feature refuses to work,
  without the value. "Startup check" means `backend/app/core/startup_checks.py`
  enforces it when `ENVIRONMENT` is `production`, `prod` or `staging`.
- **Console** shows whether the admin configuration console can store a value for this
  key (see [ADMIN-CONFIG](../guides/ADMIN-CONFIG.md)). "No" means the value comes only
  from the server's environment or `backend/.env`.
- **Missing behaviour** uses four words:
  - _Refuse to start_: the process exits during import or startup.
  - _Fail closed_: the feature rejects requests or sends nothing. No unsafe fallback.
  - _Degrade_: the feature runs with a weaker fallback.
  - _Off_: the feature is disabled.
- `ENVIRONMENT` is the switch that matters most. Only `production`, `prod` and `staging`
  are production-like. Any other value, including a typo, is treated as development.
  Keep it set to `production` on every server that serves users.

## 1. Core

| Variable                            | Required                                                            | Default                                            | Console      | Missing behaviour and notes                                                                                                                                                                                                                                                                                                 |
| ----------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ENVIRONMENT`                       | Yes in production                                                   | `development`                                      | No           | Production-like values turn on the startup checks, Secure cookies, required CORS origins, required widget domains, JSON logs and fail-closed cache rules. Other values behave as development.                                                                                                                               |
| `LOG_LEVEL`                         | No                                                                  | `INFO`                                             | Yes          | Log level. Production-like environments write JSON logs.                                                                                                                                                                                                                                                                    |
| `ORAONE_VERSION`                    | No                                                                  | `1.0.0` in code; `v1.0.0` as Compose image default | Yes          | Version label shown in health and operations output.                                                                                                                                                                                                                                                                        |
| `FRONTEND_URL`                      | Set in production (not checked)                                     | `http://localhost:3000`                            | Yes          | Public web address. Used in email links, OAuth return redirects and the widget's default CDN origin.                                                                                                                                                                                                                        |
| `APP_URL`                           | Set in production (not checked)                                     | `http://localhost:3000`                            | Yes          | Address the app returns to after billing and team invitation flows.                                                                                                                                                                                                                                                         |
| `BACKEND_PUBLIC_URL`                | No                                                                  | none                                               | Yes          | Public API address for widget and brand asset URLs. Checked first of the three backend URL settings.                                                                                                                                                                                                                        |
| `PUBLIC_BACKEND_URL`                | No                                                                  | none                                               | Yes          | Fallback public API address, used when `BACKEND_PUBLIC_URL` is unset.                                                                                                                                                                                                                                                       |
| `BACKEND_URL`                       | No                                                                  | `http://localhost:8000` for brand assets           | Yes          | Last-resort fallback public API address.                                                                                                                                                                                                                                                                                    |
| `CORS_ORIGINS`                      | Yes in production (startup refuses)                                 | localhost origins in development                   | Yes          | Comma-separated exact origins allowed to call the API. Wildcards, paths, queries, credentials and invalid ports refuse to start. Checked when the app builds its middleware.                                                                                                                                                |
| `TRUSTED_PROXY_IPS`                 | Yes in Compose; optional in code                                    | empty                                              | Yes          | Proxy addresses or CIDR ranges whose `X-Forwarded-For` header is trusted for rate limiting. Empty means every request is rate-limited by the proxy's address. Invalid entries are skipped with a warning.                                                                                                                   |
| `UPLOAD_DIR`                        | Set in production                                                   | `/tmp/oraone-uploads`                              | Yes          | Where uploaded documents are stored. The directory must not be a symbolic link, must be owned by the process user on POSIX, and is created with mode `0700`.                                                                                                                                                                |
| `RUN_BACKGROUND_WORKERS`            | No                                                                  | `false`                                            | No           | When `true`, the API process also starts the workflow scheduler and webhook outbox. Compose sets `true` only on the `workers` service. The `worker.py` process always starts both.                                                                                                                                          |
| `METRICS_BACKEND`                   | No                                                                  | `inprocess`                                        | Yes          | `prometheus` (or `prom`) or `otel` (or `opentelemetry`). If unavailable, falls back to in-process.                                                                                                                                                                                                                          |
| `ENTITLEMENTS_CACHE_BACKEND`        | No                                                                  | `inprocess`                                        | Yes          | `redis` (or `distributed`) uses Redis for the plan cache. Needs `REDIS_URL`. In production, a missing or unreachable Redis raises an error on first use.                                                                                                                                                                    |
| `REDIS_URL`                         | Yes in production (registry requires it; startup does not check it) | none                                               | Yes (secret) | Shared store for rate limits, OAuth state, refresh tokens, idempotency keys, sign-in codes and the voice audio cache. In production, a missing or unreachable Redis makes these fail closed, and `/api/health/ready` reports the cache as not configured. In development an in-process store is used, for one process only. |
| `OTEL_SERVICE_NAME`                 | No                                                                  | `oraone-api`                                       | Yes          | Service name on traces.                                                                                                                                                                                                                                                                                                     |
| `OTEL_EXPORTER_OTLP_ENDPOINT`       | No                                                                  | unset                                              | Yes          | Setting it turns tracing on. Unset means tracing is off.                                                                                                                                                                                                                                                                    |
| `STRIPE_SECRET_KEY`                 | Only when billing is enabled                                        | none                                               | Yes (secret) | Without it, Stripe stays disabled.                                                                                                                                                                                                                                                                                          |
| `STRIPE_WEBHOOK_SECRET`             | Only when billing is enabled                                        | none                                               | Yes (secret) | Missing while billing is enabled: the Stripe webhook is refused with 503.                                                                                                                                                                                                                                                   |
| `GUNICORN_WORKERS`                  | No                                                                  | `min(2 × CPU + 1, 8)`                              | No           | Worker process count. Production only.                                                                                                                                                                                                                                                                                      |
| `GUNICORN_TIMEOUT_SECONDS`          | No                                                                  | `120`                                              | No           | Restart threshold for a silent worker.                                                                                                                                                                                                                                                                                      |
| `GUNICORN_GRACEFUL_TIMEOUT_SECONDS` | No                                                                  | `30`                                               | No           | Time allowed for in-flight requests during restart.                                                                                                                                                                                                                                                                         |
| `GUNICORN_KEEPALIVE_SECONDS`        | No                                                                  | `5`                                                | No           | Keep-alive for idle connections.                                                                                                                                                                                                                                                                                            |
| `GUNICORN_MAX_REQUESTS`             | No                                                                  | `2000`                                             | No           | Requests per worker before recycling.                                                                                                                                                                                                                                                                                       |
| `GUNICORN_MAX_REQUESTS_JITTER`      | No                                                                  | `200`                                              | No           | Spread added to the recycle count.                                                                                                                                                                                                                                                                                          |
| `GUNICORN_LOG_LEVEL`                | No                                                                  | `info`                                             | No           | Gunicorn master log level.                                                                                                                                                                                                                                                                                                  |

## 2. Database

| Variable                                                  | Required                                                                              | Default                      | Console | Missing behaviour and notes                                                                                                                                                                                            |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`                                            | Yes (or the `DB_*` parts below)                                                       | none                         | No      | Async PostgreSQL URL, `postgresql+asyncpg://…`. When set, the `DB_*` values are ignored. Missing with no `DB_*` parts: the API still starts with a warning, database routes fail, and `/api/health/ready` returns 503. |
| `ALEMBIC_DATABASE_URL`                                    | No                                                                                    | falls back to `DATABASE_URL` | No      | Migration-only URL.                                                                                                                                                                                                    |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Only when `DATABASE_URL` is unset (all four of host, user, password, name are needed) | port `5432`                  | No      | The URL is built from these parts. The code does not percent-encode the password, so avoid `@ : / ? # %` in it.                                                                                                        |

## 3. Auth and email

| Variable                      | Required                        | Default                                       | Console                    | Missing behaviour and notes                                                                                                                                                                                                                                  |
| ----------------------------- | ------------------------------- | --------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `JWT_SECRET_KEY`              | Yes, always                     | none                                          | No                         | Signs access tokens. Missing or shorter than 32 characters: refuses to start. Also the fallback seed for OAuth state and for the unsubscribe-link key. Changing it invalidates tokens issued with the old key and the unsubscribe links.                     |
| `SECRET_KEY`                  | No                              | none                                          | No                         | Seed for OAuth state and for deriving the integration encryption key. Takes precedence over `JWT_SECRET_KEY` for those two uses.                                                                                                                             |
| `INTEGRATIONS_ENCRYPTION_KEY` | Set in production               | derived from `SECRET_KEY` or `JWT_SECRET_KEY` | No                         | Fernet key that encrypts stored integration tokens and console-saved values. If malformed, a warning is logged and a key is derived instead. If no seed exists, encryption fails closed. Changing it makes stored values unreadable. Not checked at startup. |
| `JWT_ISSUER`                  | No                              | `oraone-api`                                  | Yes                        | The `iss` claim written into and required on tokens.                                                                                                                                                                                                         |
| `JWT_ACCESS_TTL_MINUTES`      | No                              | `15`                                          | Yes                        | Access token lifetime.                                                                                                                                                                                                                                       |
| `JWT_REFRESH_TTL_DAYS`        | No                              | `30`                                          | Yes                        | Refresh token lifetime.                                                                                                                                                                                                                                      |
| `JWT_LEEWAY_SECONDS`          | No                              | `60`                                          | Yes                        | Clock-skew allowance when checking expiry.                                                                                                                                                                                                                   |
| `ALLOW_DEV_PASSWORD_LOGIN`    | No                              | `false`                                       | Local only                 | Only the exact value `true`, with `ENVIRONMENT=development`, enables password sign-in for seeded local accounts. Refused in production.                                                                                                                      |
| `SMTP_HOST`                   | Set in production (not checked) | none                                          | Yes                        | Mail server. Unset: each email is logged as not sent, so sign-in codes are never delivered and nobody can sign in. The sign-in request still returns the same response.                                                                                      |
| `SMTP_PORT`                   | No                              | `465`                                         | Yes                        | The code defaults to 465. The registry description says 587; the code is authoritative.                                                                                                                                                                      |
| `SMTP_USER`, `SMTP_PASSWORD`  | Only if the server needs login  | none                                          | Yes (password is a secret) | Login is attempted only when both are set.                                                                                                                                                                                                                   |
| `SMTP_FROM`                   | No                              | value of `SMTP_USER`                          | Yes                        | Sender address.                                                                                                                                                                                                                                              |
| `SMTP_USE_SSL`                | No                              | `true`                                        | Yes                        | `true` uses implicit TLS. `false` upgrades the connection with STARTTLS. Set `false` only for test servers.                                                                                                                                                  |

## 4. AI models

| Variable               | Required                          | Default                              | Console      | Missing behaviour and notes                                                                                                                                                                                                                                                |
| ---------------------- | --------------------------------- | ------------------------------------ | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OPENROUTER_API_KEY`   | Yes in production (startup check) | none                                 | Yes (secret) | The model provider for replies and embeddings. Missing in development: assistant replies use an extractive fallback (passages from the knowledge base, marked as not generated); assistant helpers return fallback results; embeddings use a local deterministic fallback. |
| `OPENROUTER_BASE_URL`  | No                                | `https://openrouter.ai/api/v1`       | Yes          | Empty value uses the default.                                                                                                                                                                                                                                              |
| `OPENROUTER_MODEL`     | No                                | `openai/gpt-5.5`                     | Yes          | Default model when an agent has no model of its own. Plan rules still apply through the model router unless `AI_FORCE_MODEL` is set. The template `backend/.env.example` uses a different default.                                                                         |
| `OPENROUTER_TIMEOUT`   | No                                | `60`                                 | Yes          | Seconds to wait for a model reply.                                                                                                                                                                                                                                         |
| `OPENROUTER_SITE_URL`  | No                                | `https://oraone.in`                  | Yes          | Sent to OpenRouter as the referring site, only when the base URL is OpenRouter.                                                                                                                                                                                            |
| `OPENROUTER_APP_NAME`  | No                                | `OraOne`                             | Yes          | Sent to OpenRouter as the application name.                                                                                                                                                                                                                                |
| `AI_FORCE_MODEL`       | No                                | unset                                | Yes          | Pins every reply to one model. It bypasses the model router, so plan-based model choice is not applied.                                                                                                                                                                    |
| `AI_MAX_OUTPUT_TOKENS` | No                                | `2048`                               | Yes          | Upper limit on reply length. Agent settings are capped to this value.                                                                                                                                                                                                      |
| `EMBEDDING_MODEL`      | No                                | `openai/text-embedding-3-small`      | Yes          | Embedding model, called through OpenRouter.                                                                                                                                                                                                                                |
| `EMBED_DIM`            | No                                | `1024`                               | No           | Vector size. Must match the database vector column. Changing it needs a migration and re-embedding.                                                                                                                                                                        |
| `EMBEDDING_TIMEOUT`    | No                                | `30`                                 | Yes          | Seconds to wait for an embedding request.                                                                                                                                                                                                                                  |
| `RERANKER_PROVIDER`    | No                                | `heuristic`                          | Yes          | One of `none`, `heuristic`, `cohere`, `jina`, `local`.                                                                                                                                                                                                                     |
| `RERANK_HTTP_TIMEOUT`  | No                                | `8.0`                                | Yes          | Seconds per remote rerank request.                                                                                                                                                                                                                                         |
| `COHERE_API_KEY`       | Only for `cohere`                 | none                                 | Yes (secret) | Without it, the Cohere reranker returns no scores and the code falls back.                                                                                                                                                                                                 |
| `COHERE_RERANK_MODEL`  | No                                | `rerank-english-v3.0`                | Yes          | Cohere model name.                                                                                                                                                                                                                                                         |
| `JINA_API_KEY`         | Only for `jina`                   | none                                 | Yes (secret) | Same fallback rule as Cohere.                                                                                                                                                                                                                                              |
| `JINA_RERANK_MODEL`    | No                                | `jina-reranker-v2-base-multilingual` | Yes          | Jina model name.                                                                                                                                                                                                                                                           |
| `BGE_RERANK_MODEL`     | No                                | `BAAI/bge-reranker-base`             | Yes          | Local rerank model, run on the API server.                                                                                                                                                                                                                                 |

## 5. WhatsApp

| Variable                     | Required                                            | Default | Console      | Missing behaviour and notes                                                                                        |
| ---------------------------- | --------------------------------------------------- | ------- | ------------ | ------------------------------------------------------------------------------------------------------------------ |
| `META_WHATSAPP_APP_SECRET`   | Yes when a Meta access token is set (startup check) | none    | Yes (secret) | Verifies the signature on every Meta POST, for WhatsApp and Instagram. Missing: all Meta POST webhooks return 401. |
| `META_WHATSAPP_VERIFY_TOKEN` | Yes for the webhook handshake                       | none    | Yes (secret) | The handshake (GET) returns 403 unless it matches. Instagram's handshake uses the same token.                      |
| `META_WHATSAPP_ACCESS_TOKEN` | Yes to send WhatsApp replies through Meta           | none    | Yes (secret) | Missing: messages are stored and answered, but the reply is not sent.                                              |

## 6. Instagram

| Variable                      | Required                      | Default | Console      | Missing behaviour and notes                                                                            |
| ----------------------------- | ----------------------------- | ------- | ------------ | ------------------------------------------------------------------------------------------------------ |
| `META_INSTAGRAM_ACCESS_TOKEN` | Yes to send Instagram replies | none    | Yes (secret) | Missing: the reply is not sent. Setting it makes the startup check require `META_WHATSAPP_APP_SECRET`. |

## 7. Twilio (SMS, WhatsApp through Twilio, voice and calls)

| Variable              | Required                                                           | Default | Console      | Missing behaviour and notes                                                                                                                                                                                  |
| --------------------- | ------------------------------------------------------------------ | ------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `TWILIO_ACCOUNT_SID`  | Yes when Twilio is used (startup check when any `TWILIO_*` is set) | none    | Yes          | Missing: Twilio webhooks return 401, SMS and WhatsApp replies are not sent, and calling returns 503.                                                                                                         |
| `TWILIO_AUTH_TOKEN`   | Same as above (secret)                                             | none    | Yes (secret) | Used to send messages and to verify `X-Twilio-Signature`. Missing: every Twilio webhook is refused.                                                                                                          |
| `TWILIO_PHONE_NUMBER` | Yes for outbound calls and SMS sending                             | none    | Yes          | Sender number, E.164. Missing: calling returns 503. Not checked at startup.                                                                                                                                  |
| `PUBLIC_API_BASE_URL` | Yes when any `TWILIO_*` is set (must be `https://`)                | none    | Yes          | Exact public origin Twilio calls. Signatures are checked against URLs built from it, and outbound call callbacks and the unsubscribe links use it. Missing: Twilio webhooks return 401 and calls return 503. |

## 8. Voice

| Variable               | Required | Default | Console | Missing behaviour and notes                                                                                                                    |
| ---------------------- | -------- | ------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `VOICE_HANDOFF_NUMBER` | No       | unset   | Yes     | E.164 number that a caller is transferred to when they ask for a person. Unset: the caller hears that no line is available, and the call ends. |
| `VOICE_SAY_VOICE`      | No       | `alice` | Yes     | Twilio voice used for spoken prompts.                                                                                                          |

ElevenLabs speech is documented in section 12.

## 9. Google

| Variable               | Required                    | Default                                                  | Console      | Missing behaviour and notes                                                                                    |
| ---------------------- | --------------------------- | -------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------- |
| `GOOGLE_CLIENT_ID`     | Yes to connect Google Drive | none                                                     | Yes          | Missing: Google Drive shows "requires account setup", and connect returns 503.                                 |
| `GOOGLE_CLIENT_SECRET` | Yes to connect Google Drive | none                                                     | Yes (secret) | Same as above.                                                                                                 |
| `GOOGLE_REDIRECT_URI`  | Set in production           | `http://localhost:3000/api/integrations/google/callback` | Yes          | Must match the redirect URI in the Google console. The default is a localhost address. Not checked at startup. |

Google Calendar and Google Sheets use their own names, listed in section 12.

## 10. Marketing email (inbound email)

| Variable               | Required               | Default | Console      | Missing behaviour and notes                                                                               |
| ---------------------- | ---------------------- | ------- | ------------ | --------------------------------------------------------------------------------------------------------- |
| `EMAIL_INBOUND_SECRET` | Only for inbound email | none    | Yes (secret) | Shared secret sent in the `X-Email-Inbound-Secret` header. Unset: every inbound email webhook is refused. |

Marketing campaigns by email cannot deliver yet, because no email sender is connected
on the server. See [PRODUCTS](../guides/PRODUCTS.md).

## 11. Widget

| Variable                       | Required | Default                  | Console | Missing behaviour and notes                                                                                  |
| ------------------------------ | -------- | ------------------------ | ------- | ------------------------------------------------------------------------------------------------------------ |
| `WIDGET_API_BASE`              | No       | `WIDGET_CDN_BASE` origin | Yes     | API origin the widget calls. Written as `data-api` in the embed snippet when it differs from the CDN origin. |
| `WIDGET_CDN_BASE`              | No       | `FRONTEND_URL`           | Yes     | Origin that serves `/widget.js`.                                                                             |
| `WIDGET_IP_RATE_LIMIT_PER_MIN` | No       | `60`                     | Yes     | Widget requests per client IP per minute. Invalid values use the default.                                    |

## 12. Limits and authorization switches

| Variable                        | Required | Default | Console | Missing behaviour and notes                                                                                                                                        |
| ------------------------------- | -------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ORAONE_FREE_ACCESS_ONLY`       | No       | `true`  | Yes     | Free-access mode. Only `false`, `0` or `no` turn it off. Payment processing runs only when this is off and `STRIPE_SECRET_KEY` is set. No startup check covers it. |
| `AUTHZ_ENFORCE_SUBSCRIPTION`    | No       | `false` | Yes     | When `true`, subscription status blocks protected features. When `false`, the decision is recorded only.                                                           |
| `AUTHZ_ENFORCE_QUOTAS`          | No       | `false` | Yes     | When `true`, quotas block requests once exceeded. A quota that cannot be measured still fails closed in production, whatever this value.                           |
| `RATE_LIMIT_AUTH_PER_MINUTE`    | No       | `10`    | Yes     | Sign-in and code requests per client per minute.                                                                                                                   |
| `RATE_LIMIT_AI_PER_MINUTE`      | No       | `20`    | Yes     | AI requests per client per minute.                                                                                                                                 |
| `RATE_LIMIT_WEBHOOK_PER_MINUTE` | No       | `600`   | Yes     | Webhook deliveries accepted per minute.                                                                                                                            |
| `RATE_LIMIT_API_PER_MINUTE`     | No       | `120`   | Yes     | General API requests per client per minute.                                                                                                                        |

## 13. Names the registry does not list

These are read by the code but are not in `config_registry.py`. The console cannot
set them, so set them in the server's environment or `backend/.env`. The OAuth names are read
by `backend/app/services/oauth_service.py`, which builds them from a prefix per provider:
`GOOGLE_CALENDAR`, `GOOGLE_SHEETS`, `SLACK`, `NOTION` and `HUBSPOT` (the registry covers only the
Google Drive pair `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`). Adding them to the registry is a code change.

| Variable                                                                                     | Required                        | Default             | Missing behaviour and notes                                                                                                                                                                                      |
| -------------------------------------------------------------------------------------------- | ------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ELEVENLABS_API_KEY`                                                                         | No                              | none                | Optional spoken replies for AI Voice. Both this and `ELEVENLABS_VOICE_ID` must be set. Otherwise the Twilio built-in voice is used. Any failure during a turn also falls back to the Twilio voice for that turn. |
| `ELEVENLABS_VOICE_ID`                                                                        | No                              | none                | Voice identifier. A malformed value is logged and the Twilio voice is used.                                                                                                                                      |
| `ELEVENLABS_MODEL_ID`                                                                        | No                              | `eleven_flash_v2_5` | ElevenLabs model.                                                                                                                                                                                                |
| `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_REDIRECT_URI`                               | Only to connect Slack           | none                | Missing: connect returns 503. The default redirect is `http://localhost:3000/api/integrations/oauth/callback`.                                                                                                   |
| `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, `NOTION_REDIRECT_URI`                            | Only to connect Notion          | none                | As above.                                                                                                                                                                                                        |
| `HUBSPOT_CLIENT_ID`, `HUBSPOT_CLIENT_SECRET`, `HUBSPOT_REDIRECT_URI`                         | Only to connect HubSpot         | none                | As above.                                                                                                                                                                                                        |
| `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_REDIRECT_URI` | Only to connect Google Calendar | none                | As above, with the same default redirect as Slack.                                                                                                                                                               |
| `GOOGLE_SHEETS_CLIENT_ID`, `GOOGLE_SHEETS_CLIENT_SECRET`, `GOOGLE_SHEETS_REDIRECT_URI`       | Only to connect Google Sheets   | none                | As above.                                                                                                                                                                                                        |
| `PORT`                                                                                       | No                              | `8000`              | Port the API binds to in its container (`gunicorn.conf.py`).                                                                                                                                                     |

Each redirect URI must match the one registered with the provider, and must be the
public address in production.

## 14. Compose and container variables

Read by `docker-compose.prod.yml` and the Dockerfiles. Put them in the file passed with
`--env-file`. Compose stops with an error when a variable marked required is missing.

| Variable             | Required | Default                      | Effect                                                                                  |
| -------------------- | -------- | ---------------------------- | --------------------------------------------------------------------------------------- |
| `DB_PASSWORD`        | Yes      | none                         | Password of the `oraone_admin` database user. Also embedded in the URLs Compose builds. |
| `OPENROUTER_API_KEY` | Yes      | none                         | Passed to the API, migrate and workers containers.                                      |
| `TRUSTED_PROXY_IPS`  | Yes      | none                         | Passed to the API, migrate and workers containers. See section 1.                       |
| `CADDY_DOMAIN`       | Yes      | `localhost` in the Caddyfile | Public host name. Caddy obtains the certificate for it.                                 |
| `ORAONE_VERSION`     | No       | `v1.0.0`                     | Image tag for the backend, frontend and migrate images.                                 |

Compose also sets these for the migrate, backend and workers containers. Values set in
Compose override values from `env_file`:

- `ENVIRONMENT=production`
- `DATABASE_URL` and `ALEMBIC_DATABASE_URL`, built from `DB_PASSWORD`
- `REDIS_URL=redis://redis:6379/0`
- `ENTITLEMENTS_CACHE_BACKEND=redis`
- `UPLOAD_DIR=/var/lib/oraone/uploads`
- `RUN_BACKGROUND_WORKERS` is `false` on migrate and backend, and `true` on workers

The migrate, backend and workers services also read `./backend/.env` through `env_file`.
That file must exist on the server.

## 15. Web application build and runtime

| Variable            | When read                       | Default                                          | Effect                                                            |
| ------------------- | ------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------- |
| `VITE_API_BASE_URL` | Build                           | empty (same-origin `/api`)                       | Set only if the API is on another origin.                         |
| `VITE_SITE_URL`     | Build                           | `https://oraone.in`                              | Canonical URLs, `robots.txt` and the sitemap. Set it for staging. |
| `API_PROXY_TARGET`  | Development and preview servers | `http://localhost:8000`                          | Where the Vite servers forward `/api`.                            |
| `NITRO_PRESET`      | Image build                     | `node-server` (set in `frontend.Dockerfile`)     | Build target for the Node server.                                 |
| `HOST`, `PORT`      | Image runtime                   | `0.0.0.0`, `8080` (set in `frontend.Dockerfile`) | Address and port of the Node server.                              |

`VITE_*` values are compiled into the build. Changing them needs a new build.

## 16. Operator scripts and migrations

Script paths are relative to `backend/`. The one exception is `scripts/capture-media.ts` in section 17,
which is at the repository root.

| Variable                                                            | Used by                                                                                                                                                     | Notes                                                                                                                                                                                                                                          |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`           | `scripts/bootstrap_db.py`, `scripts/backup_restore_drill.py` (defaults `localhost`, `5432`, `oraone`), `scripts/weekly_backup.py` (all required), `alembic` | Database connection parts.                                                                                                                                                                                                                     |
| `ORAONE_BACKUP_DIR`, `ORAONE_BACKUP_PASSPHRASE_FILE`                | `scripts/weekly_backup.py`                                                                                                                                  | Both required. The passphrase is read from a file.                                                                                                                                                                                             |
| `PLATFORM_BOOTSTRAP_APPROVED_SUBJECT`, `PLATFORM_BOOTSTRAP_CONFIRM` | `scripts/bootstrap_platform_admin.py`                                                                                                                       | The subject must equal the value on the command line. Confirm must be the exact text `PROMOTE_TO_SUPER_ADMIN`.                                                                                                                                 |
| `ENVIRONMENT`                                                       | `scripts/seed_dev_users.py`, `scripts/validate_local.ps1`                                                                                                   | The seed script refuses to run unless `ENVIRONMENT=development`.                                                                                                                                                                               |
| `ORG_ID`, `BATCH`                                                   | `scripts/reembed_org.py`                                                                                                                                    | `ORG_ID` is a required organisation UUID. `BATCH` is optional.                                                                                                                                                                                 |
| `PG_DSN` (or `DB_*`)                                                | `scripts/verify_rag_schema.py`                                                                                                                              | Connection for schema checks.                                                                                                                                                                                                                  |
| `DATABASE_URL`, `SMTP_HOST`, `AI_FORCE_MODEL`                       | `scripts/verify_product_local.py`                                                                                                                           | Local verification only.                                                                                                                                                                                                                       |
| `LOCAL_ADMIN_EMAIL`, `LOCAL_ADMIN_PASSWORD`                         | Migration `alembic/versions/20260820_0044_self_hosted_auth.py`, only while migrations run                                                                   | If both are set during `alembic upgrade`, a password hash is written to an existing account with that email that has no password, and the account is marked verified. It never creates accounts. Do not keep these set in an environment file. |

## 17. Test variables

| Variable       | Used by                                                                      | Default                                                                                                                                                    |
| -------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `E2E_BASE_URL` | `playwright.config.ts`, `e2e/multi-user.spec.ts`, `scripts/capture-media.ts` | The Playwright config defaults to `http://localhost:5173`. The multi-user spec and the media script default to `http://localhost:5180`. Set it explicitly. |

Backend tests set their own variables in fixtures, such as `ENVIRONMENT`, `DATABASE_URL`,
`JWT_SECRET_KEY` and `REDIS_URL`.

## 18. Production settings with no startup check

The startup check (`backend/app/core/startup_checks.py`) enforces `JWT_SECRET_KEY`, the
Twilio settings, the Meta app secret and `OPENROUTER_API_KEY`. `CORS_ORIGINS` is
enforced when the app builds its middleware. Everything else below has no check.
Set these deliberately on every production server:

- `DATABASE_URL` or the `DB_*` parts. Without them the API starts but cannot serve data.
- `REDIS_URL`. Without it, rate limits, sign-in codes and OAuth state fail closed.
- `FRONTEND_URL` and `APP_URL`. Without them, links point to `localhost`.
- `UPLOAD_DIR`. Without it, uploads go to `/tmp`.
- `SMTP_HOST` and the SMTP credentials. Without them, nobody can sign in.
- Each OAuth `*_REDIRECT_URI` you use. Without them, callbacks point to `localhost`.
- `INTEGRATIONS_ENCRYPTION_KEY`. Without it, the key is derived from the JWT or
  `SECRET_KEY` value. Rotating that value then makes stored integration tokens and
  console-saved values unreadable.
- `TRUSTED_PROXY_IPS`. Compose requires it. Without it, rate limits collapse onto the proxy address.
- `ORAONE_FREE_ACCESS_ONLY`. Leave the default unless billing is intended.

## 19. Secrets the admin inventory reports

The read-only inventory at `GET /api/super-admin/secrets` reports these twelve names
only: `OPENROUTER_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `JWT_SECRET_KEY`, `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`, `DATABASE_URL`, `REDIS_URL`, `SMTP_HOST` and `SMTP_PASSWORD`.
The configuration console covers the registry instead, and reports the masking rules
described in [ADMIN-CONFIG](../guides/ADMIN-CONFIG.md).
