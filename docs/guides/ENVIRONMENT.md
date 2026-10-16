# Environment configuration

Configuration comes from environment variables. For local work they are read from
`backend/.env` and `.env.local` (both git-ignored). Production values are injected
by the deployment platform and are never committed.

Templates: [`backend/.env.example`](../../backend/.env.example) and
[`.env.example`](../../.env.example).

## Backend

### Runtime and security

| Variable                   | Required | Purpose                                                                                                                |
| -------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------- |
| `ENVIRONMENT`              | yes      | `development`, `staging` or `production`. Production-like values forbid development shortcuts.                         |
| `JWT_SECRET_KEY`           | yes      | Signs access tokens. Must be at least 32 characters.                                                                   |
| `JWT_ACCESS_TTL_MINUTES`   | no       | Access-token lifetime. Default `15`.                                                                                   |
| `JWT_REFRESH_TTL_DAYS`     | no       | Refresh-token lifetime. Default `30`.                                                                                  |
| `ALLOW_DEV_PASSWORD_LOGIN` | no       | `true` enables `POST /api/auth/dev-login` for the seeded local accounts. Only honoured when `ENVIRONMENT=development`. |

### Data

| Variable               | Required    | Purpose                                                                                                 |
| ---------------------- | ----------- | ------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`         | yes         | Async PostgreSQL URL (`postgresql+asyncpg://…`).                                                        |
| `ALEMBIC_DATABASE_URL` | yes         | Sync URL used by migrations (`postgresql+psycopg2://…`).                                                |
| `REDIS_URL`            | recommended | Shared cache, sign-in codes and rate limits. Falls back to in-process memory when unset in development. |
| `UPLOAD_DIR`           | no          | Directory for uploaded documents. Must be owned by the application user.                                |

### AI (OpenRouter)

OraOne calls every model through [OpenRouter](https://openrouter.ai). No other AI
provider is supported.

| Variable                  | Required            | Purpose                                                                                                                                                       |
| ------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OPENROUTER_API_KEY`      | yes, for AI replies | Your OpenRouter key. Without it, assistant replies return a clear provider error.                                                                             |
| `OPENROUTER_MODEL`        | no                  | Default model id. Supported ids: `openai/gpt-5.5`, `anthropic/claude-sonnet-4`, `google/gemini-2.5-pro`, `google/gemini-2.5-flash`. Default `openai/gpt-5.5`. |
| `ORAONE_FREE_ACCESS_ONLY` | no                  | `true` (default) keeps every organization on Free. Set `false` for local development only.                                                                    |
| `WIDGET_API_BASE`         | no                  | Public origin of the API that website widgets call. Defaults to the web origin.                                                                               |
| `WIDGET_CDN_BASE`         | no                  | Origin that serves `widget.js`, used by the backend's embed snippets. Defaults to `FRONTEND_URL`.                                                             |
| `OPENROUTER_BASE_URL`     | no                  | Defaults to `https://openrouter.ai/api/v1`.                                                                                                                   |
| `AI_FORCE_MODEL`          | no                  | Pins every assistant to one model, for cost control.                                                                                                          |
| `EMBEDDING_MODEL`         | no                  | Embedding model used through OpenRouter for knowledge search.                                                                                                 |

A model is used only when the organization's plan allows it. `openai/gpt-5.5` and
`anthropic/claude-sonnet-4` need the Business plan, `google/gemini-2.5-pro` needs
Starter, and `google/gemini-2.5-flash` is available on every plan. In development,
`python scripts/seed_dev_users.py` moves the local accounts' organizations to the Business plan.
It needs `ORAONE_FREE_ACCESS_ONLY=false` in `backend/.env`; the seed script refuses to run
outside `ENVIRONMENT=development`.
| `EMBED_DIM` | no | Embedding size. Must match the database column. Default `1024`. |

### Email

| Variable                                               | Required               | Purpose                                                  |
| ------------------------------------------------------ | ---------------------- | -------------------------------------------------------- |
| `SMTP_HOST`                                            | yes, for sign-in codes | SMTP server. Without it, codes are logged as not sent.   |
| `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | with `SMTP_HOST`       | Credentials and sender address.                          |
| `SMTP_USE_SSL`                                         | no                     | `true` (default) for implicit TLS; `false` for STARTTLS. |

### Web origin

| Variable       | Purpose                                                   |
| -------------- | --------------------------------------------------------- |
| `FRONTEND_URL` | Base URL used in email links.                             |
| `CORS_ORIGINS` | Comma-separated origins allowed to call the API directly. |

## Web application

| Variable            | Purpose                                                                                                  |
| ------------------- | -------------------------------------------------------------------------------------------------------- |
| `VITE_API_BASE_URL` | Leave empty to use same-origin `/api` (recommended).                                                     |
| `API_PROXY_TARGET`  | Where the Vite dev and preview servers forward `/api`. Default `http://localhost:8000`.                  |
| `VITE_SITE_URL`     | Public origin used for canonical links and the sitemap. Default `https://oraone.in`. Set it for staging. |

## Test suites

| Variable       | Purpose                                                         |
| -------------- | --------------------------------------------------------------- |
| `E2E_BASE_URL` | Web origin used by Playwright. Default `http://localhost:5180`. |
