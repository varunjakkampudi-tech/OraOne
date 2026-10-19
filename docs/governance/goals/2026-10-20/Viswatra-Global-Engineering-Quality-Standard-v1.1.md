# Viswatra — Global Engineering and Quality Standard v1.1

**Applies to:** every Viswatra product (OraOne, CareerScope, FixHub, AI smart glasses, and future products), every repository, every person and every AI agent.
**Version:** 1.1 (19 October 2026), with final consistency corrections. **Status: FROZEN.** New global requirements only through a change request that names a concrete gap, risk or approved change. **Applied change requests:** CR-01 Browser, runtime and data-leakage quality gate (19 October 2026), mapped into categories 11, 12, 13, 22, 25, 26, 27 and 30; it changes no product scope and resets no approval. CR-02 No AWS and no repository names (20 October 2026), mapped into categories 1, 5, 6, 22 and 29. Supersedes `Viswatra-Global-Engineering-Baseline.md` v1.0; all v1.0 rules are kept and reorganized into 30 numbered categories, with additions from the Global Engineering Completion Program.
**Purpose:** one reusable floor for engineering, security, testing, operations, documentation and release readiness. It does not replace product requirements. Each product keeps its own Product Spec, Engineering Standards and Autonomous Goal.

---

## How to use this standard

### Precedence
1. The product's approved Product Spec decides **what** the product does and its scope.
2. The product's Engineering Standards and Autonomous Goal decide **how** that product is built.
3. This standard applies wherever those are silent.
4. Where they differ, the **stricter** rule wins. A product may loosen a rule here only with a written owner exception in its decision register.
5. **Scope rule:** this standard governs engineering quality. It never adds product features to a product whose scope is frozen (for example FixHub v1.3). Where a category here needs a capability the product spec does not include (for example an admin log viewer), record it as a gap in `GAP_MATRIX.md` and `blocker.txt` as READY_FOR_OWNER for a scope amendment; do not build it silently.

Categories 1, 22, 23 and 24 are floors that no product document, deadline or agent decision may weaken.

### Applicability tags
**[web]** public or app web, **[api]** backend, **[admin]** operator console, **[mobile]** Android/iOS, **[device]** firmware or hardware, **[ai]** products using LLMs or ML. A category that does not apply is recorded NOT_APPLICABLE_WITH_REASON in the Product Profile (Appendix A), never skipped silently.

### Category index
| # | Category | # | Category |
|---|---|---|---|
| 1 | Non-negotiables and authority | 16 | Accessibility |
| 2 | Evidence and status vocabulary | 17 | Responsive and cross-platform |
| 3 | Repository governance and Git workflow | 18 | Frontend and design system |
| 4 | Architecture and project structure | 19 | Performance |
| 5 | Naming conventions | 20 | Technical SEO |
| 6 | Configuration and environments | 21 | Localization |
| 7 | Clean code and static analysis | 22 | Security |
| 8 | AI-tool and agent file hygiene | 23 | AI and LLM security |
| 9 | API design and contracts | 24 | Privacy |
| 10 | Data, migrations and integrity | 25 | Testing automation |
| 11 | Application logging | 26 | Functional verification |
| 12 | Monitoring, tracing, alerting and incidents | 27 | CI/CD |
| 13 | Audit log and admin log system | 28 | Deployment, reliability and disaster recovery |
| 14 | Admin governance | 29 | Documentation and GitHub maintenance |
| 15 | Analytics and business intelligence | 30 | Definition of done, release readiness and reporting |

---

## 1. Non-negotiables and authority

1. **Truth.** Never fake evidence, test results, metrics, users, customers, revenue, reviews, ratings, prices, providers, availability or success messages. Demo data is isolated and labelled.
2. **No secrets** in code, chat, logs, screenshots, CI artifacts or Git history. Any exposed secret is treated as compromised: the owner rotates it, dependent sessions are invalidated, activity is reviewed, evidence is recorded.
3. **No provider secrets in clients:** never in web bundles, Android/iOS apps or firmware. Clients call your server.
4. **Owner-only actions:** production deployment or configuration, merging or pushing to protected `main`, rotating live credentials, real messages to real people, spending, creating or changing external accounts, accepting terms, app-store submission, DNS and domain changes, GitHub repository settings (branch protection, environments, secrets).
5. **Git workflow per repository:** autonomous development-branch integration without agent-created pull requests is the preferred workflow **only where the owner has approved it for that repository**. Elsewhere, the repository's existing workflow, branch protection, required reviews and instructions stay binding. No agent modifies GitHub settings, pushes to protected `main`, force-pushes, rewrites published history, bypasses required approvals, or resets, stashes or discards owner work.
6. **Governance first:** if a repository's current instructions (for example `AGENTS.md`) forbid an action, record the proposed change and wait for owner approval. Never bypass protections.
7. **Nothing is "done" without evidence** at the right level (category 2). No category is reported 100% without a measured denominator.
8. **No check is skipped and no threshold lowered** to pass. Only the owner lowers a threshold, in writing.
9. **Public repositories** contain no personal data, private paths, internal URLs or confidential material.
10. **One agent per repository branch at a time.** Two autonomous loops never write to the same development branch concurrently.
11. **No AWS (CR-02).** No product uses Amazon Web Services, including Amazon Cognito, S3, SES, SNS, Lambda, RDS or CloudFront, because of cost. Use application-managed identity and non-AWS providers (for example Hostinger, MinIO or another S3-compatible service, Resend). Existing AWS usage is replaced through a recorded owner decision and migration plan; tests, CI and runtime never call AWS.
12. **No repository names or links (CR-02)** in documents, commit messages, changelogs or release notes. Refer to "this repository" or the product name instead.

---

## 2. Evidence and status vocabulary

### 2.1 Evidence levels
| Level | Meaning |
|---|---|
| SPECIFIED | Written in an approved document only |
| OBSERVED_CODE | Code read; not proven to work |
| TESTED_UNIT | Passed unit or component tests |
| TESTED_INTEGRATION_REAL_DB | Passed against real databases or services in a disposable environment |
| TESTED_BROWSER / TESTED_DEVICE_SIM | Passed real browser automation, or simulator/emulator |
| TESTED_STAGING | Passed on a separate staging environment |
| VERIFIED_PROVIDER | Proven with the real third-party account, not a mock |
| VERIFIED_REAL_DEVICE | Proven on physical phones or hardware |
| FIELD_VALIDATED | Proven with real consenting users in real conditions |
| LIVE | In production after owner-authorized deployment |

Mocks are never VERIFIED_PROVIDER; simulators are never VERIFIED_REAL_DEVICE or FIELD_VALIDATED; documents are never PASS.

