# OraOne OS — Complete Autonomous Build and Validation Goal v2.1

Authoritative product specification: OraOne-OS-Master-Product-Spec-v2.1.md
Engineering baseline: OraOne-OS-Engineering-Standards-v2.1.md
Repository: varunjakkampudi-tech/OraOne
Mission: Implement and validate the complete unified OraOne OS across all modules (website, WhatsApp, Instagram, humanlike voice and eligible outbound calling, Lead OS, omnichannel, workflows, integrations, AI Studio, marketplace, analytics, beta, admin/ops, billing, future Growth). Do not restrict the product goal to Chat/Product 1. Distinguish planned, implemented, test-confirmed, provider-approved, beta and production-verified states. Production push/merge, commercial sends/calls, paid vendor accounts, and deployment are owner-only.
## 0. Preflight and precedence
Read the v2 product spec and Engineering Standards, the repository, migration history, README, legacy v1.1/L0 documents, PR history, CI and Hostinger workflow. This v2.1 goal supersedes the earlier L0-only authorization once the owner approves the v2.1 plan in writing. Until then, the v1.1 L0 goal (OraOne-Autonomous-Goal.md) remains the only active authorization, so there is no gap. Record the approval date and approved file versions in `PROGRESS.md`. Existing high-priority privacy, safety, truth, tenancy and non-spam requirements retain precedence. No undocumented release date or proof-of-production assumption.

Revalidate exact main HEAD and branches before beginning. Audit whether recent code or configs changed from 19 Oct baseline. Verify deploy-hostinger.yml is manual-only on main and protected by a production environment; do not trust a file name alone. Inventory existing product modules and tests and preserve working code/migrations, all owner changes and full history. Create an external git bundle, checksum, verify, restore-clone and fsck before major change; stop unsafe change if recovery proof fails.
## 1. Execution authority and workflow
- Autonomous technical decisions for implementation order, refactors justified by evidence, domain boundaries, tests, UI fixes, CI on development branch, safe synthetic mocks and documentation. No repeated user approval for internal technical details.
- One designated development integration branch, small task branches/worktrees when useful, no PR requirement for autonomous loop, no push to main, no branch protection bypass, no production configuration changes or deploy-hostinger.yml execution. All code goes through independent second-session review, full relevant tests and sequential validated integration; when independent reviewer unavailable, mark pending, do not claim review, and hold sensitive changes on task branch.
- External accounts, provider approvals, consent evidence, commercial billing, real sending/calling, changing terms, marketing publication, paid spend, production data, beta invitations and production merge/deploy stay owner-only. Record an exact step-by-step blocker.txt item and continue unrelated safe work.
- Goal is end-to-end full OS internal code readiness in authorized phases, with explicit gates for third-party approval and real-production evidence. Do not claim all products ready when critical live permissions are missing. A fully integrated mock is not an operational WhatsApp/Instagram/calling service.
### 1.1 Engineering Standards in autonomous mode

| Standards wording | Autonomous-mode equivalent |
|---|---|
| "Every pull request" or "every development integration" | Every integration into the development branch, run on the task branch before and on the integrated baseline after |
| "Every development push" | Every push to the development branch or a task branch |
| "Nightly" | The scheduled nightly run, every checkpoint, and before any promotion request |
| "Staging before and after deployment" | Authorized staging deployments only, on a host separate from production; without one, ephemeral CI validation and a READY_FOR_OWNER blocker |
| A reason or template field in a pull request | The commit message and the item's `PROGRESS.md` integration record (requirement, tests, screenshots, migration notes, rollback plan, review result) |
| Human approval | Independent review session; owner review before promotion for the sensitive areas in Standards section 6.3 |
| Owner-exclusive authority (Standards section 11) | Not available to the agent; recorded as READY_FOR_OWNER |

No check is dropped and no threshold is reduced.

## 2. Required initial artifacts before implementation
Create: GAP_MATRIX.md, FEATURE_MATRIX.md, APP_SCREEN_MATRIX.md, JOURNEY_MATRIX.md, PROVIDER_PERMISSION_MATRIX.md, TEST_MATRIX.md, MIGRATION_AUDIT.md, RISK_REGISTER.md, COST_MODEL.md, PROGRESS.md, QUALITY_AUDIT.md, blocker.txt and ADRs. Enumerate every spec feature OS-01–OS-10, OS-WEB/WA/IG/VOICE/OMNI/CRM/FLOW/INT/MKT/STUDIO/ANALYTICS/BILL/BETA/ADMIN/OPS/GROWTH/EXT and gates G01–G30, mapping source code, phase, test, actor, exact SHA, evidence level, status and blocker.

Statuses: SPECIFIED; OBSERVED_CODE; IMPLEMENTED; TESTED_LOCAL; TESTED_STAGING; VERIFIED_EXTERNAL; VERIFIED_PRODUCTION; BETA; GATED; BLOCKED; READY_FOR_OWNER; NOT_DUE; RETIRED. NOT_DUE is only for a feature deliberately excluded from an approved release, not an excuse to silently omit an all-OS goal. Every rate/percentage states numerator and denominator.

