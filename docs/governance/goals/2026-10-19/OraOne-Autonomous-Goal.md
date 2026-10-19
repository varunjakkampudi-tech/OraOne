# OraOne — Autonomous Build and Validation Goal (Phase L0, with L1 Preparation)

**Project:** OraOne (oraone.in)
**Company:** Viswatra (intended)
**Execution mode:** Autonomous development and testing (development branch only; `main`, production deployment, and production configuration are owner-only)
**Product specification:** OraOne-Product-Spec-v1.1.md (PROPOSED until the owner approves it)
**Engineering baseline:** OraOne-Engineering-Standards.md
**Repository:** `varunjakkampudi-tech/OraOne`, baseline `main` at `10a6fdd0f9cc8c97d40327d4266933e6c463a723` (re-verify at start)
**Objective:** Complete Phase L0 — foundation audit and Product 1 hardening — with independently verifiable evidence; prepare Phase L1 designs and contracts without activating them; document every owner and external blocker; prepare the owner's L0 exit and L1 start decisions. Do not make them.

---

## 0. Prerequisites (check before starting)

- Repository access: git can fetch and push to the designated development branch. Record remote and branch names
- Local runtime: Python and Node versions used by the repository's CI, Docker for PostgreSQL (pgvector), Redis, and MinIO
- Test-only configuration: a non-production Cognito user pool (or the repository's local test-auth path, where it is blocked in production), Stripe test mode keys, and mocked AI providers. Variable names (never values) recorded in `blocker.txt` if missing
- Paid AI provider APIs are not called by automated tests; use mocks. Any real-provider evaluation run needs an owner-set spend cap first
- GitHub Actions enabled, with enough minutes for the trigger matrix (section 16B.7)
- A separate staging host and its GitHub environment secrets, provided by the owner, for staging deployment (section 16B.4). Without them, staging deployment is blocked and validation runs in ephemeral CI environments

---

## 1. Authoritative references and precedence

Read in order before modifying code:
1. `OraOne-Product-Spec-v1.1.md`: product identity, portfolio status, Lead OS features and phases, journeys J01 to J12, screen inventory, data and provenance contract, AI behaviour contract, privacy and anti-abuse rules, security and reliability requirements, the 25 go/no-go gates, roles, and open decisions D01 to D18
2. `OraOne-Engineering-Standards.md`: stack, code quality, UX, backend, data, AI, security, testing, definition of done
3. The repository: code, tests, migrations, configuration, CI, documentation, and history

Precedence:
1. The spec's truth rule, AI behaviour contract (section 7), and privacy, consent, and anti-abuse rules (section 8)
2. The portfolio status in spec section 1.1 (no planned product shown or built as live)
3. Other spec requirements
4. This goal file for workflow and execution behaviour
5. Engineering Standards, except where explicitly overridden here
6. Existing code

### 1.1 Unapproved decisions

The spec is PROPOSED and decisions D01 to D18 are open. Never treat them as approved and never record an assumption as a decision.
- Precedence items 1 and 2 always apply as constraints
- Implement only work that is independent of open decisions, reversible, and compliant with those constraints
- When a decision is needed, record it in `blocker.txt` as READY_FOR_OWNER with the decision, recommended option, alternatives, risks, and the exact owner action. Continue unrelated work

### 1.2 Current authorization

- **Authorized now:** Phase L0 (spec section 11): baseline inventory, reproducible CI, migration and model parity, secured tenant flows, Product 1 production-blocker fixes, accessibility and responsive fixes, security hardening, restore evidence on disposable infrastructure, and the matrices in section 5
- **Preparation only:** Phase L1 designs, data-model proposals, API contracts, screen-matrix entries, and test plans, written as documents and disabled scaffolding behind flags. No L1 feature is activated or marked implemented
- **Not authorized:** L1 implementation (until the owner approves the spec and decisions D01, D03, D05, D06, D16, and D17), L2, L3, and portfolio products P2 to P10

Spec urgency rule: L0 production blockers come before any L1 work.

### 1.3 Evidence levels

Every result is labelled with exactly one level: OBSERVED_CODE, TESTED_LOCAL (local or CI ephemeral environment), TESTED_STAGING, VERIFIED_EXTERNAL (real provider or third party), or PRODUCTION (owner-run only). A lower level never satisfies a gate that needs a higher one. Staging results are never presented as production results.

---

## 2. Primary mission

In priority order:
1. **Baseline:** a SHA-pinned inventory and functional test run classifying every spec requirement as OBSERVED_CODE, TESTED_LOCAL, VERIFIED_EXTERNAL, BLOCKED, PLANNED, GATED, or RETIRED (spec section 1)
2. **L0 production blockers:** fix migration and model drift, tenancy and authorization gaps, failing or missing tests, CI gaps, and security findings in existing Product 1 functionality
3. **L0 quality:** accessibility, responsive, cross-browser, and AI answer-quality evidence for existing Product 1 flows
4. **L0 operations:** outbox, webhook, quota, kill-switch, and restore evidence on disposable infrastructure
5. **L1 preparation:** designs, contracts, and test plans for the L1 Lead OS core
6. **Reports:** the L0 exit report and the L1 readiness proposal for the owner

Complete all safe work autonomously. Stop an individual task only for a genuine blocker (section 20). Never mark a requirement complete without evidence. Do not add features beyond the spec.

---

## 3. Autonomous authority

You may decide independently: implementation order, internal APIs and module boundaries, algorithms, refactoring of genuine problems, test strategy, UI implementation details within the spec and approved identity, security hardening consistent with the spec, observability, CI configuration, and documentation structure.

When uncertain: check the spec, inspect the code, compare viable approaches, prefer proven, secure, maintainable, low-cost options, preserve working behaviour and historical migrations, choose the smallest complete solution, record material decisions in `docs/decisions/`, and continue.

Never invent consent, provider permissions, credentials, customers, prices, metrics, legal approval, or test results. Do not reset the repository to a new template.

---

## 4. Git workflow — autonomous, no PRs

1. Verify repository status and the baseline commit
2. Preserve history and uncommitted owner work
3. Create and verify a baseline backup (section 4.1)
4. Use a designated development integration branch
5. Use short-lived task branches or worktrees where helpful
6. Implement one coherent requirement at a time
7. Run the definition of done, using the mapping in section 4.2
8. Review independently (section 16)
9. Commit only validated changes
10. Integrate sequentially into the development branch
11. Revalidate the integrated baseline after each material integration
12. Remove only temporary branches confirmed safe to delete

Never push to or merge into `main`; promotion is owner-only. Never dispatch `deploy-hostinger.yml` or any job that uses the `production` environment. Never force-push protected branches or rewrite published history. Do not bypass branch protection. When the development branch is ready for promotion, record it in `blocker.txt` as READY_FOR_OWNER with branch, commit SHA, and validation results.

### 4.1 Verified baseline backup

Before any major modification (anything beyond reading, auditing, and creating the evidence files in section 18):
1. Record `git rev-parse HEAD`, the current branch, `git status --porcelain`, `git branch -a`, and `git tag`
2. If uncommitted or untracked owner changes exist, do not stash, reset, check out over, clean, or commit them. Work in a separate worktree from the baseline SHA. Archive a copy of the uncommitted files outside the repository, excluding secret files (`.env*`, key, certificate, and credential files); list excluded files by name only
3. Create a full bundle outside the repository: `git bundle create <backup-dir>/oraone-baseline-<SHA>.bundle --all`
4. Verify with `git bundle verify` and record a SHA-256 checksum
5. Clone the bundle into a temporary directory; confirm the baseline SHA, branches, and tags match; run `git fsck`; delete the temporary copy
6. Record every command, exit code, checksum, path, and result in `PROGRESS.md`
7. If any step fails, make no major modifications; record a blocker and continue read-only audit work

### 4.2 Engineering Standards in autonomous mode

| Standards wording | Autonomous-mode equivalent |
|---|---|
| "Every integration" or "every pull request" | Every integration into the development branch, run on the task branch before and on the integrated baseline after |
| "Every commit" | Every commit |
| "Nightly" | The scheduled nightly run (section 16B.2), every checkpoint (section 19), and before any promotion request |
| "Every staging deployment" or "before promotion" | Authorized staging deployments (section 16B.4) and release-candidate validation before the promotion request. Production deployment stays owner-only |
| "A reason in the change record" | The commit message and the item's `PROGRESS.md` entry |
| Pull request template fields | The item's integration record in `PROGRESS.md`: linked spec requirement, test evidence, screenshots, migration notes, rollback plan, review result |
| "One human approval" | Independent review session (section 16); owner review before promotion for the sensitive areas in Standards section 6 |
| Owner-only decisions (Standards section 10) | Not available to the agent. Record as READY_FOR_OWNER in `blocker.txt` |

No check is dropped and no threshold is reduced.

---

## 5. Mandatory baseline audit and matrices

Before implementing, inspect: repository structure, routes and screens, API routers, services, repositories, middleware (auth, org, project, platform context, rate limits), models and all migrations, workers and outbox, providers and connectors, RAG and knowledge ingestion, widget SDK and loader, billing and entitlements, feature flags, environment variables, tests, CI and deployment workflows, documentation, and the release checklist and integration review items named in spec section 1.

Produce before implementation:
- `GAP_MATRIX.md`: every spec requirement with section, phase (L0 to L3, P2 to P10), status, evidence level, implementation path, tests, dependency, severity, commit SHA, blocker ID
- `FEATURE_MATRIX.md`: every spec feature and differentiator with phase and status
- `APP_SCREEN_MATRIX.md`: every active and planned route and screen (spec section 5 groups: public marketing, identity and onboarding, daily operator workspace, management, platform admin, future gated), with UI states, actor role, permissions, API, phase, and tests
- `JOURNEY_MATRIX.md`: journeys J01 to J12 with phase, required cases (positive, negative, authorization, accessibility, mobile, cross-browser, failure, recovery), and status

Classify by evidence, not by earlier claims. Earlier test counts and the October 15 consolidation are history, not proof.

---

## 6. Status vocabulary

- **Specified:** in the spec, not implemented
- **OBSERVED_CODE:** code exists; behaviour not verified
- **Implemented:** code exists and passes its own tests
- **Tested:** acceptance cases pass at the stated evidence level
- **Integrated:** validated on the development branch
- **Blocked:** owner action, external dependency, or open decision
- **READY_FOR_OWNER:** work and procedure ready; owner must act or decide
- **NOT_DUE:** belongs to a phase not yet authorized (L1 implementation, L2, L3, P2 to P10)
- **Gated / Planned / Retired:** as defined in spec section 1

Never count NOT_DUE items as completed, failed, blocked, or ready. Track all 25 go/no-go gates separately.

---

## 7. Execution order (guidance)

- **Stage A — Foundations:** baseline backup, inventory, matrices, CI triggers for the development branch, coverage measurement, dependency and secret scanning
- **Stage B — Data integrity:** Alembic model and migration parity, upgrade and downgrade on disposable databases, drift fixes (spec gate 13); verify the spec section 1.2 repository facts on the current SHA; apply rules R1 to R6 where they need no open decision (for example, showing an unscored lead's temperature as "unknown" in the UI and API responses, and keeping planned-product routes disabled), and record the rest as READY_FOR_OWNER
- **Stage C — Tenancy and auth:** Cognito flows with a test pool, refresh, recovery, logout, privileged MFA where configured; org and project isolation on every path (spec gates 3, 4, 5)
- **Stage D — Product 1 core:** widget, RAG with citations, prompt-injection resistance, visitor capture to project-scoped lead with source, consent, status, and task, idempotent replay (spec gates 6, 7)
- **Stage E — Handoff and inbox foundations that already exist:** no duplicate sends, no dropped messages, no false "human responded" (spec gate 8), with outbound messaging disabled
- **Stage F — Privacy:** opt-out and deletion propagation, suppression before routing (spec gate 9)
- **Stage G — Cost and integrations:** durable AI cost reservations across workers (gate 11); webhook and outbox success, retries, restarts, signatures, dead letters with mocks (gate 12)
- **Stage H — Billing:** Stripe test-mode lifecycle and entitlement checks (gate 14); no live billing
- **Stage I — Quality:** accessibility (gate 15), responsive and cross-browser (gate 16), security scans and abuse tests (gate 17), public-page truth audit (gates 1 and 21)
- **Stage J — Operations:** alerts, logs, audit, kill switches, backup and restore drills on disposable infrastructure (gate 20); measured performance baselines (gate 19)
- **Stage K — L1 preparation:** Opportunity Thread data-model proposal, the status mapping and additive migration plan in spec section 6.1 (D03), the VisitorProfile and Contact options (D17), the temperature proposal (D16), the metric dictionary implementation plan (spec section 3.7.1), RBAC matrix extensions, API contracts, screen and journey entries, test plans. Documents and disabled scaffolding only
- **Stage L — Reports:** L0 exit report and L1 readiness proposal

Reorder when the audit shows a better sequence, but L0 blockers always come before Stage K.

---

## 8. Scope

In scope: everything in section 1.2 "Authorized now", and Stage K preparation.

Out of scope:
- L1 implementation or activation before owner approval; L2, L3; portfolio products P2 to P10
- Any outbound channel (email campaigns, SMS, WhatsApp, voice, social) or calendar or CRM connector activation
- Live billing, real prices on public pages, or plan launches
- Contact enrichment, scraping, fingerprinting, or cross-tenant matching
- Production deployment or configuration changes
- Pilot recruitment or customer contact

---

## 9. Environment isolation and safety limits

All development and destructive testing use local, CI, or disposable staging resources.

Do not:
- Push to `main`, dispatch the production deploy workflow, or use the `production` environment
- Modify production infrastructure, configuration, DNS, Cognito pools, Stripe live settings, or provider accounts
- Use production databases, Redis, or storage for any test; use real customer or tenant data in fixtures or reports
- Send email, messages, or notifications to real people
- Create third-party accounts or accept provider terms
- Call paid providers without an owner-set cap; use production keys anywhere
- Store or print secrets, tokens, OTPs, prompts with personal data, or contact details
- Lower thresholds, conceal failing tests, fabricate results, or show planned products as live
- Run fault injection, restore drills, or load tests on the production Hostinger host or any shared environment

Use synthetic tenants, contacts, and conversations and mocked providers.

---

## 10. Engineering standards

Apply OraOne-Engineering-Standards.md in full. Preserve the observed stack (Standards section 1.1). The proposed tool additions (Standards section 1.2) are adopted only after owner approval; until then, record them as READY_FOR_OWNER. The exception is measurement and scanning tools that run only in CI and change no product code (coverage, dependency audit, secret scan); these may be added to CI on the development branch and listed in the promotion entry for owner review.

---

## 11. Testing and definition of done

Apply Standards section 7.4 without weakening it. Coverage: 80 percent lines and 70 percent branches on changed backend code; denial and failure tests for every authorization, tenancy, consent, cost-cap, and outbound path. Record exact commands, exit codes, test names, coverage, commit SHAs, and CI run IDs.

---

## 12. Security and abuse testing

Prioritise: OTP and login abuse and enumeration; session fixation, refresh, and revocation; cross-organization and cross-project isolation on read, write, export, search, merge, websocket, widget, and admin paths; role escalation; platform-admin separation; webhook signatures and replay; CSRF, XSS, SQL injection, SSRF (crawlers, connectors, knowledge ingestion); upload parsing and malware controls; prompt injection that tries to trigger privileged actions or cross-tenant reads; sensitive data exposure in logs and exports; secrets and dependency vulnerabilities; audit logging integrity; OWASP Top 10, API Security Top 10, and LLM Top 10.

When a serious defect is found: record it without secrets, classify severity, keep reproducible evidence, block readiness of the affected function, fix where safe, retest, and record unresolved defects in `blocker.txt`. Do not integrate work that depends on an unresolved critical vulnerability.

---

## 13. UI/UX and accessibility

Every core screen meets Standards section 3: all states, breakpoints from 320 to 1440 px, keyboard and screen reader, zoom and reflow, reduced motion, high contrast, three browser engines, honest labelling of planned products, no fabricated content. Use real rendered screenshots as evidence; never present mockups as completed functionality. Do not redesign approved flows for preference alone.

---

## 14. Integrations, AI, and data permissions

- Only the website widget channel is active. Other channels stay disabled and are tested only at their abstraction boundary with mocks
- Knowledge crawling only for authorized domains and content, honouring robots and terms, with SSRF defences and quotas
- AI features follow spec section 7 and Standards section 4.4. Evaluation sets gate any change to prompts, retrieval, or models
- Never report mocked provider behaviour as VERIFIED_EXTERNAL

---

## 15. Failure handling and resilience

Test on disposable infrastructure: PostgreSQL, Redis, provider, and worker interruption; queue retries and dead letters; duplicate delivery; webhook replay; recovery and reconciliation (spec journey J10). Verify behaviour after recovery, not just the failure screen. Do not invent backup or recovery-time measurements.

---

## 16. Independent review

Every material change gets a review in a separate agent session that sees only the requirements, the diff, the surrounding code, and the test results. A review by the session that wrote the code does not count.

If an independent review cannot run: never claim it occurred; record the limitation, commit SHAs, and follow-up in `blocker.txt`; the change may be integrated only if all checks pass and is labelled "independent review pending"; sensitive areas (Standards section 6) stay on their task branch until reviewed; unreviewed changes cannot be marked ready or promoted.

The review covers: requirement completeness, correctness, architecture fit, API and data contracts, tenancy and authorization, privacy and consent, AI contract, migration safety, concurrency and idempotency, error and recovery handling, accessibility, test quality, regression risk, operational impact, and documentation.

### 16A. Comprehensive quality audit, fix, and retest

- **16A.1 Accessibility:** automated axe plus recorded manual keyboard and screen-reader tests on website, widget, and workspace; WCAG 2.2 A and AA violations in active flows fixed. Automated scans alone are not evidence
- **16A.2 Responsive:** every active screen at the Standards section 3 breakpoints; clipping, overflow, overlap, and inaccessible controls fixed. Screenshots alone are not functional evidence
- **16A.3 Cross-browser:** Playwright on Chromium, Firefox, and WebKit; real mobile browsers where available; limitations recorded in `blocker.txt`. WebKit emulation does not prove all Safari versions
- **16A.4 Security:** Standards section 5 and section 12 above; every confirmed critical or high finding fixed before the affected function is marked ready; only the owner can waive, in writing
- **16A.5 Performance and reliability:** Core Web Vitals, chat first-token time, API timings, query plans, large-list pagination, memory, queue throughput. Record measurements and proposed budgets; do not invent pass thresholds (spec section 9)
- **16A.6 Fix, retest, verify cycle:** reproduce, record severity and requirement, find root cause, smallest safe fix, regression test, focused tests, integration and E2E tests, full definition of done, independent review, record evidence, close only after verification. If review is unavailable, the defect is "fixed, review pending", not closed. Repeated failures follow section 20.1
- **16A.7 Continuous gates:** rerun relevant suites after each major module; one complete repository audit before declaring L0 complete
- **16A.8 Report:** `QUALITY_AUDIT.md` with category, scope, tests run, issues found, fixed, remaining, severity, evidence, and pass, fail, or blocked. No invented results or certifications

### 16B. CI/CD and automated testing

- **16B.1 Workflows:** extend the existing workflows rather than duplicating them. Add triggers for the development branch, a nightly schedule, and a `workflow_dispatch` test workflow. Leave `deploy-hostinger.yml` unchanged and never dispatch it; record its guards (manual only, `main` only, typed DEPLOY confirmation, `production` environment) in `PROGRESS.md`. No agent-written job deploys to production or on a push to `main`
- **16B.2 Trigger matrix:**

| Trigger | Required checks |
|---|---|
| Every push | ruff, ESLint, Prettier, backend unit tests, dependency audit, secret scan, frontend build |
| Every integration | Above, plus backend integration with PostgreSQL and Redis, migration checks when models change, tenancy and RBAC suite, widget SDK tests, critical Playwright on Chromium, accessibility and responsive checks on changed screens, coverage |
| Every major module | Relevant regression, Playwright on all three engines, accessibility, responsive, security |
| Nightly | Full regression, all-browser E2E, migration parity, AI evaluation sets (mocked or capped), security scans, tenancy isolation |
| Before staging deployment | Build, audit, secret scan, integration, sanity, migration validation, critical E2E |
| After staging deployment | Smoke, sanity, critical-path E2E, API health, database, Redis, worker, and queue health, accessibility |
| Before promotion request | Full regression, security, performance and load (disposable environment only), resilience, restore drill, quality audit (16A) |
| Manual trigger | Allowlisted suite, environment (ephemeral or staging, never production), and browser |

- **16B.3 Real providers and paid services:** never on push or nightly. Only owner-started manual runs with test-mode keys and an owner-set cap; cost recorded per run
- **16B.4 Staging:** a separate host, never the production Hostinger server, database, Redis, or storage; owner-provided. Deploy only from the development branch through a staging environment restricted to that branch; verify the target against an allowlist, the commit SHA, and artifact checksum; validate migrations on synthetic data; run smoke, sanity, and critical paths; mark success only when every gate passes; never blindly reverse a migration that may lose data. Without a staging host, record READY_FOR_OWNER and validate in ephemeral CI
- **16B.5 Evidence and reliability:** each run reports workflow, trigger, branch, SHA, suite, browser, passed, failed, skipped, and flaky tests, coverage, timings, artifacts; Playwright traces and screenshots on failure; retention 30 days for reports and 14 days for media (owner may change); no secrets or personal data in artifacts; skipped mandatory tests count as incomplete; at most 2 retries per test, and tests that pass only on retry are flaky and recorded
- **16B.6 Security:** explicit least-privilege permissions in every workflow; actions in new or changed workflows pinned to commit SHAs; no production secrets in test workflows; no secrets exposed to fork-triggered runs; concurrency controls for staging
- **16B.7 Usage limits and permissions:** check Actions minutes, runner capacity, and workflow permissions first. If anything is missing, record the exact blocker and options rather than skipping runs or reporting PASS
- **16B.8 Documentation:** `docs/runbooks/ci-cd.md`, `docs/runbooks/manual-testing.md`, `docs/runbooks/staging-deployment.md`; README steps for manual runs
- **16B.9 Acceptance:** prove with actual runs that development pushes trigger checks, a failing test fails the run, low coverage fails the build, a security finding blocks integration, manual runs work and every option maps to a real command, nightly has run at least once, Playwright runs on all three engines, staging validation (if a host exists) runs post-deploy checks and blocks promotion on failure, artifacts are accessible, and no agent workflow can reach production. Use negative-test fixtures on a temporary branch and remove them afterwards. A workflow file alone is not evidence

---

## 17. Mandatory blocker.txt

Template: BLOCKER ID, title, priority, module, spec requirement or gate, status (OPEN, READY_FOR_OWNER, RESOLVED, VERIFIED), problem, verified root cause, current implementation, impact, what was tried, work completed, why autonomous resolution is unsafe or impossible, exact owner action, step-by-step instructions, environment variable names (no values), external dependencies, expected result, verification procedure, tests to rerun, affected tasks, evidence.

Record blockers immediately. Never invent configuration steps or approvals. Separate verified findings from assumptions. Keep resolved blockers for traceability. Never turn a blocked gate into a pass.

Expected blockers include: spec approval and decisions D01 to D18; production Cognito, TLS, backups, monitoring, and incident authority (D10); staging host; provider choices and AI spend cap (D08, D09); legal review of consent and outbound rules for India (DPDP, TRAI and DND) (spec section 8); production-only gates (3 in production, 20 timed production drills, 25); pilot evidence (gate 23).

---

## 18. Documentation and evidence

Maintain: `PROGRESS.md` (module status, integration records, baseline backup record, checkpoint summaries, flaky-test history, workflow status), `GAP_MATRIX.md`, `FEATURE_MATRIX.md`, `APP_SCREEN_MATRIX.md`, `JOURNEY_MATRIX.md`, `blocker.txt`, `QUALITY_AUDIT.md`, `docs/architecture/`, `docs/decisions/`, `docs/investigations/`, `docs/runbooks/`, and the release checklist.

Evidence must trace to code, test runs, environment identity, and commit SHA. No fabricated evidence or percentages.

---

## 19. Progress reporting

Report separately: overall specified scope; L0 implementation; L0 tested readiness with evidence levels; L1 preparation; NOT_DUE phases; owner decisions; external dependencies; unresolved defects; CI run results. Every percentage states its numerator and denominator. NOT_DUE items are excluded from completion percentages. Never report whole-product readiness from L0 evidence.

After each item: item ID, status, commit SHA, checks passed, remaining issues.

Checkpoints (not stops): every 10 integrated items or every 24 hours of work, whichever comes first, update `PROGRESS.md`, the matrices, and `blocker.txt`, and post a status summary of no more than ten lines. Then continue.

---

## 20. Hard-stop conditions

Stop the affected task and record a blocker when:
- A change would break the truth rule, AI contract, or privacy and consent rules
- A change conflicts with the spec, or depends on an open decision
- An owner-only decision, credential, provider permission, or legal review is needed
- A production action would be required
- Protected-branch rules prevent integration
- A critical security risk cannot be resolved safely
- A destructive operation would risk real data
- A mandatory test or check still fails after the failure-escalation procedure (section 20.1) finds no safe resolution

Continue unrelated safe work. If every remaining task is blocked, finish with a complete status report.

### 20.1 Failure escalation

After three unsuccessful attempts on the same item:
1. Stop retrying the same approach
2. Write a root-cause analysis in `docs/investigations/<item-id>.md`, separating verified causes from hypotheses, and link it from `PROGRESS.md`
3. If a justified new approach can fix it safely without weakening requirements, tests, or thresholds, record the reason and continue. Each new approach gets its own three-attempt cycle
4. If two consecutive approaches each exhaust their attempts without measurable progress, treat the item as blocked
5. Record the cause, attempts, next steps, and evidence in `blocker.txt`
6. Keep the work on its task branch, unintegrated; keep related flags off; mark dependents blocked
7. Continue unrelated safe tasks

Never skip, disable, or weaken a test, lower a threshold, or mark a failing item passed.

---

## 21. Go/no-go tracking

Track all 25 spec section 12 gates with owner, evidence location, test output, commit SHA, date, result (PASS, FAIL, BLOCKED, NOT_DUE), and remediation. Use the spec section 12.1 gate-to-phase map: gates outside the active phase are NOT_DUE, never failed. For L0, evidence is expected at TESTED_LOCAL or TESTED_STAGING for the gates the map assigns to L0. Production parts of gates 3, 19, and 20, and gates 23 to 25, stay BLOCKED or NOT_DUE with the owner action recorded. The agent cannot waive any gate.

---

## 22. Completion definition

The loop is complete when:
1. All safe, locally executable L0 work is implemented
2. Required tests pass wherever executable
3. The matrices (section 5) cover every spec requirement, feature, screen group, and journey with phase and status
4. The development branch is validated
5. Every unresolved dependency is in `blocker.txt`
6. All 25 gates have a status: evidence, BLOCKED with a reason, READY_FOR_OWNER, or NOT_DUE
7. L1 preparation documents and contracts exist, with nothing activated
8. The quality audit (16A) is complete and `QUALITY_AUDIT.md` reflects measured results
9. CI acceptance (16B.9) passes with actual runs, or each unmet item is blocked
10. The repository is clean, recoverable, and inspectable
11. No production deployment, production change, outbound message, or planned-product activation has occurred

The final report separates: L0 development complete, L0 technically validated (with evidence levels), release candidate ready for owner review, L1 preparation ready, and owner decisions pending. Only the owner authorizes promotion, production deployment, or L1.

---

## 23. Final deliverables

1. Executive summary
2. SHA-pinned baseline inventory and classification
3. Feature, screen, journey, and gap matrices
4. Architecture summary
5. L0 fixes with evidence
6. Test totals, failures, and coverage
7. Security, privacy, and AI-contract assessment
8. Accessibility, responsive, and cross-browser results
9. Performance and resilience measurements with proposed budgets
10. Migration parity and restore evidence
11. Integration and provider status (mocked versus verified)
12. All 25 gates with status
13. Outstanding issues by severity
14. `blocker.txt` with step-by-step owner actions
15. Branch name and commit SHA
16. CI status and run IDs
17. L1 readiness proposal: data model, lifecycle mapping, RBAC changes, API contracts, test plan, and the decisions needed
18. `QUALITY_AUDIT.md`

Do not claim production readiness or commercial launch without the evidence.

---

## 24. Final execution instruction

**Execute OraOne Phase L0 autonomously, and prepare Phase L1 without activating it.**

Do not create pull requests or wait for routine approvals. Make well-supported technical decisions, preserve verified Product 1 behaviour and history, keep to the spec, validate every meaningful change, and fix problems rather than only documenting them.

Do not push to `main`, dispatch the production deploy workflow, change production configuration, send messages to real people, activate gated products or channels, treat proposed decisions as approved, or invent evidence.

**The desired outcome is a hardened, tested, documented Product 1 foundation with honest evidence levels, a ready L1 design, every owner dependency clearly recorded, and no false claims of readiness.**
