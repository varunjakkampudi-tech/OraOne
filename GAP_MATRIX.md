# GAP_MATRIX — OraOne (Stage A)

Each gap has an ID, the requirement it breaks (source and section), its status, and the action. Status: OPEN (agent can work it on `dev`), BLOCKED (needs owner), READY_FOR_OWNER (owner action with instructions in `blocker.txt`), DONE (verified in `QUALITY_AUDIT.md`). Denominators are stated per group.

## A. Governance and workflow

| ID   | Gap                                                                         | Requirement                   | Status          | Action                                                                    |
| ---- | --------------------------------------------------------------------------- | ----------------------------- | --------------- | ------------------------------------------------------------------------- |
| GV-1 | Owner approval of v2.1 not in repository                                    | Standards 2.4; Goal 1.2       | BLOCKED (owner) | `blocker.txt` G1                                                          |
| GV-2 | Hostinger auto-deploy-on-push setting unverified                            | Goal 1 (approval condition 2) | BLOCKED (owner) | `blocker.txt` G2                                                          |
| GV-3 | Goal names a repository that differs from the remote (name withheld, CR-02) | Goal header                   | READY_FOR_OWNER | `blocker.txt` G5                                                          |
| GV-4 | Deploy workflow is `deploy.yml`, goal names `deploy-hostinger.yml`          | Goal 16B.1                    | OPEN            | Record the mapping in `PROGRESS.md`. Do not rename without owner approval |
| GV-5 | No `docs/decisions/`, `docs/runbooks/`, `docs/investigations/`              | Goal 16B.8, 18                | OPEN            | Create with README stubs                                                  |
| GV-6 | No `CHANGE_REGISTER.md`                                                     | Standard 3.6                  | OPEN            | Create                                                                    |

## B. CI/CD (Standard 27; Goal 16B)

Denominator: 16B.2 trigger matrix has 8 rows.

| ID    | Gap                                                                          | Status                                                | Action                                                                           |
| ----- | ---------------------------------------------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------- |
| CI-1  | Push trigger: `main` only                                                    | DONE on `dev` (ci.yml now `[main, dev]`, not yet run) | verify with a real `dev` push                                                    |
| CI-2  | No nightly schedule                                                          | OPEN                                                  | add `schedule` to a new workflow that runs the existing commands                 |
| CI-3  | No `workflow_dispatch` test workflow with suite selection                    | OPEN                                                  | add with allowlisted commands only; never production                             |
| CI-4  | No dependency audit (`bun audit`, `pip-audit`)                               | OPEN                                                  | add to CI on `dev`; list findings in QUALITY_AUDIT                               |
| CI-5  | No secret scan (gitleaks)                                                    | OPEN                                                  | add; the goal allows CI-only scanners                                            |
| CI-6  | No coverage measurement or threshold                                         | OPEN                                                  | measure first, then set thresholds from the baseline. Do not lower any threshold |
| CI-7  | Actions pinned by tag, not commit SHA: 0 of 15 `uses:` lines                 | OPEN                                                  | pin with SHAs taken from the upstream repositories                               |
| CI-8  | `fix-formatting.yml` opens pull requests (`peter-evans/create-pull-request`) | READY_FOR_OWNER                                       | goal says no agent-created PRs; owner decides whether to keep it                 |
| CI-9  | Playwright not run on tablet (768/1024) or 320 widths                        | OPEN                                                  | add projects; prove with a real run                                              |
| CI-10 | No Alembic parity job on a disposable DB in CI for `dev`                     | CHECK                                                 | `backend` job runs `alembic upgrade head`; confirm it covers downgrade           |

Least-privilege permissions: 3 of 3 workflow files declare `permissions:` (DONE).

## C. Quality and static analysis (Standard 7)

| ID   | Gap                                                                        | Status                                      | Action                                             |
| ---- | -------------------------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------- |
| QA-1 | Prettier failed on 8 files                                                 | DONE (archive excluded, PROGRESS formatted) |                                                    |
| QA-2 | No knip (unused exports), jscpd (duplication), dependency-cruiser (cycles) | OPEN                                        | run on baseline, record counts, fix or disposition |
| QA-3 | No mypy or complexity limit on backend                                     | OPEN                                        | measure first                                      |
| QA-4 | Existing findings not yet inventoried (Standard 7.4)                       | OPEN                                        | inventory and disposition                          |