### 2.2 Statuses
- **Requirement:** PLANNED, IMPLEMENTED, INTEGRATED, the evidence levels, BLOCKED, READY_FOR_OWNER, NOT_DUE, NOT_ASSESSED, NOT_APPLICABLE_WITH_REASON, RETIRED.
- **Portfolio adoption (Appendix B):** NOT_ASSESSED, NOT_APPLICABLE_WITH_REASON, PLANNED, IMPLEMENTED, TESTED, VERIFIED, BLOCKED, READY_FOR_OWNER.
- **Test:** PASS, FAIL, BLOCKED, NOT_RUN, SKIPPED_WITH_REASON, FLAKY, NOT_APPLICABLE. A skipped mandatory test is not a pass.
- **Gate:** PASS, FAIL, BLOCKED, NOT_ASSESSED, NOT_APPLICABLE with reason.

### 2.3 Separately evidenced release states
Internal build complete → mock-provider validation → staging validated → field readiness → live provider approval → app-store approval (if any) → public production launch (owner only). None implies another.

### 2.4 Activation status
A product's autonomous build goal is **ACTIVE** only when its activation approval (the approved spec version and any named activation decisions) is recorded with date and approver in that repository's `PROGRESS.md` or decision register. Otherwise its status is **AWAITING_OWNER_APPROVAL**: read-only auditing and work already authorized under the repository's current governance may proceed; implementation may not. A statement in a document or chat is not a recorded approval until it is written into the repository record.

### 2.5 Completion verification
| Item | Status may be claimed only when |
|---|---|
| This global standard | SPECIFIED once the canonical document is approved |
| Per-product adoption | VERIFIED only when every applicable category has current, repository-specific evidence (SHA and date) |
| Repository cleanup | VERIFIED only after full inventory, static analysis, manual audit, remediation and final validation (7.4) |
| Staging readiness | Real staging evidence from a separate staging environment |
| Production readiness | Every applicable release gate passed and an explicit owner GO recorded |
| Portfolio | Never "complete" because one document or one repository passes; each product is reported separately |

---

## 3. Repository governance and Git workflow

1. **Discover, don't guess:** verify each repository URL, access and permissions before work.
2. **Record the baseline:** commit SHA, branches, tags, remotes, `git status --porcelain`, existing uncommitted changes.
3. **Verified backup** before major changes: `git bundle create … --all`, `git bundle verify`, SHA-256 checksum, test clone, `git fsck`, recorded in `PROGRESS.md`. If any step fails, stay read-only.
4. Owner work is never stashed, reset, cleaned or committed by an agent; use a separate worktree.
5. Where approved for the repository (category 1.5): development integration branch with short-lived `task/<id>-<slug>` branches; one requirement at a time; definition of done before each integration; sequential integration.
6. **Change and rollback register** (`CHANGE_REGISTER.md`): each integration's SHA, scope, risk, migrations, and the exact rollback steps.
7. **Independent review** in a separate agent session given only requirements, diff, context and test results. If unavailable: never claim it; label "independent review pending"; sensitive areas stay on their task branch.
8. **Failure escalation:** three failed attempts → root-cause analysis in `docs/investigations/<id>.md` → new approach; two failed approaches → blocked, flags off, continue other work.
9. **Checkpoints** every 10 integrated items or 24 hours: matrices, `PROGRESS.md`, `blocker.txt`, a summary of at most ten lines; then continue.
10. Open owner decisions block only what depends on them; record READY_FOR_OWNER with recommendation, options, risks and exact owner steps.
11. **blocker.txt template:** ID; title; priority; module; requirement or gate; status (OPEN, READY_FOR_OWNER, RESOLVED, VERIFIED); problem; verified cause; current state; impact; what was tried; work completed; why autonomous resolution is unsafe or impossible; exact owner action; step-by-step instructions; environment variable names (never values); dependencies; expected result; verification; tests to rerun; evidence. Keep resolved items.

---

## 4. Architecture and project structure

- **Organize by feature/domain**, each owning its routes, UI, services, data access and tests. Clear module ownership recorded in `CODEOWNERS` or the architecture document.
- Layers: boundary (routes, validation) → services (business rules) → repositories (data access). Thin routes. UI never calls databases or third-party APIs directly.
- **One authoritative implementation per domain:** one identity model, one migration history, one API per concern. Duplicate endpoints, services, models, clients and parallel backends are reconciled, not left side by side.
- **No circular dependencies;** dependency direction enforced by a tool (dependency-cruiser or madge for TypeScript, import-linter for Python, Gradle module rules for Android).
- Modular monolith by default; split into services only with evidence (scale, team, isolation) recorded in an ADR.
- Shared code in `shared/` or `packages/` only when used by two or more domains; shared UI through the design system.
- **Prefer improving sound existing architecture** over framework rewrites; a rewrite needs an ADR with evidence.
- Deprecation policy: deprecated modules and APIs are marked with a removal date, migration path and owner.

Reference layout (adapt per stack and record differences in the Product Profile):
```
/apps/web  /apps/admin  /apps/mobile        # clients
/services/api/src/<domain>/                  # routes, service, repository, schemas, tests
/services/api/migrations/                    # one ordered migration chain
/packages/ui  /packages/config               # design system; shared lint/tsconfig/prettier
/firmware                                    # [device]
/e2e  /docs  /scripts  /.github/workflows
```

---

## 5. Naming conventions

| Item | Convention |
|---|---|
| Folders | `kebab-case` |
| TS/JS files | `kebab-case.ts`; React components `PascalCase.tsx` (one style per repo, lint-enforced) |
| Components, classes, types | `PascalCase` |
| Functions, variables | `camelCase`; booleans as questions (`isActive`, `hasConsent`) |
| Constants | `UPPER_SNAKE_CASE` |
| Python | modules/functions `snake_case`, classes `PascalCase` (PEP 8) |
| Kotlin | classes `PascalCase`, functions `camelCase`, packages lowercase |
| C firmware | `snake_case` with module prefix (`audio_init`) |
| Database | tables plural `snake_case`; `id`, `created_at`, `updated_at`; foreign keys `<entity>_id` |
| API paths | `/v1/` prefix, plural nouns, `kebab-case` |
| Env variables | `UPPER_SNAKE_CASE` with product prefix (`FIXHUB_DB_URL`) |
| Analytics events | `object_action`, past tense (`booking_created`) |
| Feature flags | `ff_<area>_<feature>` with owner and expiry |
| Branches | `dev` (integration), `task/<id>-<slug>` |
| Commits | Conventional Commits with requirement ID; never a repository name or URL (CR-02) |

Names describe purpose. No `utils2`, `new`, `final`, `temp`, `test123`, `data`, and no misleading names (a suite called "playwright" runs Playwright).

---

## 6. Configuration and environments

