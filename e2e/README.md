# End-to-end tests for the product surfaces

These tests open the web app in a real browser and check that each page a visitor or a signed-in user can reach shows its main content, does not scroll sideways, and throws no uncaught JavaScript errors. The configured widths are 390 px (phone), 768 px (tablet) and 1280 px (desktop). The CI browser job runs 390 px and 1280 px only. Run 768 px locally with `--project=768`.

## How to run

From the repository root:

```sh
npm run test:e2e
```

- If the web app is already running on http://localhost:5173, the tests use it.
- If nothing is running there, Playwright starts `npm run dev` for the run and stops it afterwards.
- To test another address, set `E2E_BASE_URL`, for example `E2E_BASE_URL=http://localhost:5180 npm run test:e2e`.
- The browser is the Chromium build that is already installed on this machine (Playwright's `chromium-1248`). If it is missing on another machine, run `npx playwright install chromium` once. The tests do not download browsers on their own.
- No backend is needed for the default run. The Studio and install pages get their data from a mock inside the browser.

Results print one line per test and project (`390`, `768`, `1280`). A failing run saves a screenshot and a trace under `test-results/`.

## What each file proves

Files are listed in the order they run. Each one runs at all three widths.

| File                  | What it proves                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `public-site.spec.ts` | The homepage, products, pricing, docs, contact, privacy, terms and cookie pages load, show a main heading, do not scroll sideways, and throw no uncaught errors.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `studio.spec.ts`      | The OraOne OS hub at `/studio` shows its heading and one card per product area, and the four navigation groups are present. Channel cards read "Not connected yet" with no assistant, and "Connected" for website chat when the mock reports an active chat channel. The four channel setup pages (`/studio/channels/<name>`) show their checklist, and an unknown name shows a plain message. Assistants (`/studio/assistants`), Inbox, Leads, Team, Billing, Calls and Workflows show their main heading with the mocked account. The Inbox channel filter appears when there is at least one conversation. The Calls page shows its "No call campaigns yet." empty state. |
| `admin.spec.ts`       | `/admin?preview=design` shows the design-preview notice (not signed in, no admin permissions, sample data only). The Users page reports "Data source not connected" instead of listing real users.                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `install.spec.ts`     | The assistant install page shows the "Copy code" control and the "Waiting for first visit" state, because the mock reports that no visitor has loaded the widget yet.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `auth.spec.ts`        | The sign-in page shows the email-code form and the form has no password field. Nothing is submitted.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

Shared code:

- `product-support.ts` holds the API mock, the horizontal-scroll check, the page-error collector and the hydration wait.
- `fixtures.ts` (existing) blocks Google Fonts requests so a slow font host cannot change the results.

## What is mocked

Studio and install tests answer every `/api` request inside the browser with fixed fake data. Requests whose path does not start with `/api/` are passed through untouched, so the app's own modules still load.

- The account is `mock.user@example.test`, the organization is "Mock Organization", and the workspace is "Mock workspace".
- Lists are empty, except for the widget on the install page and one fake conversation in the Inbox filter test.
- The hub's "Connected" test answers `/api/agents` and `/api/agents/<id>/channels` with one assistant and an active website chat channel. Without an assistant, every channel card reads "Not connected yet".
- Billing shows a free "Starter" plan with no charges.
- The mock accepts only `GET`. Any write returns 405, so the tests cannot change data.
- Unknown `/api` paths return 404, so a missing mock shows up as an error on the page.

The auth and admin tests do not call the API. The public pages are not mocked; they are served by the dev server.

## What is not tested here, and what needs a real account

These checks need a real environment and are not covered by this suite:

- **Real sign-in.** The email-code flow, email delivery and session cookies are not exercised. The suite never requests a code.
- **Real workspace data.** Assistants, conversations, leads, calls, team members and billing are shown from fixtures only. Real data needs a signed-in test account on a running backend.
- **Verified website install.** The install page is only checked in its waiting state. Confirming a visit needs the widget embedded on a real site.
- **Staff admin.** The Admin Console is a design preview. Staff sign-in is not connected yet, so there is nothing real to test.
- **Development-only password panel.** The sign-in page in development builds also shows a password form for seeded developer accounts. It is intentionally outside the checked form and does not exist in production builds.
- **Other pages.** Only the routes listed above are covered. Onboarding, the older `/app` workspace and the remaining Studio pages are not in this suite.

## Older suites in this folder

The other `*.spec.ts` files in this folder (for example `critical.spec.ts`, `multi-user.spec.ts`, `visual.spec.ts`) were written for a live backend, a different port and several browsers. They are not part of `npm run test:e2e`, which runs only the five files above. They are kept as they were and can be run separately once their backend and accounts are set up.
