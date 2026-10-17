# Development commands

Commands for the frontend (repository root) and the backend (`backend/`). Frontend scripts are
defined in `package.json`; `bun` is the package manager (`bun.lock`), and `npm run <script>` runs
the same scripts. Run commands from the repository root unless noted.

## Install

```bash
# Frontend
bun install

# Backend (Python 3.11+)
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows; use .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
```

## Run the app

```bash
bun run dev        # Vite dev server
bun run build      # production build (runs the sitemap generator first)
bun run preview    # serve the built output
```

## Lint, format and type-check

| Task          | Frontend                                         | Backend                               |
| ------------- | ------------------------------------------------ | ------------------------------------- |
| Lint          | `bun run lint` (ESLint, Prettier rules included) | `cd backend && ruff check .`          |
| Auto-fix lint | `bun run lint:fix`                               | `cd backend && ruff check . --fix`    |
| Format        | `bun run format` (Prettier)                      | `cd backend && ruff format .`         |
| Format check  | `bun run format:check`                           | `cd backend && ruff format --check .` |
| Type check    | `bun run typecheck` (`tsc --noEmit`)             | not applicable                        |

Shortcut for the backend: `bun run backend:lint` (format check and lint) and `bun run backend:format`.

## Unit tests

```bash
bun run test          # Vitest, single run
bun run test:watch    # Vitest, watch mode

cd backend
python -m pytest -q   # backend test suite
```

## End-to-end tests (Playwright)

```bash
bun run test:e2e              # all suites
bun run test:e2e:smoke        # also :sanity, :critical, :regression, :visual
```

Suites are tagged in `e2e/`; see `e2e/README.md` for setup details.

## Before opening a pull request

1. `bun run typecheck`
2. `bun run lint` and `bun run format:check`
3. `bun run test`
4. `cd backend && ruff format --check . && ruff check . && python -m pytest -q`
5. `bun run build` when the change touches routes, configuration or the build.

Do not commit secrets. Keep `backend/.env` local.