- All configuration from environment variables or a config service, **validated by schema at startup** (zod, pydantic); missing required config outside test mode stops the app with a clear error.
- No default secrets. `.env.example` lists every variable with description and fake value; real `.env*` files are git-ignored.
- Environments: local, test, CI, staging, production, each with its own config; production values never present in CI test jobs.
- No hard-coded URLs, hosts, credentials or environment-specific values in source.
- Test-only shortcuts (fixed OTPs, persona switches, seed users) exist only in explicit test mode and are absent from staging and production builds; a test proves it.
- Feature flags: server-evaluated, default off, owner and expiry recorded, removed after rollout.
- `CONFIG_REFERENCE.md` documents every variable, its purpose, environments, and whether it is secret.

---

## 7. Clean code and static analysis

### 7.1 Rules
- **Target for a completed repository cleanup audit:** zero unused files, exports, functions, classes, hooks, variables, imports, parameters, types, components, routes, styles, assets, fonts, translation keys, scripts, dependencies, environment variables, feature flags or database columns.
- **Per change:** zero *new* lint, format, unused-code, complexity, duplication or architecture (boundary and circular-dependency) violations.
- No commented-out code, unreachable branches or leftover debug output.
- `TODO`/`FIXME` only with an issue or requirement ID; none in launch-critical paths at release.
- Strict typing (TypeScript `strict`; mypy/pyright for Python); no new `any`, `@ts-ignore`, `# type: ignore` or non-null assertions without a reason and ID.
- Cyclomatic complexity ≤ 10 per function (lint-enforced); files over ~400 lines need a reason; duplication below the tool threshold.
- No deprecated APIs or unsupported/abandoned dependencies without a dated replacement plan.
- Errors handled explicitly; never swallowed.

### 7.2 Tools by stack
| Check | TypeScript / React | Python | Kotlin / Android | C / ESP-IDF |
|---|---|---|---|---|
| Lint | ESLint (typescript-eslint, react-hooks, jsx-a11y, import) | ruff | detekt, Android Lint | `-Wall -Wextra -Werror`, cppcheck, clang-tidy |
| Format | Prettier | ruff format | ktlint | clang-format |
| Types | `tsc --noEmit` strict | mypy / pyright | compiler | compiler |
| Unused code and deps | knip | vulture, ruff F401/F841, deptry | Android Lint `UnusedResources`, detekt | cppcheck `unusedFunction` |
| Circular deps / boundaries | dependency-cruiser or madge | import-linter | Gradle module rules | — |
| Duplication | jscpd | jscpd | jscpd | jscpd |
| Unused CSS | Tailwind content scan; PurgeCSS otherwise | — | — | — |
| Translation keys | missing/unused key script | same | `MissingTranslation`, unused strings | — |

All run in CI (category 27) and in pre-commit hooks.

### 7.3 Safe deletion
**No file or symbol is deleted solely because an analyzer reports it unused.** Delete only after proving it is unused: check dynamic imports, string-based references, reflection, framework conventions (file-based routing, auto-registration, dependency injection), scheduled jobs and cron, migrations and seed scripts, deployment and CI references, and external consumers of public APIs or SDKs. Record the proof in the change register. Never delete historical database migrations, security evidence, license files, or required operational scripts.

### 7.4 Full clean-code audit (on adoption and before each major release)
1. Run every tool in 7.2; fix all findings.
2. Inventory every tracked file: purpose, location, name, references.
3. Inventory routes, endpoints, jobs, migrations, env vars, flags and dependencies; remove or justify unreferenced ones (7.3).
4. Static analysis on everything; **manual line-by-line review** prioritized by risk: authentication, authorization, payments or quotes, data access, file handling, webhooks, admin, configuration, then the rest.
5. Check structure and naming against categories 4 and 5; move or rename with `git mv`.
6. **Disposition every pre-existing finding**, not only new ones, as FIXED, FALSE_POSITIVE_WITH_PROOF, or OWNER_EXCEPTION (with decision ID, reason and review date). Existing critical and high security findings are never ignored because they predate a change; they follow category 22.
7. Re-run the full definition of done. Record in `QUALITY_AUDIT.md` with file counts reviewed out of total and findings by disposition. Only then may cleanup be marked VERIFIED (2.5).

---

## 8. AI-tool and agent file hygiene

- Inventory files created by or for AI coding tools: `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`, `GEMINI.md`, `.gemini/`, `.cursor/`, `.windsurf/`, Antigravity or other agent folders, prompt files, scratchpads, transcripts, caches and generated plans.
- **Keep** active governance instructions (for example `AGENTS.md`) until their rules move to an owner-approved canonical policy; then reduce duplicates to one canonical file plus thin pointers.
- **Remove** from the repository: scratchpads, temporary prompts, chat transcripts, caches, unused skill configurations, and duplicate or contradictory instruction files — after checking they are not referenced.
- **Before removing a transcript or prompt file, scan it for secrets and personal data.** If any is found, deleting the file is not enough: the secret is treated as exposed (category 1.2) and the owner rotates it. History is not rewritten.
- **Exclude** all agent material from build artifacts, Docker images, mobile bundles, firmware images and deployments (via `.dockerignore`, build includes, and a CI check that inspects the artifact).
- Preserve legitimate in-product AI features, CI/CD, tests, developer docs and reproducible build tools.
- `.gitignore` covers agent caches and scratch folders so they do not return.

---

## 9. API design and contracts [api]

- Typed contracts: OpenAPI (REST) or schema files for other protocols, generated or validated in CI; request and response validation at the boundary.
- Versioned APIs (`/v1/`); backward-compatible evolution; breaking changes only in a new version with a dated deprecation of the old one (`Deprecation` and `Sunset` headers where useful).
- Consistent error format (for example RFC 9457 problem details) with stable error codes; no internal details or stack traces in responses.
- Pagination on every list (cursor-based for large or changing data); filtering and sorting allowlisted.
- Idempotency keys on create and payment-like actions; correct HTTP semantics (201, 204, 409, 412, 422, 429).
- Rate limits and quotas per actor; `Retry-After` on 429.
- Event and webhook payloads have versioned schemas.

---

## 10. Data, migrations and integrity [api]

- One ordered migration history; additive migrations; never edit applied migrations; each tested for upgrade and, where feasible, rollback on a disposable database; model/schema parity checked in CI.
- Constraints in the database (foreign keys, unique, check, not null) as well as in code; indexes justified by query plans.
- Transactions around every multi-step state change; optimistic concurrency (version columns) where records are edited concurrently; first-wins and capacity rules enforced inside the database transaction; locks and caches are optimizations, never the source of correctness.
- Background workers are idempotent, leased, retried with backoff and jitter, with a visible dead-letter queue; transactional outbox for external side effects.
- Every mutable record: stable ID, actor, timestamps, version, retention class, audit trail for sensitive changes.
- Encryption at rest for sensitive fields; key custody documented.
- ERD maintained (category 29).