Audit all routes/screens (including apparent duplicates and hidden old prototype modules), migrations and production source truth. Re-verify the spec Appendix A.1 repository facts and apply rules R1 to R7 where they need no open decision. Classify routes as working, real error, disabled, planned or broken, rather than 'functional' when auth/API fails. Never treat unused model names as functioning modules.
## 3. Complete execution stages
1. Baseline preservation: migrations ↔ model parity, restoring historical data compatibility, no surprise deletes, real dependency inventory/license/SBOM, backend+frontend builds, current CI execution, security and exposed-secret audit.
2. Unified shell and product map: professional responsive/accessible operator app for every approved module, UX state machine and permissions, clean marketing/demo/website truth, complete API and documentation navigation.
3. Security/privacy foundation: central tenant RBAC/policy + consent/suppression; webhook auth/replay; input/output/header/CSRF/XSS/SSRF; redacted logs, export/delete workflows, rate-limit and budget fail-closed, admin MFA/step-up.
4. Lead OS and website: accurate lead/contact/opportunity canonical model and import, website script/widget, RAG, inbox and handoff, routing/SLA, campaigns eligibility, pipeline and key metrics.
5. WhatsApp official adapter: compliant onboarding/token/webhooks/templates/two-way messages, opt-out, inbox, error reconciliation; synthetic provider contract tests first; external approval gate before live send.
6. Instagram official adapter: eligible professional account onboarding/permissions, initiated conversations, supported comments/DM, inbox handoff; mocks first, live external verification only after permission.
7. AI voice: speech streaming, interruptions, inbound test numbers, transfers, voice templates, human takeover; contact import preview with consent evidence, DND and suppression, approved dry run, eligible queue, bounded dialing attempts, cost and kill switch. No real outbound attempt until owner's telecom/consent/provider authorization.
8. Workflow automation + integrations: typed builder, versioning, durable execution/replay, approvals, connector catalog, sandbox/mocks, per-tool deterministic authorization.
9. Studio/marketplace: scoped agent development, source evaluations, vetted templates/connector submissions, scanning, moderated admin publishing and revoke/rollback.
10. Analytics/billing/beta/admin: verified events and metric definitions, billing caps and reconciliation, beta cohort/flags, versioned config admin with validation, staged preview and publish, redacted logs, incident tools and exports.
11. Future marketing modules: prepare separate gated official YouTube/Instagram publisher contracts, OAuth, campaign calendar and draft/review flow, without auto-posting or implying approved access.
12. Operations, deploy and hardening: Hostinger reference architecture, safer staging, backups/restore, performance/load, SLO monitoring and independent alerts; owner-only protected main manual production deployment.
Stage order follows the spec build-order rule (section 8.1): stages 5 to 11 start implementation only after the R0 gates G01, G03, G04, G21, and G22 pass and the shared services they depend on exist with passing tests. Before that, those stages produce specifications, adapter contracts, fixtures, and mock-based contract tests only.

After every module, run all relevant test categories and update evidence. Resolve dependencies rationally; do not enable a channel solely because its UI exists. If a provider cannot approve use, finish safe mock contracts and mark VERIFIED_EXTERNAL and production gates BLOCKED, not PASS.
## 4. Full product testing — no exceptions
For every active or upcoming OS module, enumerate and implement acceptance tests in TEST_MATRIX.md: happy/edge/negative/malformed input/unauthorized actor/cross tenant/consent denial/suppression/DND/provider unavailability/latency timeout/rate limit/cost exhaustion/race/duplicate/replay/cancellation/rollback/deletion/privacy/accessible interaction/localization/responsive/cross browser/security audit. Build test fixture contracts for WhatsApp events, Instagram DMs, streamed voice calls and call attempt states, XLSX imports, workflow replay, marketplace moderation, billing and admin config publish. Real provider E2E remains an external stage and must not be replaced with mocks in readiness reporting.

Default CI: push → format/lint, type, build, security, unit. Integration branch → disposable DB/Redis/S3 integration, migration parity, critical E2E and tenant RBAC. Nightly → full regression, Chromium/Firefox/WebKit, a11y, security, AI eval and reliability. Manual workflow_dispatch → independently select smoke/sanity/critical/regression/API/frontend/widget/voice/WhatsApp/Instagram/workflows/integrations/marketplace/admin/analytics/security/privacy/load/restore/all, browser and allowed environment; exact commands and evidence. Before/after staging deploy → comprehensive safe checks and environment validation. Before production owner dispatch → all G01–G30 that apply to the desired live OS offering must pass. Missing integrations block an all-products public release.