## D. Product and security (Standard 22; Spec v2.1 section 9)

| ID    | Gap                                                 | Status                | Action                                                      |
| ----- | --------------------------------------------------- | --------------------- | ----------------------------------------------------------- |
| SEC-1 | No dependency or secret scan in CI                  | OPEN (see CI-4, CI-5) |                                                             |
| SEC-2 | No SBOM, license policy, provenance                 | OPEN                  | generate SBOM (CycloneDX) in CI                             |
| SEC-3 | No threat model (`docs/security/THREAT_MODEL.md`)   | OPEN                  | write from code review of auth, tenancy, widget, webhooks   |
| SEC-4 | No `RISK_EXCEPTIONS.md`                             | OPEN                  | agents cannot approve exceptions; create the empty register |
| SEC-5 | Cross-tenant and webhook tests exist (prior rounds) | PARTIAL               | re-run in CI and record                                     |

## E. Product and matrices (Spec v2.1 sections 5, 9, 12; Goal sections 5, 9)

| ID   | Gap                                                                                       | Status | Action                                                                                   |
| ---- | ----------------------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| PM-1 | `FEATURE_MATRIX.md`, `APP_SCREEN_MATRIX.md`, `JOURNEY_MATRIX.md`, `TEST_MATRIX.md` absent | OPEN   | Build from the routes, screens and tests in the repo; mark unverified items NOT_ASSESSED |
| PM-2 | `PROVIDER_PERMISSION_MATRIX.md` absent                                                    | OPEN   | list WhatsApp, Instagram, telephony, Stripe with status BLOCKED or READY_FOR_OWNER       |
| PM-3 | `MIGRATION_AUDIT.md`, `COST_MODEL.md`, `RISK_REGISTER.md` absent                          | OPEN   | create                                                                                   |
| PM-4 | 25 go/no-go gates (Goal 21) not tracked                                                   | OPEN   | track in `QUALITY_AUDIT.md` with NOT_DUE mapped by release slice                         |

## F. Owner-only items (not agent work)

See `blocker.txt`, "ROUND 10" G1 to G5, and ROUND 9 items 35a to 35d and 19.

## Counts

- Governance rows: 6 (GV-1 to GV-6): BLOCKED 2, READY_FOR_OWNER 1, OPEN 3
- CI rows: 10: DONE 1 (on dev, unexercised), OPEN 7, READY_FOR_OWNER 1, CHECK 1
- Quality rows: 4: DONE 1, OPEN 3
- Security rows: 5: OPEN 4, PARTIAL 1
- Product rows: 4: OPEN 4

Measured numerators and denominators per category are in `QUALITY_AUDIT.md`.

## G. Workflow audit findings (read-only agent audit, 20 October 2026)

Measured: 3 workflow files, 6 jobs, 15 `uses:` lines, 0 pinned to a commit SHA, 3 top-level `permissions:` blocks. Triggers: ci.yml on pull_request and push to main/dev; deploy.yml and fix-formatting.yml workflow_dispatch only. No workflow deploys on push.