---

## 11. Application logging

- **Structured JSON** only (pino, structlog, Timber JSON, ESP-IDF structured tags).
- Fields: `timestamp` (UTC ISO 8601), `level`, `service`, `env`, `release` (commit SHA), `request_id`, `trace_id`, `span_id`, pseudonymous `actor_id` and `actor_type`, `event`, `message`, `duration_ms`, and `error.fingerprint` for errors.
- Levels: `fatal`, `error`, `warn`, `info`, `debug` (off in production by default).
- **Never log:** passwords, OTPs, tokens, cookies, API keys, complete phone numbers or emails, addresses, exact coordinates, message bodies, photos, private documents, payment or health data. A central redaction list is applied by the logger. **Redaction is proven by tests that log synthetic secrets and sensitive fixtures and assert they never appear** in logs, traces or exports.
- Request ID created at the edge and propagated through services, queues, jobs and outbound calls (W3C Trace Context via OpenTelemetry); returned to users as an opaque support reference.
- Browser and mobile exceptions captured with PII scrubbing and release tags; session replay only with consent and masking.
- Sampling for high-volume debug and info logs; never for errors or audit events. Retention per category 24.
- **No silent failure (CR-01):** an unexpected runtime error, security finding or data leak always creates an actionable incident or defect with severity, reproduction details, source location (file and line, or stack fingerprint), responsible owner and a regression test. Swallowed exceptions and empty `catch` blocks fail lint.
- Release builds of mobile apps and firmware log no personal data, tokens or secrets to device logs (logcat, Xcode console, serial).

---

## 12. Monitoring, tracing, alerting and incidents