Require execution evidence from GitHub workflow runs: branch, SHA, exact suite, counts, coverage, skipped/flaky, versions, run IDs, screenshots/traces, vulnerability summaries, artifact provenance and outcome. Never infer passing from YAML alone. Inject safe negative tests on temporary dev branches to verify failed tests block integration and promotion.
## 5. User experience acceptance
Implement and review every matrix screen at 320–1920 widths, WCAG 2.2 AA, keyboard, zoom/reflow, focus, TalkBack/VoiceOver/NVDA where appropriate, reduced motion, no dead buttons or fake forms, role-appropriate nav, clear loading/empty/error/offline states. Functional Chrome/Firefox/WebKit; actual mobile browsers where available. Preserve OraOne logo and coherent design identity. Approved real demos can be clearly labeled; never use invented claims, customer testimonials, fake customers, fake metrics, fictional provider connections, placeholder prices or backend-unwired forms on oraone.in.
## 6. Critical operations and change management
- Build secure admin config draft → validate → test → approve → publish → audit → monitor → rollback. Publish tenant settings only within tenant scope; global/provider keys with privileged controls. GitHub code deployment is a separate owner-only action, not a consequence of admin publish.
- Beta uses per-tenant/user flags, independent kill switches, preview cohorts, privacy approvals, test suites and rollback. Beta ≠ bypass of production law, permissions or mandatory tests.
- End-to-end correlation IDs, redacted logs and secure admin export; reproducible incidents with trace context, severity, affected release SHA, alert, RCA and test-backed hotfix. No guarantee that all bugs resolve within seconds.
- No live sends, calls, payment charges, content posting or privileged provider actions for automated tests. Use synthetic fixtures and official sandbox/test accounts where authorized.
- Validate Hostinger manual main-branch deployment: protected production GitHub environment, human review, typed confirmation, immutable artifact SHA, backup/recovery, migration validation, deployed health and smoke, rollback validation, independent monitoring. Leave workflow execution and production infra changes to owner.
## 7. Failure handling, reviews and reporting
For each defect: reproduce → capture sanitized evidence → root cause → smallest safe fix → regression test → focused/unit/integration/E2E → quality checks → independent review → revalidate integrated branch → close only on actual PASS. After three failed attempts, document RCA in `docs/investigations/`; try a defensible new approach, each with its own three-attempt cycle. If two consecutive approaches each exhaust their attempts without measurable progress, treat the item as blocked: keep it on its task branch, unintegrated, flags off, dependents marked blocked, and continue other work. No suppressing/skipping required tests, lowering gates or fabricated reviews.

Every 10 integrated tickets or daily work checkpoint: update PROGRESS.md with counts and evidence, blockers and next work. For a new reviewer, provide requirements, diff, surrounding code and tests; not implementer reasoning. Keep clean worktree and backup recovery proof. Preserve owner changes and existing production data.
## 8. blocker.txt contract
For each genuine external action: ID, severity, module, spec gate, verified fact vs assumption, exact missing permission/provider/config, environment variable name (never value), why agent cannot do it, what was completed, step-by-step owner action with official documentation source, expected result, test/verification to rerun, dependencies, and status OPEN/READY_FOR_OWNER/RESOLVED/VERIFIED. Separate blocked future channel approvals from genuine engineering defects. Keep unrelated safe work moving.

Expected examples: WhatsApp business verification and templates, Instagram professional account/app review, telephony commercial registration and lawful recipients, provider bills/spend ceilings, host/Cognito/Stripe, content publishing scopes, beta tester consent, production domain/TLS, independent backups, staged deployment authorizations.
### 8.1 Hard-stop conditions

Stop the affected task, record a blocker, and continue unrelated safe work when:
- A change would break the safety, privacy, tenancy, truth, or anti-spam rules
- A change depends on an open owner decision (spec section 13)
- Credentials, provider approval, consent evidence, legal review, or paid spend are needed
- A production action, real send, real call, real charge, or real post would be required
- Branch protection prevents integration
- A critical security risk cannot be resolved safely
- A destructive operation would risk real data
- A mandatory check still fails after the failure-escalation procedure in section 7

## 9. Final full OS completion and no-go criteria
Only declare complete OraOne OS production readiness if: all product modules requested for live availability are real, externally authorized and live-validated; every G01–G30 applicable gate passes; security issues and migration drift resolved; full beta/accessibility/performance/recovery evidence; all channel/contact policy enforcement tested; all public UI and claims truthful; owner-approved protected main build and Hostinger production deployment tested; dashboards, logs, backups and incident procedures working; manuals, provider rights and docs current. A module without verified official permissions is not ready, regardless of mocks or code completeness.

Gates outside the target release are reported NOT_DUE using the spec section 9.1 map, never as failed. Deliver final reports: executive dashboard, full phase/product statuses and percent numerators, all screens/journeys/test case status, provider integration matrix, imported Excel consent rejection evidence, legal/compliance gaps, security findings and fixes, CI run IDs, migration parity, billing cost controls, Hostinger deployment readiness and owner steps, backup/restore, public website truth audit, beta rollout and exact blocker.txt.

Agent scope today: Prepare and implement safe development/staging changes after owner approval of this v2 program; never autonomously touch production, send real outbound campaigns, merge main or dispatch production deployment. External and release authorization remains owner-controlled.