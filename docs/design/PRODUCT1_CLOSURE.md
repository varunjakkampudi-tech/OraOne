# Product 1 cleanup and verification

Date: 14 October 2026. Starting checkpoint: `ef6ba4d`.

## Single application boundary

`frontend/` is the only application UI; `backend/` supplies the real FastAPI
contracts. No separate Product 1/2 folders, Lovable runtime, Supabase backend or
duplicate UI export was introduced. Products 2–9 remain planned design previews;
Product 10 remains a long-term vision, not an implemented service.

The import-graph pass removed seven unused legacy screens/demo components and
58 further unreachable source modules. It inspected local static imports,
re-exports and literal dynamic imports with the existing ESLint parser. The
remaining 176 source files were reachable from the app entry point, with zero
unresolved local imports and zero unreachable JavaScript candidates. This is
graph evidence, not a claim that every line received independent security review.

Removed files are recoverable from Git history. Active shared loaders, dialogs,
branding, SDK distribution, Google Drive and Calendar integrations remain.
Unused component-generator configuration and dependencies were pruned. Marketing
copy, product metadata and isolated test fixtures are not operational dummy data.

## Defects corrected

- Analytics request failures now show unavailable/retry states instead of zeros.
- Lead pagination uses real loaded-record counts; missing dates are not replaced
  with the current date.
- Inbox supports additional backend batches and record-specific detail retrieval.
  Its client-side search explicitly describes the loaded records it searches.
- Offline quality simulations are not presented as measured agent quality.
- Typed audit snapshots are normalized before JSONB persistence and detached
  from caller mutation. Development tracebacks omit local-variable dumps.
- Application connectors no longer manufacture tokens, documents or folder trees.
  Legacy simulated connections fail closed and require real OAuth reconnection.
- Local storage rejects symlink roots and checks owner/private permissions on
  POSIX; production continues to require configured MinIO/S3-compatible storage.
- Non-security embedding bucket hashes are marked explicitly without changing
  existing vectors. No scanner exclusions were introduced.
- Dashboard loading is exposed as a busy state; live screenshots wait for content.
- Clean-checkout CI exposed wildcard dashboard CORS when no private environment
  existed. Defaults now allow only exact loopback development origins; deployment
  requires explicit origins and wildcard configurations fail closed. Public widget
  CORS remains a separate domain-checked policy. Ten configuration regressions
  cover the boundary. Pytest dotenv loading now preserves process overrides.

## Executed evidence

| Gate | Result | Evidence boundary |
| --- | --- | --- |
| Backend | 218 tests passed | Local PostgreSQL/Redis; independent worker paused to avoid consuming test outbox rows |
| Real Product 1 API | 38 checks, zero failures | Real local auth, persisted resources, widget authorization, grounded free OpenRouter inference, usage and logout |
| Real browser | 22 checks passed | Local OTP cache, real API, persisted project/upload/customer notes, primary screens and assistant detail pages |
| Safe API smoke | 169 routes, no 5xx | Five 200, 160 expected anonymous 401, two 404 and two 422; not authenticated acceptance for every API |
| SDK | 1 test passed | SSR safety and queued-call replay; not an arbitrary third-party-site deployment |
| Frontend quality | ESLint zero warnings, Prettier and production build passed | Final dependency cleanup inputs |
| Import graph | 176 reachable files, zero unresolved imports | Static module graph, not dynamic runtime acceptance |
| Dependencies | npm runtime audit and installed Python audit found no known advisories | Scanned package versions only; not a zero-vulnerability guarantee |
| Bandit | No high-severity/high-confidence findings | 21 low and one medium raw finding retained for context review |
| Docs | Anchor tests and ten Mermaid syntax parses passed | Source/embed parity and links are validated separately |
| Workflow configuration | Three YAML files and 31 Bash blocks parsed | Manual deployment is dispatch-only/main-gated; syntax is not hosted execution |

The initial backend baseline had one competing-worker test failure. Its exact
outbox recheck passed after pausing that worker, and the final 218-test suite
passed. Initial live project creation failed while malformed audit snapshots
accumulated; normalization, regression and a fresh API process preceded the clean
live runs. A first dashboard screenshot was still loading and was superseded by
a content-ready capture. These failures are not counted as passing evidence.

The browser fixture suite separately covers auth navigation, unavailable data,
Product 1 screens, administrator routes, mobile layout and all 283 reference
destinations. Consult the current GitHub run for the final consumed SHA; historical
26-test results must not be treated as live inbox or production acceptance.

After dependency pruning, the local fixture sweep passed 25 tests and timed out in
one multi-destination navigation test. Its wildcard mock had shadowed auth/identity
responses. Correct contract fixtures, a session-ready assertion and a bounded
90-second budget for fourteen destinations preceded a passing focused recheck.
The hosted full suite remains the final exact-commit gate; this is not relabeled
as a single clean local full-suite run.

The first hosted application run at `00d24e9` passed frontend build/browser checks,
API smoke and frontend security headers, but backend tests reported 217 passed and
one CORS rejection failure. That failure was retained and corrected, not waived.
The configuration fix passed thirteen focused CORS tests, including the original
negative security test, before being published for fresh hosted validation.

## Repository and deployment controls

Quality CI rejects uncommitted autofixes using repository-root pathspecs. Backend
CI migrates an isolated PostgreSQL/pgvector test database rather than silently
skipping database tests; SDK tests are part of application checks. Manual Hostinger
deployment checks out and tags the same dispatch SHA. No deployment was dispatched
by this cleanup. GitHub description, homepage/topics and private vulnerability
reporting were configured and verified; visibility and licensing were not changed.

## Remaining acceptance boundaries

No claim is made of 100-percent line coverage, pixel parity with every reference
frame, every-button live acceptance, full secret-history review, penetration testing
or zero security vulnerabilities. Bandit's medium observation is the stable local
development upload directory; production local fallback is forbidden and the root
now has owner/symlink/permission checks. Low observations include type-narrowing
assertions, protocol strings mistaken for passwords and optional-service recovery.
They remain visible rather than being suppressed for a clean score.

Cognito/live inbox delivery are intentionally deferred. Third-party OAuth requires
configured owner credentials/consent; privileged live administrator mutations were
not performed by promoting a real identity. Production hosting, egress validation,
backups and recovery are separate authorization gates. PostgreSQL RLS is not claimed.
No payment integration is required for the current free-access product. Owner legal
ownership/widget licensing and visual approval remain owner decisions.

## Local review

Final hosted verification at `b928349` passed both workflows: 228 backend tests
and 26 browser tests. The final marketing pass removes fictional testimonials,
unused outcome metrics and unsupported certification/uptime claims. Private
reporting links to the verified GitHub vulnerability reporting channel.

The repeat real-browser run uncovered a public-widget CORS prefix collision with
authenticated `/api/widgets` management. The public exception now matches only
`/api/widget` and its children. Regression tests verify credentialed dashboard
preflight, rejection of unauthorized management origins and cookie-free public
widget preflight. The real-browser verifier rejects network `ERR_FAILED` events.

Latest UI: `http://localhost:3001/`; API: `http://127.0.0.1:8000/`.
Port 3000 can serve an older Docker frontend and is not the authoritative preview.
PostgreSQL/pgvector, Redis and MinIO are supplied by development Compose. Alembic
was at `0050_webhook_delivery_identity`. Private environments and generated test
reports remain ignored. Scripts clean only their synthetic workspaces, never all
user data. See the [quickstart](../guides/QUICKSTART.md) for first-clone setup.