- OpenTelemetry-compatible traces across web, API, workers and provider calls where appropriate.
- Metrics: RED per endpoint (rate, errors, p50/p95/p99 duration); USE per resource (utilization, saturation, errors); queue depth and age, retries, dead letters; database and cache health; provider latency, failures and delivery outcomes; infrastructure capacity and cost.
- Errors grouped by fingerprint and attributed to release SHA, enabling **release-to-release error comparison**.
- Health endpoints `/health/live` and `/health/ready`; synthetic checks for critical journeys on staging and, by the owner, production.
- **Monitoring and alert delivery independent of the primary host** (an external uptime checker and alert channel), so an outage of the host does not silence its alerts.
- Incident classification (SEV1–SEV4 with definitions), alert routing, acknowledgement, escalation and resolution history; each alert links to a runbook.
- **Automated incident detection (CR-01):** alerts for unusual authentication failures, privilege-escalation attempts (denied role or permission changes, access to another account's objects), suspicious or bulk exports, data-access violations, dependency and provider failures, exception-rate spikes per release, and critical service outages. Thresholds start from measured baselines, are recorded with their evidence in `ALERT_THRESHOLDS.md`, and are reviewed after each incident.
- Detection and response objectives (for example time to detect, time to acknowledge) are **measured and owner-approved, never promised** ("fixed in seconds" is not a valid objective).

---

## 13. Audit log and admin log system [admin]

### 13.1 Audit log
- Append-only record of: sign-in and failures, MFA, role/permission changes, admin actions, configuration publish and rollback, data export and deletion, sensitive-record access, impersonation or break-glass, money-like state changes.
- Record: `id`, `timestamp`, actor (id, role, auth method, or the job/service name for automated actions), action, target, redacted before/after diff, authorized reason (required for sensitive actions), `request_id`, `trace_id`, hashed IP/device, result. **Sensitive automated actions** (scheduled deletions, bulk jobs, auto-suspensions, AI-initiated actions) are audited the same way as manual ones (CR-01).
- Searching the audit log is role-scoped; exports are privacy-safe (redacted, time-limited, reason required) and every export and every view of an export is itself audited.
- Tamper-evident (hash chain or write-once storage); no update or delete path in the application. Legal hold overrides retention deletion.

### 13.2 Admin log system
Authorized administrators get:
- Search and filters by service, severity, date range, event, environment, request ID, trace ID, actor and target; trace correlation across services.
- Release-based error comparison; incident detail and affected-service views.
- Alerts with acknowledgement, escalation and resolution history; links to runbooks and rollback information.
- Role-scoped views: support sees only assigned cases with redacted fields; nobody sees secrets.
- Exports are redacted, time-limited, watermarked with the requester, require a reason, and are themselves audited.

---

## 14. Admin governance [admin]

- Private control plane; server-side RBAC (ABAC where ownership or region matters); deny by default; no client-chosen roles; no developer backdoors.
- MFA for all staff; step-up for sensitive actions; short sessions; device and session revocation.
- User, role and permission management with least privilege and separation of duties for sensitive changes.
- Configuration versioning with **draft → validate → test → approve → publish → monitor → rollback**, impact preview for consequential changes, effective dates, and existing records keeping the version they agreed to.
- Feature flags and closed-beta cohorts with kill switches.
- Content and catalogue publishing through the same workflow.
- System health, incident management, audit log and redacted diagnostics (category 13).
- Privacy requests and retention controls (category 24).
- Cost controls, quotas and provider health.
- Release and deployment visibility (current SHA per environment).
- Admin actions use the same domain commands as the product; no raw database editing.
- **Publishing configuration never authorizes a code deployment, a provider message, a real payment, or external publication.**
- Impersonation off by default; if enabled, time-limited, read-only unless approved, fully audited.
- Admin is `noindex`, excluded from sitemaps, never linked publicly.

---

## 15. Analytics and business intelligence

- `TRACKING_PLAN.md`: every event (`object_action`), trigger, typed properties, source, owner, consent category, and the metric it serves. CI checks emitted events against the plan.
- **Server-side events are authoritative** for business outcomes; client events only for interface behaviour.
- `METRICS.md`: each metric with numerator, denominator, source events, time zone, exclusions (test, synthetic, internal, duplicate), freshness and owner. Dashboards show definitions, data freshness and time zone.
- Executive dashboards with drill-down; funnels and cohorts where applicable; product adoption and experience analysis; operational and reliability metrics; infrastructure and provider cost reporting.
- Permission-aware access to sensitive reports; privacy-safe exports with retention.
- No invented revenue, traffic, users, customers, sales or conversion. Consent-aware; no covert tracking; no secondary use of customer data.
- Web: real-user monitoring of Core Web Vitals at p75.

---

## 16. Accessibility (WCAG 2.2 AA)

- Semantic HTML first; ARIA only when needed and correct; correct heading structure and landmarks.
- Visible labels; text error messages linked to fields and summarized.
- Full keyboard operation; visible focus; logical order; no traps; skip link; focus managed on route changes and dialogs.
- Contrast ≥ 4.5:1 text, ≥ 3:1 large text and UI parts.
- Targets at least 24×24 CSS px (WCAG 2.5.8); aim for 44×44 on mobile; mobile keyboards do not hide focused inputs.
- 200% zoom and 400% reflow at 320 px without loss; dynamic text scaling on mobile.
- `prefers-reduced-motion` respected; nothing flashes more than 3 times per second.
- Correct `lang` for the page and mixed-language passages.
- Loading, empty, offline, denied, expired and error states announced via live regions where appropriate.
- Meaningful `alt`; captions and transcripts for media.
- Testing: automated axe on changed screens in CI; recorded manual checks with NVDA, VoiceOver (macOS/iOS) and TalkBack per major module; mobile accessibility verified on real devices. Rendering evidence, not source inspection alone.

---

## 17. Responsive and cross-platform

- Breakpoints 320, 360, 390, 768, 1024, 1280, 1440, 1920 px (adapt to the product); portrait and landscape where relevant.
- Mobile-first, fluid layouts; no horizontal page scroll; long words and translations wrap; tables become cards or scroll within their own container; dialogs and sticky elements fit the viewport.
- Responsive images (`srcset`/`sizes`, AVIF/WebP with fallback, explicit dimensions).
- Browsers: Chromium, Firefox, WebKit via Playwright; real Android Chrome and iOS Safari for release candidates.
- Mobile device matrix (OS versions, at least one low-end Android) in the Product Profile.

---

## 18. Frontend and design system [web, mobile]

- Shared design tokens and component library; no duplicated UI for repeated patterns.
- Every screen handles loading, empty, success, error, offline, permission-denied, session-expired and stale states; never shows success when the backend failed.
- Forms: same validation schema on client and server; input kept on error; double-submit prevented; idempotency keys on create.
- Every screen, route, modal and button listed in `APP_SCREEN_MATRIX.md` with role, permissions, API, states, strings and tests.
- Visual regression snapshots for key screens across breakpoints and themes.

---

## 19. Performance

- Web at p75 on mobile: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1. API, job and device targets come from measured baselines approved by the owner.
- Per-route budgets (JavaScript, CSS, images, requests) enforced in CI with Lighthouse CI or bundle checks.
- Route-level code splitting; lazy loading below the fold; subset fonts with `font-display: swap`.
- Long-cache immutable hashed assets; explicit cache headers; CDN for static content.
- Indexes justified by `EXPLAIN`; no N+1 queries (tested); pagination; timeouts, retries with jitter and circuit breakers on outbound calls.
- Load, soak, stress and spike tests only on disposable environments.

---

## 20. Technical SEO [web, public pages]

Rankings are never guaranteed; this sets the strongest technical foundation.

- **Crawlability and architecture:** public pages server-rendered or pre-rendered; clean, stable, lowercase hyphenated URLs; breadcrumbs; internal linking with descriptive anchors; no orphan public pages.
- **Status codes:** permanent moves 301; removed content 404 or 410; no soft 404s; redirect chains avoided.
- **Metadata:** unique title (about 50–60 characters) and description (about 150–160); canonical on every indexable page; one `<h1>`; Open Graph and Twitter/X cards with a correctly sized image.
- **Multilingual:** reciprocal `hreflang` for each language plus `x-default`; language in the URL path or subdomain, never only a cookie.
- **sitemap.xml** generated automatically from routes and content; only canonical, indexable, 200-status URLs; accurate `lastmod` (omit `priority` and `changefreq`); 50,000 URLs or 50 MB uncompressed per file, index file beyond; separate image/video sitemaps if useful.
- **robots.txt** accurate, references the sitemap, disallows private areas (not a security control).
- **No indexing** of admin, account, search-result, filtered, staging or preview pages (`noindex` plus authentication).
- **Structured data (JSON-LD)** only for what is true and visible: `Organization`, `WebSite`, `BreadcrumbList`, `SoftwareApplication`, `LocalBusiness`/`Service` (real address and area), `Product`/`Offer` (real prices), `Article`, `JobPosting`, `Event`. `AggregateRating`/`Review` only from real, verifiable reviews. FAQ rich results now appear only for some authoritative sites and HowTo results were retired. Never fabricate reviews, ratings, offers, customers or prices.
- **Validation:** Schema.org validator and Google Rich Results Test; CI parses JSON-LD on key pages; CI checks every sitemap URL returns 200, is self-canonical and indexable; a crawler finds broken links and orphan pages.
- **Quality:** original, useful, factual content; image `alt` and compression; Core Web Vitals "good". Clear structure also helps AI-powered search; `llms.txt` is optional with no guaranteed effect.
- Search Console and Bing Webmaster Tools only when the owner provides access.

---

## 21. Localization

- Keyed message catalogs with ICU placeholders and plurals; no hard-coded user-facing text.
- Launch languages per product; 100% coverage of launch-critical screens, emails, notifications and errors; CI fails on missing keys, unused keys or placeholder text.
- Native-speaker review of legal, money, safety and consent text, recorded with reviewer, date and string version; editing a reviewed string resets its review.
- Locale-aware date, time, number, INR and phone formats; canonical UTC storage.
- Language switching never resets work or consent; preference persists across sessions and channels.
- Accessibility of localized content: correct `lang`, font rendering, screen-reader pronunciation, long-string layouts.

---

## 22. Security

- Checklists: OWASP ASVS Level 2, OWASP Top 10, API Security Top 10, Mobile Top 10 (MASVS) where apps exist, and the OWASP Top 10 for LLM Applications where AI is used (category 23).
- **Threat model** per product (`docs/security/THREAT_MODEL.md`) with trust boundaries, data flows and abuse cases; updated when architecture changes.
- **Identity:** one identity/session model; secure cookies or short-lived rotated tokens; MFA and step-up for privileged roles; session and device revocation; recovery without enumeration; rate limits and spend caps on sign-in and OTP.
- **Authorization:** deny by default; object-, field- and function-level checks on every read, write, search, export, file, websocket, job and admin path; tests for every role and cross-account/tenant denial.
- **Multi-tenant isolation** across database, APIs, jobs, caches, search indexes and file storage.
- **Input/output:** schema validation; output encoding; parameterized SQL; CSRF for cookie auth; strict CORS; SSRF protection.
- **Headers:** CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, frame protection.
- **Files:** private storage; short-lived signed URLs after authorization; content-type detection; size limits; malware scanning; metadata stripped from shared images while investigation originals stay in restricted encrypted storage.
- **Webhooks:** signatures, timestamp and replay protection, idempotency.
- **Zero sensitive-data leakage (CR-01).** Automated tests prove that credentials, tokens, OTPs, session data, personal information, private documents, internal configuration and authorization-protected data never appear in:
  - API responses to unauthorized or other-account callers (including error bodies, headers and redirect URLs)
  - browser storage: `localStorage`, `sessionStorage`, IndexedDB, readable (non-`HttpOnly`) cookies, and service-worker caches, inspected after each critical journey
  - client bundles and source maps (built JavaScript scanned for secrets, internal URLs and configuration; production source maps not publicly served)
  - console output, analytics events, traces, telemetry and diagnostic or log exports
  Tests use synthetic secrets and sensitive fixtures and assert their absence. Any finding is at least High severity.
- **Identity without AWS (CR-02):** application-managed authentication (secure sessions, Argon2id password hashing and/or email one-time codes, TOTP MFA for privileged roles) or another approved non-AWS provider.
- **Secrets:** environment or secret manager (non-AWS); never in clients or firmware; rotation runbook (owner executes); app refuses to start without required secrets.
- **Supply chain:** dependency audit (npm audit, pip-audit, osv-scanner); SBOM (CycloneDX); license policy; provenance for build artifacts; secret scanning of tree and full history (gitleaks); SAST (CodeQL or Semgrep); DAST baseline (OWASP ZAP) on staging; Actions pinned to commit SHAs, least-privilege `permissions:`; no secrets to fork runs; no `pull_request_target` executing untrusted code.
- **Containers and infrastructure:** minimal pinned base images, non-root user, image vulnerability scan, no secrets in layers, infrastructure configuration reviewed.
- **Mobile:** no secrets in the app, certificate validation, secure storage, obfuscation where useful, store-policy compliance. **Firmware:** signed images, secure boot where hardware allows, no keys in firmware, safe update rollback.
- **Findings:** each with severity, exploitability, affected data, remediation and retest evidence. Confirmed critical and high block the affected functionality until fixed and independently retested. Findings that predate the current change are in scope.
- **Risk exceptions:** there is no generic waiver. An unresolved exploitable critical vulnerability is never treated as production-ready. Any risk acceptance is recorded in `RISK_EXCEPTIONS.md` with: severity, exploitation conditions, affected data, an independent security assessment, compensating controls, expiry date, re-evaluation date, compliance confirmation, and the owner's signed decision. An exception never substitutes for legal or regulatory compliance. Agents cannot create or approve exceptions.
- Incident runbooks (unauthorized access, data leak, compromised credential, fraud), including legal reporting duties confirmed by legal review.
- `SECURITY.md` with a responsible-disclosure contact.

---

## 23. AI and LLM security [ai]

- Follow the OWASP Top 10 for LLM Applications.
- **Prompt injection:** treat all user content, retrieved documents, web pages, emails and tool outputs as untrusted data, never as instructions; separate system instructions from data; test with injection fixtures.
- **Tool authorization:** every tool an AI can call enforces the same server-side permissions as the user it acts for; consequential actions (send, pay, delete, publish, book) need explicit user confirmation; no autonomous privilege escalation.
- **Output handling:** model output is validated and encoded before rendering, executing or storing; never executed as code or SQL without strict checks.
- **Data handling:** minimal personal data sent to models; provider data-retention and training settings documented; no customer data used for training without explicit opt-in; redaction before logging prompts and responses.
- **Spend controls:** per-user, per-tenant and global token and cost caps; rate limits; alerts on spikes; model and provider keys only on the server.
- **Quality and safety:** evaluation sets for key tasks, regression-tested in CI; disclosure that users are interacting with AI; human review for high-impact outputs.

---

## 24. Privacy (India first)

- Digital Personal Data Protection Act 2023 and its Rules, as confirmed by legal review per product.
- `DATA_INVENTORY.md`: every personal data field with purpose, lawful basis, retention, location and processors.
- Clear consent where consent is the basis; easy withdrawal; notices in the user's language.
- Rights: access, correction, export, deletion across database, object storage, caches, search indexes, backups (by expiry) and processors; restoring a backup re-applies later deletions.
- Retention schedule with automatic deletion; legal hold overrides deletion.
- TLS 1.2+ in transit; encryption at rest; encrypted, restore-tested backups.
- No sale of data; no AI training on customer data without opt-in; processor list maintained.
- No sensitive data leaking into logs or analytics (tested).
- Children: products not designed for children say so; anything involving minors needs separate legal review.
- Fixtures use synthetic people, reserved test phone ranges and fictitious addresses.

---

## 25. Testing automation

### 25.1 Mandatory suites (as applicable)
| Suite | Proves | Typical tools |
|---|---|---|
| Unit | Functions and rules, edge and error cases | Vitest/Jest, pytest, JUnit, Unity |
| Component | UI in all states | Testing Library, Compose UI tests |
| Property-based | Rules hold for generated inputs | fast-check, Hypothesis |
| Integration | Real database, queue, cache in containers | Testcontainers |
| API contract | Requests/responses match OpenAPI; compatibility | Supertest, schemathesis, Pact |
| Authorization | Every role allowed/denied on every endpoint | Generated matrix |
| Concurrency | Races, duplicates, idempotency across real workers | Parallel workers, real DB |
| Migration | Upgrade, parity, rollback where feasible | Disposable DB |
| **Smoke** | Build alive: starts, health OK, home loads, sign-in, one key action | `@smoke` |
| **Sanity** | A specific change works and neighbours are intact | `@sanity` |
| **Critical path** | Business-essential journeys end to end | `@critical` |
| **Regression** | Prior behaviour intact; changed-area per module, full nightly and pre-release | `@regression` |
| End-to-end | Real journeys in real browsers or devices | Playwright, Maestro/Espresso/XCUITest |
| Cross-browser | Chromium, Firefox, WebKit | Playwright projects |
| Responsive and visual regression | Layouts and approved snapshots | Playwright screenshots |
| Accessibility | Automated plus manual | axe-core, screen readers |
| Localization | Each language, long strings, switching mid-flow | Playwright locales |
| Performance, load, soak, stress, spike | Latency, capacity, leaks | k6, Lighthouse CI |
| Fault injection and resilience | Failure of DB, cache, worker, provider, network; recovery | Disposable environment |
| Security | SAST, DAST, dependencies, secrets, abuse cases | Category 22 tools |
| Mutation | Tests catch real bugs in critical domains | Stryker, mutmut, Pitest |
| Backup/restore | Restore works and data is correct | Scheduled drill |
| Mobile device | Install, permissions, lifecycle, offline, deep links, notifications, upgrade | Real devices |
| Firmware / hardware-in-the-loop | Firmware on real boards | Product rig |
| AI evaluation [ai] | Task quality, injection resistance, cost | Eval sets |
| Exploratory, beta, field UAT | Humans try to break it; real users accept it | Owner-arranged |

### 25.2 Per-feature scenarios
Success; invalid, malformed and boundary input; unauthorized and cross-account access; duplicate submission and concurrency; network failure, timeout and cancellation; database or provider failure; stale state, session expiry and re-authentication; recovery, retry, compensation and rollback; accessibility and each language; privacy, logging and analytics correctness.

### 25.3 Rules
- Real tools only; mocks never reported as real provider, device or production evidence; no suite named Playwright unless it runs Playwright.
- Tags (`@smoke`, `@sanity`, `@critical`, `@regression`, module) drive CI selection.
- `TEST_MATRIX.md` maps every requirement to tests: test ID, requirement, screen/journey, role, locale, channel, environment, scenario, expected result, command, run ID, SHA, result, failure artifacts.
- Coverage on changed code ≥ 80% lines and 70% branches; 100% branches on authorization, money and core state machines; mutation score tracked for critical domains. Coverage is necessary, not sufficient.
- Flaky: at most two retries; retry-only passes reported FLAKY and fixed by root cause.
- Deterministic factory data; no order or wall-clock dependence; no real personal data.
- Defects close only after reproduction, root cause, fix, regression test, related suites, definition of done, independent review and evidence.

### 25.4 Browser runtime gate [web] (CR-01)
- Every Playwright journey uses a shared fixture that records console messages (`error` and `warning`), `pageerror` (uncaught exceptions), unhandled promise rejections, hydration errors, failed requests (`requestfailed`), and unsuccessful HTTP responses on critical requests.
- The test **fails on any unexpected finding**. Expected messages and responses (for example a deliberate 401 in a denial test, or a 404 on a not-found page) are listed in `EXPECTED_RUNTIME_MESSAGES.md` with exact pattern, journey, reason, owner and review date; no broad wildcards. Expected responses get their own explicit tests.
- React and framework warnings appear only in development builds, so launch-critical journeys run against **both** a development build (warnings, hydration) and the production build (errors, network failures).
- Third-party script noise is not ignored silently: it is either removed, fixed or listed in the allowlist with a reason.
- Mobile [mobile]: device-log capture (logcat, Xcode console) during device test runs, checked for crashes, uncaught exceptions and sensitive data.

---

## 26. Functional verification

Before a module is done and before every release candidate:
1. Inventories: `FEATURE_MATRIX.md`, `APP_SCREEN_MATRIX.md`, OpenAPI endpoints, `JOURNEY_MATRIX.md`, domain commands, jobs, notifications, admin configurations and flags.
2. Every link and button: a crawler finds broken links, dead buttons, and buttons that report success without a real backend result.
3. Every form: valid, invalid, empty, too long, special characters, each language, double submit, slow network.
4. Every endpoint and command: success, validation failure, unauthorized, forbidden, not found, conflict, rate limit.
5. Every role: its full journey list, then every other role's actions to confirm denial.
6. Every state transition and screen state, including errors and recovery.
7. Every integration: success, timeout, error, duplicate and delayed callbacks with mocks; with the real provider only after owner approval.
8. Every admin action and flag: effect, audit record, rollback.
9. Every deployment and recovery procedure rehearsed on staging.
10. **Manual runtime review (CR-01):** during each major module audit and each release-candidate test, a tester walks the launch-critical journeys with browser DevTools open (Console, Network, Application/Storage) on each supported browser, and reviews device logs on supported mobile devices. Record tester, environment, browser or device, SHA and findings in `QUALITY_AUDIT.md`; every unexpected finding becomes a defect (category 11).
Results recorded with evidence and denominators; anything failing becomes a defect or blocker.

---

## 27. CI/CD

### 27.1 Trigger matrix
| Trigger | Required validation |
|---|---|
| Push / task branch | Format, lint, type check, unused-code and circular-dependency analysis, unit tests, dependency and secret scans, build, docs validators, agent-file artifact check |
| Development integration | Above plus API/integration with real DB, contract, authorization and tenancy, migrations, concurrency if touched, `@smoke`, `@sanity`, `@critical` E2E with the browser runtime gate (25.4), sensitive-data leakage tests, client-bundle secret scan, changed-area regression, accessibility/responsive/localization on changed screens, coverage, performance budget, SEO checks on public pages |
| Major feature completion | Complete feature matrix for the area, accessibility (manual record), responsive, all browsers, security review |
| Nightly | Full regression on all browsers and languages, security scans including history, resilience, mutation on critical domains, dependency checks, link crawler |
| Manual (`workflow_dispatch`) | Allowlisted suite, module, browser and environment (ephemeral or approved staging); each selector runs a real command |
| Pre-staging | Artifact integrity and provenance, migration dry run, secrets and permissions check, backup verified |
| Post-staging | Health, smoke, sanity, critical, alerts and logging flowing, privacy checks, provider sandbox flows, ZAP baseline |
| Production | Owner-only manual deployment from protected `main` with approvals, backup, health checks and rollback |

### 27.2 Release protections proven with real safe runs
A failing test, missing translation, secret finding, unsafe migration, unexpected browser runtime error, sensitive-data leak, or missing mandatory suite each blocks promotion (skipped counts as failed via a summary job); artifacts and traces carry the exact SHA; production cannot run from another branch (proven by configuration review and a guard test, never by an agent dispatching production); production secrets are unavailable to untrusted pull requests and ordinary test jobs. Negative fixtures run on temporary branches and are removed. A workflow file is not evidence.

### 27.3 Practicalities
Least-privilege workflow permissions; pinned actions; caching for speed; concurrency groups to cancel superseded runs; Actions-minute shortfalls recorded as blockers, never solved by skipping suites.

---

## 28. Deployment, reliability and disaster recovery

- Reproducible builds with immutable artifact identity, provenance and the exact tested SHA.
- Infrastructure as code or documented reproducible deployment configuration where appropriate. Host-specific rules (for example Hostinger) apply only to products actually deployed there.
- Protected deployment environments; migration preflight and compatibility checks (expand-and-contract for zero-downtime changes).
- Graceful shutdown and worker drain; health, readiness and synthetic checks.
- Automated encrypted backups with independent off-host copies; corruption detection; scheduled restore drills with recorded results.
- Recovery time and recovery point objectives (RTO/RPO) proposed from measurements and approved by the owner.
- Feature rollback (flags) and application rollback (previous artifact) both rehearsed; database changes designed so app rollback is safe.
- Runbooks: deploy and rollback, incident response, secret and certificate rotation, provider outage, queue replay and data reconciliation, backup restore, data subject requests.
- Capacity planning, resource limits and cost limits; monitoring independent of the primary host (category 12).
- Staging is a separate host with synthetic data, authentication and `noindex`. Destructive, load or chaos tests never run on shared or production hosts.

---

## 29. Documentation and GitHub maintenance

### 29.1 Documentation set
README (setup in under 10 minutes, troubleshooting); product overview and approved requirements; roadmap; architecture with **C4 context, container and component diagrams**; **ERD** and data-flow diagrams; **sequence diagrams** for key journeys; **state machines** for lifecycles; threat model and trust boundaries; API contracts and version policy; `CONFIG_REFERENCE.md`; deployment, backup, recovery and incident runbooks; security and privacy architecture; accessibility and localization guides; test strategy and `TEST_MATRIX.md`; feature, screen and journey inventories; CI/CD diagram and branch governance; ADRs; `CHANGELOG.md` and release notes; dependency inventory and SBOM; cost model; known limitations; operational ownership; `PROGRESS.md`, `GAP_MATRIX.md`, `QUALITY_AUDIT.md`, `CHANGE_REGISTER.md`, `blocker.txt`; `docs/PRODUCT_PROFILE.md`.

Diagrams in **Mermaid** (or another text format), syntax-validated in CI (for example with mermaid-cli), and updated in the same change that alters the architecture. Update canonical documents; never create contradictory duplicates. Documents never contain repository names or repository links (CR-02).

### 29.2 GitHub professionalism
`CONTRIBUTING.md`; `CODEOWNERS`; `SECURITY.md`; issue templates; PR template only where PRs are used (not by agents in autonomous mode); Dependabot or Renovate update policy; labels; release tags with notes; signed or verified commits where configured; `.gitattributes` and complete `.gitignore`. **Branch protection, required checks, environments and secrets are repository settings changed only by the owner**; the agent prepares the exact recommended settings as READY_FOR_OWNER. Never rewrite history or delete needed evidence to make a repository look clean.

---

## 30. Definition of done, release readiness and reporting

### 30.1 Definition of done (per change)
1. Type check — zero errors
2. Lint and format — zero errors, zero new warnings
3. Unused-code, complexity, duplication and architecture (boundary, circular-dependency) checks — zero new violations
4. Unit and component tests pass; coverage thresholds met
5. Integration, contract and authorization tests with real dependencies pass
6. `@smoke`, area `@sanity` and `@critical` pass in every launch language
7. Accessibility, responsive and localization checks on changed screens pass
8. Security scans: no high or critical findings without a fix or a valid recorded exception (category 22); no secrets
9. Logging schema and redaction tests pass; audit events for sensitive actions
10. Analytics events exist in the tracking plan
11. SEO checks pass for changed public pages
12. Browser runtime gate (25.4) passes on affected journeys: no unexpected console errors, page errors, rejections, hydration errors or critical network failures; leakage tests pass
13. Performance budget met
14. Build succeeds; no agent files in the artifact
15. Documentation, diagrams and matrices updated
16. Independent review done or labelled pending
17. `TEST_MATRIX.md`, `PROGRESS.md` and `CHANGE_REGISTER.md` updated with commands, run IDs, SHA and results

### 30.2 Release readiness
All product launch gates satisfied with evidence; full regression green on the release SHA; **no launch-critical feature marked PASS while it has an unresolved reproducible runtime error, unhandled exception, unauthorized data exposure or unexplained critical network failure** (CR-01); manual runtime review recorded; security, privacy, accessibility and localization sign-offs; performance measured against approved targets; backup, restore and rollback rehearsed; monitoring and alerts live; legal pages published; analytics verified on staging; sitemap and structured data validated; provider and app-store approvals where needed; field acceptance where required; owner GO recorded. Missing any applicable item = NO GO.

### 30.3 Reporting per product
Scope denominator and completion; code quality and hygiene; security findings and remediation; accessibility and responsive verification; SEO where applicable; test inventory, executed results and coverage; journey completion; provider permissions and external dependencies; infrastructure and operational readiness; CI run IDs and release SHA; deployment and rollback evidence; documentation completeness; beta and field evidence; outstanding owner actions; PASS, FAIL, BLOCKED or NOT_ASSESSED per category and per product gate. A planning document or a green test summary never substitutes for demonstrated readiness.

---

### 30.4 Repository-wide completion
Per-change rules (30.1) keep quality from getting worse. A repository is complete only when, in addition, every pre-existing finding has been inventoried and resolved or formally dispositioned with evidence (7.4), and every applicable category is VERIFIED (2.5).

## Appendix A — Product Profile (`docs/PRODUCT_PROFILE.md`)

| Field | Value |
|---|---|
| Product, default and integration branches (repository verified by the agent but never named in documents, CR-02) | |
| Scope status (draft, approved, frozen) and governing documents | |
| Activation status (ACTIVE with recorded approval reference, or AWAITING_OWNER_APPROVAL) | |
| Approved Git workflow for this repository | |
| Surfaces: web, admin, API, Android, iOS, WhatsApp, device, AI | |
| Stack per surface | |
| Hosting and deployment target | |
| Launch languages | |
| Roles | |
| Public pages needing SEO; schema types | |
| Data classes and sensitive data | |
| Providers and approval status | |
| Supported browsers, OS versions, device matrix | |
| Performance, RTO and RPO targets (measured, owner-approved) | |
| Thresholds stricter than this standard | |
| Categories NOT_APPLICABLE_WITH_REASON | |
| Owner exceptions (decision IDs) | |

## Appendix B — Portfolio adoption matrix (`PORTFOLIO_ADOPTION_MATRIX.md`)

One row per category (1–30) and one column per product. Each cell: status (NOT_ASSESSED, NOT_APPLICABLE_WITH_REASON, PLANNED, IMPLEMENTED, TESTED, VERIFIED, BLOCKED, READY_FOR_OWNER), evidence link, SHA and date. A product's cells are never updated from another product's evidence.

| # | Category | OraOne | CareerScope | FixHub | AI smart glasses |
|---|---|---|---|---|---|
| 1 | Non-negotiables and authority | NOT_ASSESSED | NOT_ASSESSED | NOT_ASSESSED | NOT_ASSESSED |
| … | … | … | … | … | … |
| 30 | Definition of done, release readiness and reporting | NOT_ASSESSED | NOT_ASSESSED | NOT_ASSESSED | NOT_ASSESSED |

## Appendix C — Relationship to existing product documents

| Product | Product documents keep authority for | Notes |
|---|---|---|
| OraOne (v2.1) | Scope, FastAPI/React stack, Hostinger deploy, D01–D20 | Hostinger rules apply here |
| CareerScope (v12) | Scope, D1–D14, proposed stack | Fill the Product Profile before the stack is approved |
| FixHub (v1.3, frozen) | Scope, QA-01–QA-34, G01–G25, D01–D27 | Gaps needing new features go to READY_FOR_OWNER, not into the build |
| AI smart glasses (v9) | Profiles, broker, evidence levels, P-1 schedule | Categories 20 and 15 web parts apply only to its public site; 22 mobile/firmware and 23 AI apply |