| ID    | Finding                                                                                                                                | Severity | Status          | Action                                                                                                          |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------- | --------------------------------------------------------------------------------------------------------------- |
| WF-1  | deploy.yml has no `needs:` on CI; a manual dispatch from main deploys HEAD whatever its CI state                                       | Medium   | READY_FOR_OWNER | Owner decides whether to require a passing CI run before deploy; branch protection cannot be read from the repo |
| WF-2  | deploy.yml host key comes from ssh-keyscan on each run (trust on first use)                                                            | Low      | OPEN            | Pin the production host key as a secret                                                                         |
| WF-3  | fix-formatting.yml gives `contents: write` and `pull-requests: write` to the whole job, including dependency install scripts           | Medium   | OPEN            | Split into a read-only job and a write job                                                                      |
| WF-4  | fix-formatting.yml checkout persists the token in .git/config                                                                          | Low      | OPEN            | Set persist-credentials: false                                                                                  |
| WF-5  | fix-formatting.yml opens pull requests (peter-evans/create-pull-request)                                                               | Info     | READY_FOR_OWNER | Owner decides whether to keep it (see CI-8)                                                                     |
| WF-6  | fix-formatting.yml swallows failures (`                                                                                                |          | true`)          | Low                                                                                                             | OPEN | Remove the ` |     | true` |
| WF-7  | ruff unpinned in fix-formatting.yml; backend/requirements-dev.txt pins `ruff>=0.17,<1.0`                                               | Low      | OPEN            | Install from requirements-dev.txt                                                                               |
| WF-8  | fix-formatting.yml has no timeout or concurrency                                                                                       | Low      | OPEN            | Add both                                                                                                        |
| WF-9  | All 15 action references use mutable tags, none pinned to SHA                                                                          | Medium   | OPEN            | Pin to commit SHAs (CI-7)                                                                                       |
| WF-10 | production-images job boots with ENVIRONMENT=development; backend/app/core/config.py treats production, prod and staging as production | Medium   | OPEN            | Boot with ENVIRONMENT=production and test-only secrets                                                          |
| WF-11 | No dependency audit, secret scan, coverage, nightly schedule or manual test workflow                                                   | Medium   | OPEN            | See CI-2 to CI-6                                                                                                |

Checked and compliant: least-privilege top-level permissions in ci.yml and deploy.yml; deploy job guarded by `refs/heads/main`; every package.json script the workflows call exists; Playwright projects 390 and 1280 exist; scripts/deploy-remote.sh has deploy and rollback modes.

## H. Frontend accessibility and responsive findings (static read-only audit, 20 October 2026)

Static review only; no browser run. Checks: onClick on non-interactive elements, img alt, input labels, icon-only buttons, fixed widths, reduced-motion handling.

| ID     | Finding                                                                                                      | Severity        | Status | Action                      |
| ------ | ------------------------------------------------------------------------------------------------------------ | --------------- | ------ | --------------------------- |
| A11Y-1 | Disabled chat composer input has only a placeholder, no label (src/components/oraone/pages.tsx:634)          | Low             | OPEN   | Add aria-label              |
| A11Y-2 | Same defect, second input (src/components/oraone/pages.tsx:753)                                              | Low             | OPEN   | Add aria-label              |
| A11Y-3 | Icon-only link button relies on title only (src/components/oraone/pages.tsx:490)                             | Low-Medium      | OPEN   | Add aria-label              |
| A11Y-4 | Three icon-only link buttons rely on title only (src/components/oraone/dashboard.tsx:465, 480, 493)          | Low             | OPEN   | Add aria-label              |
| A11Y-5 | .workspace-menu has fixed width 265px with no max-width guard (src/styles.css:1298)                          | Low (suspected) | OPEN   | Check at 390px in a browser |
| A11Y-6 | Shared image component depends on every caller passing non-empty alt (src/components/site/templates.tsx:196) | Low (suspected) | OPEN   | Check callers               |

Measured counts: 158 onClick occurrences in 30 files, none on non-interactive tags; 4 img tags, all with alt; 104 input-like elements in 25 files, about 25 call sites read; 18 icon-size buttons in 6 files; 3 reduced-motion blocks found.
Not verified: unread studio and templates form controls; visual overflow and focus at 390px (needs a browser run).

## I. Backend tenancy and authorization findings (read-only audit, 20 October 2026)

Measured: 30 of 356 route decorators read (about 8%). 23 read by handler body, 7 checked by dependencies. The remaining 326 are NOT verified. The file-level sweep is a signal only.

