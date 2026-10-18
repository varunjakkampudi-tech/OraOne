# OraOne

OraOne is an AI chat platform for websites. Businesses build assistants, teach them
from their own documents, test them in a playground and review conversations and
leads. **Product 1, the OraOne AI Chat Platform, is this repository.**

## What it includes

Status uses the portfolio labels: **Built** (code and tests exist), and **Live-needs-account** (the
code is built, but a service needs accounts, mail or a setup step before customers can use it).

| Area                                                  | Status                                                                                   |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Passwordless sign-in with email codes                 | Built. Live-needs-account: production needs a mail server for sign-in codes              |
| Workspaces (projects) and organizations               | Built                                                                                    |
| Assistants: configuration and playground              | Built. Live-needs-account: AI replies need an OpenRouter key                             |
| Website chat: script tag, browser SDK, React and REST | Built, see the [website guide](docs/guides/WEBSITE-WIDGET.md)                            |
| Conversations inbox                                   | Built                                                                                    |
| Leads and import                                      | Built                                                                                    |
| Knowledge documents and search                        | Built                                                                                    |
| Team, billing and usage, analytics, API keys, account | Built. Billing is off (free access)                                                      |
| Public marketing site, documentation and legal pages  | Built                                                                                    |
| Configuration console (staff)                         | Built. Other platform administration pages are empty states until their services connect |

The repository also contains code for AI voice, WhatsApp, Instagram, the omnichannel
inbox, workflows, marketing campaigns, the marketplace, integrations and calls. Several of
these are Live-needs-account: they need a provider account and a setup step that Studio does not
yet offer. Mobile applications are not in this repository, and OraOne OS is a long-term vision.
The status and blockers of each are in [PRODUCTS](docs/guides/PRODUCTS.md) and
[PRODUCT-PORTFOLIO](docs/PRODUCT-PORTFOLIO.md).

## Architecture

| Path                      | What it is                                                                       |
| ------------------------- | -------------------------------------------------------------------------------- |
| `src/`                    | Web application (TanStack Start and React), server-rendered by Nitro.            |
| `backend/`                | FastAPI API, PostgreSQL models, Alembic migrations, background worker and tests. |
| `e2e/`                    | Playwright end-to-end suites.                                                    |
| `docs/`                   | Architecture, guides and operations documentation.                               |
| `docker-compose.dev.yml`  | Local PostgreSQL (pgvector) and Redis.                                           |
| `docker-compose.prod.yml` | Production stack behind Caddy.                                                   |

The web application calls the API through its own origin at `/api`. Sessions are
httpOnly cookies, so no token is stored in the browser.

**AI provider:** every model call goes through [OpenRouter](https://openrouter.ai).
No other AI provider is used.

## Quick start

The full instructions are in [docs/guides/QUICKSTART.md](docs/guides/QUICKSTART.md).

```bash
docker compose -f docker-compose.dev.yml up -d postgres redis

cd backend
cp .env.example .env            # set JWT_SECRET_KEY and ALLOW_DEV_PASSWORD_LOGIN=true
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python scripts/seed_dev_users.py
.venv/Scripts/python -m uvicorn server:app --reload --port 8000

# in a second terminal, from the repository root
bun install
bun run dev                      # http://localhost:5180
```

### Local accounts

| Account           | Password          | Role           |
| ----------------- | ----------------- | -------------- |
| `varun@oraone.in` | `varun@oraone.in` | user           |
| `admin@oraone.in` | `oraone.in`       | platform owner |

Use the **Developer sign-in** panel on the sign-in page. It appears only in
development builds, and these accounts exist only in development. The seed script
refuses to run outside `ENVIRONMENT=development`. Never seed these accounts on a server.

## Commands

| Task                    | Command                                                                          |
| ----------------------- | -------------------------------------------------------------------------------- |
| Type check              | `bun run typecheck`                                                              |
| Lint                    | `bun run lint`                                                                   |
| Format check            | `bun run format:check`                                                           |
| Format and fix          | `bun run format` and `bun run lint:fix`                                          |
| Unit tests              | `bun run test`                                                                   |
| Production build        | `bun run build`                                                                  |
| Backend tests           | `cd backend && python -m pytest -q`                                              |
| Backend format and lint | `cd backend && ruff format . && ruff check .`                                    |
| End-to-end, all suites  | `bun run test:e2e`                                                               |
| Single end-to-end suite | `bun run test:e2e:smoke` (also `:sanity`, `:critical`, `:regression`, `:visual`) |

See [docs/guides/TESTING.md](docs/guides/TESTING.md) for prerequisites and suites.

## Continuous integration

| Workflow             | Purpose                                                                                                                                                                   |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ci.yml`             | On pull requests and pushes to `main`. Web lint, typecheck, unit tests and build; backend Ruff checks, migrations and tests; Playwright browser tests at 390 and 1280 px. |
| `deploy.yml`         | Manual only (`workflow_dispatch`), and only from `main`. Uses the `production` environment and the secrets `DEPLOY_HOST`, `DEPLOY_USER` and `DEPLOY_SSH_KEY`.             |
| `fix-formatting.yml` | Manual. Formats the code and opens a pull request.                                                                                                                        |

Nothing deploys on a push or a pull request. The deploy workflow runs only when someone starts it
from the Actions tab. See [HOSTINGER-DEPLOYMENT](docs/HOSTINGER-DEPLOYMENT.md) for the server and the
secrets that must be set first.

## Documentation

- [Vision and mission (draft for owner review)](docs/VISION-AND-MISSION.md)
- [Product portfolio: status and blockers](docs/PRODUCT-PORTFOLIO.md)
- [Products guide: what each part does and how to set it up](docs/guides/PRODUCTS.md)
- [Architecture and flow diagrams](docs/architecture/DIAGRAMS.md)
- [Quickstart](docs/guides/QUICKSTART.md)
- [Add OraOne to your website](docs/guides/WEBSITE-WIDGET.md)
- [Configuration reference (every environment variable)](docs/operations/CONFIGURATION.md)
- [Authentication and authorization](docs/architecture/AUTHENTICATION-RBAC.md)
- [Testing](docs/guides/TESTING.md)
- [Deployment (generic Compose steps)](docs/operations/DEPLOYMENT.md)
- [Hostinger production deployment](docs/HOSTINGER-DEPLOYMENT.md)
- [Backup and restore](docs/operations/BACKUP-RESTORE.md)
- [Troubleshooting and runbook](docs/operations/RUNBOOK.md)
- [Security controls and accepted risks](docs/operations/SECURITY.md)
- [Security model](docs/security/SECURITY-MODEL.md)
- [Admin and configuration guide](docs/guides/ADMIN-CONFIG.md)
- [Security reporting](SECURITY.md)

## Licence

See [LICENSE](LICENSE). All rights reserved by OraOne Technologies Pvt. Ltd.
