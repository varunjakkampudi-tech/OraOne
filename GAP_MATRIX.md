# GAP_MATRIX — OraOne (Stage A)

Each gap has an ID, the requirement it breaks (source and section), its status, and the action. Status: OPEN (agent can work it on `dev`), BLOCKED (needs owner), READY_FOR_OWNER (owner action with instructions in `blocker.txt`), DONE (verified in `QUALITY_AUDIT.md`). Denominators are stated per group.

## A. Governance and workflow

| ID   | Gap                                                                    | Requirement                   | Status          | Action                                                                    |
| ---- | ---------------------------------------------------------------------- | ----------------------------- | --------------- | ------------------------------------------------------------------------- |
| GV-1 | Owner approval of v2.1 not in repository                               | Standards 2.4; Goal 1.2       | BLOCKED (owner) | `blocker.txt` G1                                                          |
| GV-2 | Hostinger auto-deploy-on-push setting unverified                       | Goal 1 (approval condition 2) | BLOCKED (owner) | `blocker.txt` G2                                                          |
| GV-3 | Repository name in goal (`OraOne`) differs from remote (`oraone-prod`) | Goal header                   | READY_FOR_OWNER | `blocker.txt` G5                                                          |
| GV-4 | Deploy workflow is `deploy.yml`, goal names `deploy-hostinger.yml`     | Goal 16B.1                    | OPEN            | Record the mapping in `PROGRESS.md`. Do not rename without owner approval |
| GV-5 | No `docs/decisions/`, `docs/runbooks/`, `docs/investigations/`         | Goal 16B.8, 18                | OPEN            | Create with README stubs                                                  |
| GV-6 | No `CHANGE_REGISTER.md`                                                | Standard 3.6                  | OPEN            | Create                                                                    |

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

| ID   | Gap                                                                                       | Status | Action                                                                                      |
| ---- | ----------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------- |
| PM-1 | `FEATURE_MATRIX.md`, `APP_SCREEN_MATRIX.md`, `JOURNEY_MATRIX.md`, `TEST_MATRIX.md` absent | OPEN   | Build from the routes, screens and tests in the repo; mark unverified items NOT_ASSESSED    |
| PM-2 | `PROVIDER_PERMISSION_MATRIX.md` absent                                                    | OPEN   | list WhatsApp, Instagram, telephony, Stripe, Cognito with status BLOCKED or READY_FOR_OWNER |
| PM-3 | `MIGRATION_AUDIT.md`, `COST_MODEL.md`, `RISK_REGISTER.md` absent                          | OPEN   | create                                                                                      |
| PM-4 | 25 go/no-go gates (Goal 21) not tracked                                                   | OPEN   | track in `QUALITY_AUDIT.md` with NOT_DUE mapped by release slice                            |

## F. Owner-only items (not agent work)

See `blocker.txt`, "ROUND 10" G1 to G5, and ROUND 9 items 35a to 35d and 19.

## Counts

- Governance rows: 6 (GV-1 to GV-6): BLOCKED 2, READY_FOR_OWNER 1, OPEN 3
- CI rows: 10: DONE 1 (on dev, unexercised), OPEN 7, READY_FOR_OWNER 1, CHECK 1
- Quality rows: 4: DONE 1, OPEN 3
- Security rows: 5: OPEN 4, PARTIAL 1
- Product rows: 4: OPEN 4

Measured numerators and denominators per category are in `QUALITY_AUDIT.md`.
