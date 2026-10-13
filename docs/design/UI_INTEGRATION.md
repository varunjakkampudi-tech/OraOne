# OraOne design migration and UI integration

## Authoritative implementation

`frontend/` is the only application frontend. It uses the existing FastAPI backend and preserves real authorization, project, analytics, knowledge, integration, widget, team, usage, and administration contracts. No Lovable/Supabase runtime or sample-data service is used by the application.

The migrated customer shell provides:

- one global OraOne header with the existing logo;
- separate workspace and project context;
- grouped Product 1 navigation for dashboard, agents, conversations, leads, analytics, knowledge, integrations, website widget, team, usage, and settings;
- responsive mobile navigation without a duplicate desktop brand;
- explicit loading, empty, unavailable, and retry states instead of invented operational claims;
- custom email authentication screens for the self-hosted flow while Cognito integration is intentionally deferred.

## Portfolio and route migration

The reference design repository's checked-in `ROUTES.csv` contains 283 destination paths. The matching inventory is retained at `frontend/e2e/route-inventory.json` with its path family and source metadata; `frontend/e2e/route-migration.spec.js` visits every entry at a 390px viewport and checks rendering, browser runtime errors, and horizontal overflow. Dynamic path parameters are replaced with deterministic test identifiers. This is route coverage evidence, not a claim that every route is a distinct approved visual design.

The shared product catalog lives in `frontend/src/constants/productCatalog.js`. The product directory and marketing catalog use that single source for names, scope, and lifecycle labels. Product 1 destinations continue to resolve to the existing functional app screens. Products 2–9 and Product 10 have cohesive, responsive design-preview routes under `/app/products/:productSlug/*`; `/studio/*` resolves to the AI Studio preview. Preview screens explicitly state that functionality is not yet active and do not fabricate live usage metrics or vendor status. Marketing pages for future products likewise identify planned scope rather than presenting it as released.

Compatibility paths in the reference inventory resolve to an existing canonical feature, a product design preview, an authenticated admin destination, or the existing not-found/unavailable state. They do not add duplicate application modules or imply separate implementations for every URL variant.

## Design and approval status

`DESIGN_SYSTEM.md` is the canonical visual/shell specification; `DESIGN.md` describes how this migration applies it. The migration preserves the current logo, typography, palette, and shell. `route-inventory.json` and its browser test provide deterministic route-level evidence; they do not assert screenshot-level parity against every Stitch/Lovable frame. Each screen still requires human visual acceptance for final pixel-level approval. This task did not perform a screenshot-by-screenshot Stitch inventory or obtain owner visual approval.

## Compatibility routes

The application keeps canonical functional routes such as `/app/agents`, `/app/conversations`, `/app/knowledge-base`, and `/app/settings`. Design-export URLs resolve to functional screens or compatibility redirects. Customer profiles and assistant-specific knowledge/analytics preserve their record-scoped URLs rather than collapsing into aggregate lists. Where a detail view is available, record identifiers select the matching record. Records absent from the active workspace show an unavailable state instead of opening unrelated content. Platform user and organization routes stay inside the server-gated admin shell; user search accepts an exact user ID as well as email/name.

Future-product design URLs are not treated as implemented services. The product directory remains the truthful entry point: Product 1 is active; Products 2–9 are planned; Product 10 is the long-term vision.

## Verification boundary

The browser suite checks the custom email authentication presentation and flows, Product 1 route compatibility, the reference route inventory, responsive shell behavior, unavailable-data behavior, and primary Product 1 screens. The full-inventory test uses a 390px viewport and checks for runtime exceptions, error-boundary rendering, empty roots, and horizontal overflow. It is not a substitute for interaction-by-interaction acceptance or screenshot review. Backend tests, SDK tests, ESLint, Prettier, and the production build remain separate release gates.

These checks do not constitute production deployment, live inbox delivery, or owner approval of every visual detail.

## Design-first integration pass — 13 October 2026

The visual reference was retrieved from Lovable project
`248b62ff-6461-43fa-8b39-cbc54076af43`, commit
`4b77cd781fd834862c06240fbffa224d0ea11ae3`. Reference-only exports are kept outside
the application repository. Its demo services were not imported.

This pass integrates the public navigation and hero, shared authentication frame,
workspace navigation, assistant cards and editor tabs, unified inbox and customer
profile, selected-assistant playground, knowledge surfaces, team/settings, and
platform-admin shell. The original logo and real API contracts remain in use.
Future modules remain explicitly planned design previews.

