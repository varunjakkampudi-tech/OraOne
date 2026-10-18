# Testing

OraOne has four layers of automated tests. CI (`.github/workflows/ci.yml`) runs the web lint,
typecheck and unit tests, the backend lint and tests, and the Playwright browser tests at 390 and
1280 px. It runs on pull requests and on pushes to `main`. The 768 px browser project is not run
in CI.

| Layer                        | Tool                   | Command                                                | Covers                                          |
| ---------------------------- | ---------------------- | ------------------------------------------------------ | ----------------------------------------------- |
| Web unit                     | Vitest                 | `bun run test`                                         | API client, mapping rules, UI helpers           |
| Backend unit and integration | pytest                 | `cd backend && python -m pytest -q`                    | Auth, tenancy, RAG, billing, workers, endpoints |
| End-to-end                   | Playwright             | `bun run test:e2e`                                     | The running application in real browsers        |
| Formatting and lint          | Prettier, ESLint, Ruff | `bun run format:check`, `bun run lint`, `ruff check .` | Code quality                                    |

## End-to-end suites

Playwright suites are tagged in their titles. Each tag can be run on its own.

Only the spec files named in `testMatch` in `playwright.config.ts` run by default:
`public-site`, `studio`, `channel-setup`, `admin`, `install`, `auth` and `route-health`. The tags
below apply to tests in those files. The other spec files in `e2e/` are not in that list, so the
tag commands do not run them unless the config changes.

| Suite         | Tag           | Purpose                                                                                                                                                                     |
| ------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Smoke         | `@smoke`      | Fast check that the main pages render: brand, logo, hero, sign-in and the sample workspace.                                                                                 |
| Sanity        | `@sanity`     | Every representative Product 1 route responds with status 200, renders a heading and has no broken images.                                                                  |
| Critical      | `@critical`   | Sign-in, protected routes, sign-out and the studio flows that must never break.                                                                                             |
| Regression    | `@regression` | Navigation, product menus, the mobile menu, video sources, error pages and tabs.                                                                                            |
| Visual        | `@visual`     | Screenshot comparison of the home page, sign-in and the sample dashboard.                                                                                                   |
| Accessibility | `@regression` | axe scans (WCAG 2.1 AA) of the public pages, sample workspace, studio and install screens. Serious and critical findings fail the run. `e2e/accessibility.spec.ts`          |
| Responsive    | `@regression` | No horizontal page overflow at 360, 390, 768 and 1280 px across public, sample and studio screens. `e2e/responsive.spec.ts`                                                 |
| SEO           | `@regression` | Every sitemap page returns 200 with a title, description, a canonical link to itself, one h1 and `lang`. `e2e/seo.spec.ts`                                                  |
| Links         | `@regression` | Every internal link on the main screens resolves to a page that exists. `e2e/links.spec.ts`                                                                                 |
| Controls      | `@regression` | Clicks every safe button on the main screens and fails on any uncaught page error. Controls that change data or end the session are skipped by name. `e2e/controls.spec.ts` |

```bash
bun run test:e2e:smoke
bun run test:e2e:sanity
bun run test:e2e:critical
bun run test:e2e:regression
bun run test:e2e:visual
bun run test:e2e            # all suites, all browsers
```

### Prerequisites

The suites run against the full local stack:

1. Start PostgreSQL and Redis (`docker compose -f docker-compose.dev.yml up -d postgres redis`).
2. Migrate and seed: `cd backend && alembic upgrade head && python scripts/seed_dev_users.py`.
3. Start the API with `ALLOW_DEV_PASSWORD_LOGIN=true` in `backend/.env`.
4. Start the web app with `bun run dev`, or point `E2E_BASE_URL` at a running build.

The first run installs the browser:

```bash
bunx playwright install --with-deps chromium
```

### Sitemap, widget and install

`e2e/seo.spec.ts` reads `public/sitemap.xml`, which `scripts/generate-sitemap.ts` writes from the route inventory before every build. `e2e/widget.spec.ts` checks that `widget.js` is served and that the install screen offers the script tag, SDK and React code.

### Browsers and devices

Projects in `playwright.config.ts`: Chromium at 390, 768 and 1280 px. CI runs the 390 and 1280
projects. Firefox, WebKit and mobile device emulation are not configured.

### Visual baselines

Baselines live in `e2e/visual.spec.ts-snapshots/`. Review every change before you
update them:

```bash
bun run test:e2e:visual -- --update-snapshots
```

### Reports

Failing runs keep a trace and a screenshot in `test-results/`. The config uses the list reporter,
so no HTML report is written by default. When the browser job fails, CI uploads `test-results/`
and `playwright-report/` as an artifact.

## Backend tests

`backend/tests/` uses a real PostgreSQL database for database-backed tests, and
skips them cleanly when none is reachable. CI runs them against a pgvector service.

## Formatting

- Web: `bun run format` (Prettier) and `bun run lint:fix` (ESLint).
- Backend: `cd backend && ruff format . && ruff check . --fix`.

The **Fix formatting** workflow applies the same commands in CI and opens a pull request.
