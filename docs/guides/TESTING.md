# Testing

OraOne has four layers of automated tests. Each runs in CI on every push and pull
request.

| Layer                        | Tool                   | Command                                                | Covers                                          |
| ---------------------------- | ---------------------- | ------------------------------------------------------ | ----------------------------------------------- |
| Web unit                     | Vitest                 | `bun run test`                                         | API client, mapping rules, UI helpers           |
| Backend unit and integration | pytest                 | `cd backend && python -m pytest -q`                    | Auth, tenancy, RAG, billing, workers, endpoints |
| End-to-end                   | Playwright             | `bun run test:e2e`                                     | The running application in real browsers        |
| Formatting and lint          | Prettier, ESLint, Ruff | `bun run format:check`, `bun run lint`, `ruff check .` | Code quality                                    |

## End-to-end suites

Playwright suites are tagged in their titles. Each tag can be run on its own.

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

The first run installs the browsers:

```bash
bunx playwright install --with-deps chromium firefox webkit
```

### Sitemap, widget and install

`e2e/seo.spec.ts` reads `public/sitemap.xml`, which `scripts/generate-sitemap.ts` writes from the route inventory before every build. `e2e/widget.spec.ts` checks that `widget.js` is served and that the install screen offers the script tag, SDK and React code.

### Browsers and devices

Projects: desktop Chromium, Firefox and WebKit, plus Pixel 7 (Android Chrome) and
iPhone 14 (Safari). Tests that depend on the viewport skip themselves on the other
kind of device.

### Visual baselines

Baselines live in `e2e/visual.spec.ts-snapshots/`. Review every change before you
update them:

```bash
bun run test:e2e:visual -- --update-snapshots
```

### Reports

Failing runs keep a trace, a screenshot and an HTML report in `playwright-report/`.
CI uploads these as artifacts.

## Backend tests

`backend/tests/` uses a real PostgreSQL database for database-backed tests, and
skips them cleanly when none is reachable. CI runs them against a pgvector service.

## Formatting

- Web: `bun run format` (Prettier) and `bun run lint:fix` (ESLint).
- Backend: `cd backend && ruff format . && ruff check . --fix`.

The **Fix formatting** workflow applies the same commands in CI and opens a pull request.