| ID      | Finding                                                                                                                                                                    | Severity | Verified  | Status              | Action                                                                                                         |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------- | ------------------- | -------------------------------------------------------------------------------------------------------------- |
| SEC-T1  | Telegram bot token stored as plaintext configuration["bot_token"] (src/api/omnichannel/routes.py:94); binding_secrets encrypts only sdk_secret and telegram_webhook_secret | HIGH     | VERIFIED  | OPEN, priority 1    | Encrypt bot_token like the other binding secrets; add a regression test that the stored value is not plaintext |
| SEC-T2  | Bot token in URL path (src/api/omnichannel/routes.py:216), so it reaches access logs; redaction in middleware/access_log.py not yet read                                   | MEDIUM   | SUSPECTED | OPEN                | Move token out of the path; confirm redaction                                                                  |
| SEC-T3  | Email inbound uses one deployment-wide header secret, not per binding (src/api/omnichannel/routes.py:128)                                                                  | MEDIUM   | VERIFIED  | OPEN                | Per-binding secret                                                                                             |
| SEC-T4  | Unauthenticated callers can tell "no agent bound" (200) from "bad secret" (401) (src/api/omnichannel/routes.py:187-193)                                                    | LOW      | VERIFIED  | OPEN                | Return the same response for both                                                                              |
| SEC-T5  | widget_event called with require_published=False (src/api/widgets/public.py:957-969); rate limit is per IP only                                                            | LOW      | VERIFIED  | OPEN                | Require published key                                                                                          |
| SEC-T6  | OAuth exchange logs exception text (src/api/integrations/routes.py:523); ConnectorError content not read                                                                   | LOW      | SUSPECTED | OPEN                | Check ConnectorError; log without upstream body                                                                |
| SEC-T7  | uuid.UUID(org_id) unguarded on Stripe metadata (src/services/billing_service.py:516)                                                                                       | LOW      | VERIFIED  | OPEN                | Guard and return a clean error                                                                                 |
| SEC-T8  | Dev-only login logs auth_subject (src/services/auth_service.py:244), gated to development plus flag                                                                        | INFO     | VERIFIED  | Accepted, no change |                                                                                                                |
| SEC-T9  | Routes with low tenant-reference density (chat, websites, knowledge, integrations, widgets) need a per-query check                                                         | MEDIUM   | SUSPECTED | OPEN                | Full per-route audit, then tests                                                                               |
| SEC-T10 | Usage routes use only get_current_organization with no permission dependency visible                                                                                       | LOW      | SUSPECTED | OPEN                | Confirm intended read permission                                                                               |

Checked and sound (VERIFIED): public API ownership helpers (_scoped, _owns); RAG chunk filter by organization_id; escalations and inbox scoped by org and project; chat thread access user-scoped; Twilio, Meta, SDK and Telegram signatures fail closed; Stripe signature and event-id replay protection; inbound dedupe on provider message id; constant-time OTP comparison with attempt limits; no secret logging found by grep.

Recommended order: SEC-T1 first (it is the only HIGH), then SEC-T2 and SEC-T3, then the per-route audit of the other 326 routes (SEC-T9).

## J. Amendment CR-02 (no AWS, no repository names or links) — status, 20 October 2026

| ID    | Requirement                               | Measured status                                                                                                                                                                                                                                                                                 | Action                     |
| ----- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| CR2-1 | No AWS runtime code, SDK or dependency    | DONE for code: tracked source checked for boto, aws, cognito, s3, ses, sns, cloudfront, rds; no SDK or dependency found. Remaining hits are comments (reworded), detection patterns for leaked AWS keys in the security scanner (kept on purpose), and alembic migration history (never edited) | none                       |
| CR2-2 | Cognito removed                           | DONE: migration 20261016_0051 removed Cognito identity columns; sign-in is application-managed; no SMS sign-in path exists                                                                                                                                                                      | D21 decision (blocker R11) |
| CR2-3 | No repository names or links in documents | PARTIAL: removed from SECURITY.md, PROGRESS.md, GAP_MATRIX.md, blocker.txt. Still present in archived source documents (blocker R9) and in earlier commit messages (blocker R10)                                                                                                                | blocker R9, R10            |
| CR2-4 | Container names                           | OPEN: docker-compose files use the repository slug as a prefix (blocker R12)                                                                                                                                                                                                                    | owner decision             |
| CR2-5 | Object storage S3-compatible, non-AWS     | Recorded: docs/architecture/SYSTEM-OVERVIEW.md states an S3-compatible service is optional; local disk is the development fallback                                                                                                                                                              | none                       |

Counts: tracked files searched 1,064 (including binaries). AWS-specific matches in tracked source after the reword: 0 runtime, 2 detection patterns, 1 migration comment.