Executed final checks in this pass:

- Frontend ESLint passed with zero errors/warnings; Prettier and Git diff checks passed.
- Production build passed (largest entry bundle 424.34 kB; charts 377.29 kB).
- Playwright: **23 passed in 4.0 minutes**, including all **283 reference destinations**
  at a 390px viewport, primary Product 1 screens, auth presentation/flows, record
  deep links, admin compatibility, mobile Settings overflow and session retry.
- SDK compatibility: **1 passed**, verifying SSR safety and deferred-loader queue replay.
- Actual local desktop/mobile homepage and authentication screenshots were captured
  and visually inspected under `frontend/output/playwright/ui-migration-*.png`.

The automated integration/route suite uses isolated API fixtures. It proves browser
rendering and tested UI contracts, not live inbox delivery or all production API
behavior. No complete post-redesign live-data sweep or pixel-level approval of every
source frame is claimed. The earlier failed suite (20 passed, 3 failed) was followed
by fixes and the clean final 23-test run; it is not used as final acceptance evidence.

## Earlier local integration verification — 13 October 2026

The following evidence predates the final design-first changes. It demonstrates
earlier functional integration, not acceptance of every newly migrated screen.

The latest development UI runs at `http://localhost:3001`, with the API at
`http://127.0.0.1:8000` and an independent background worker. Port 3000 may
serve an older Docker frontend; it is not the verified latest design.

Executed live checks, without API mocks:

- `backend/scripts/verify_product_local.py`: final AI run **38 checks**, zero failures, including
  local signup/verification/password-plus-OTP authentication, normal-user admin
  denial, project creation, document upload and indexing, widget publication,
  disallowed-origin rejection, a real grounded OpenRouter answer, leads,
  workflows, analytics, usage, team, integrations, logout and refresh rejection.
- `frontend/scripts/verify-local-browser.cjs`: final stable run **17 checks**,
  including persisted project creation, knowledge upload, 13 authenticated primary
  pages, logout and anonymous protected-route rejection. No browser runtime
  exceptions were recorded. An earlier 18-check run also exercised recovery from
  rate limiting. The final sweep is paced to respect real API limits; expected
  normal-user admin-denial responses are recorded separately.
- A final non-AI API sweep passed **36 checks**, including persisted assistant
  knowledge binding and exact-assistant analytics. AI and non-AI reports use
  separate filenames so skipped inference cannot replace live evidence.
- Safe OpenAPI probes: 169 GET/HEAD operations without 5xx responses. Anonymous
  authorization rejection is reachability evidence, not functional acceptance.

These scripts create unique synthetic accounts/workspaces and remove only their
own local test records and uploaded objects. OTPs are read from the local test
cache; these runs do not prove inbox delivery. Test reports and screenshots are
ignored under `backend/output/` and `frontend/output/playwright/live-local/`.
The live AI check uses a separate process pinned to `openrouter/free`, verified
against provider pricing, not the paid model configured in the private `.env`.
An inherited old key initially overrode the updated file; verified processes
were restarted without that stale environment value. No key is included here.

Latest full backend result: **206 passed**, no warnings. The independent worker
was paused during this suite because its legitimate consumption of synthetic
outbox events races with isolated retry assertions, then restarted afterward.
Frontend: **21 browser tests and one SDK test passed**; the changed route
inventory and session-retry tests also passed a focused rerun.
An additional Product 1 overview regression passed, proving failed API sources
show unavailable/retry states rather than fabricated zero counts or empty lists.
The assistant knowledge browser regression also passed: saving explicit empty
selection targets the selected assistant and persists across reload.
ESLint uses `--max-warnings 0`; lint, Prettier and production build passed. Python compilation
and touched-file Ruff checks passed. These results are local execution evidence,
not hosted CI or deployment evidence.

Dedicated Product 1 pages now include the chat overview, document directory and
assistant knowledge bindings. Explicit empty knowledge selection is distinct
from an omitted legacy selection. Assistant editor/behavior links preserve the
assistant and configuration tab; playground links preserve the assistant ID.

Remaining acceptance boundaries: mocked route inventory tests are not real
functionality tests for every control; admin mutation workflows, external OAuth
providers, live email delivery and screenshot-level acceptance require separate
evidence. Cognito is intentionally excluded from this local task. Do not infer
100% migration or production readiness from these results.
