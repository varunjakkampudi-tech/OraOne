# OraOne

OraOne is an AI chat platform for websites. Businesses build assistants, teach them
from their own documents, test them in a playground and review conversations and
leads. **Product 1, the OraOne AI Chat Platform, is this repository.**

## What it includes

| Area                                                  | Status                                                            |
| ----------------------------------------------------- | ----------------------------------------------------------------- |
| Passwordless sign-in with email codes                 | Available                                                         |
| Workspaces (projects) and organizations               | Available                                                         |
| Assistants: configuration and playground              | Available, AI replies use OpenRouter                              |
| Website chat: script tag, browser SDK, React and REST | Available, see the [website guide](docs/guides/WEBSITE-WIDGET.md) |
| Conversations inbox                                   | Available                                                         |
| Leads                                                 | Available                                                         |
| Knowledge documents and search                        | Available                                                         |
| Team, billing and usage, analytics, API keys, account | Available                                                         |
| Public marketing site, documentation and legal pages  | Available                                                         |
| Staff console                                         | Available to platform administrators                              |

The repository also contains code for AI voice, WhatsApp, Instagram, the omnichannel
inbox, workflows, marketing campaigns, the marketplace, integrations and calls. Several of
these need a setup step that is not yet available in Studio. Mobile applications are not in
this repository, and OraOne OS is a long-term vision. The status and blockers of each are in
[PRODUCTS](docs/guides/PRODUCTS.md) and [PRODUCT-PORTFOLIO](docs/PRODUCT-PORTFOLIO.md).

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
development builds, and these accounts exist only in development.

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

| Workflow              | Purpose                                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| `format-and-lint.yml` | Checks formatting, ESLint, TypeScript and Ruff on every push and pull request.                          |
| `test-suites.yml`     | Web unit tests, backend tests, and the Playwright suites (smoke, sanity, critical, regression, visual). |
| `fix-formatting.yml`  | Manual. Formats the code and opens a pull request.                                                      |

## Documentation

- [Architecture and flow diagrams](docs/architecture/DIAGRAMS.md)
- [Quickstart](docs/guides/QUICKSTART.md)
- [Add OraOne to your website](docs/guides/WEBSITE-WIDGET.md)
- [Environment variables](docs/guides/ENVIRONMENT.md)
- [Authentication and authorization](docs/architecture/AUTHENTICATION-RBAC.md)
- [Testing](docs/guides/TESTING.md)
- [Deployment](docs/operations/DEPLOYMENT.md)
- [Troubleshooting](docs/guides/TROUBLESHOOTING.md)
- [Security model](docs/security/SECURITY-MODEL.md)

## Licence

See [LICENSE](LICENSE). All rights reserved by OraOne Technologies Pvt. Ltd.
