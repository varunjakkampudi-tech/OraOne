# OraOne OS — Master Product Specification v2.1

Status: Owner-requested complete-product target; PROPOSED for formal approval, not a report of implemented or deployed features.
Product: OraOne OS — One AI. Every Conversation.
Domain: oraone.in
Reference baseline: existing OraOne Product Specification v1.1, Engineering Standards and L0 Goal, inspected 19 October 2026. v2.1 keeps all v2.0 requirements and carries forward the repository-grounded rules from v1.1 (Appendix A).
Scope decision: This revision supersedes v1.1's limitation to Product 1 and a future-only OS for internal development planning. Its objective is the complete integrated OraOne OS, not a chat-first product. It does not assert any unverified integration is available or authorize unlawful contact, purchases or production deployment.
## Changes in v2.1

| # | Change | Where |
|---|---|---|
| C1 | Markdown formatting for tables and headings | Whole document |
| C2 | v1.1 repository facts and rules R1 to R7 carried forward (lead temperature default, VisitorProfile identity and memory, two lead-status fields, USD default, planned-product stubs) | Appendix A.1 |
| C3 | v1.1 status-versus-workflow reconciliation and additive status migration carried forward | Appendix A.2 |
| C4 | v1.1 metric dictionary carried forward and extended to channels | Appendix A.3 |
| C5 | Build-order rule: shared foundations before channel modules | Section 8.1 |
| C6 | Gate-to-release map so gates outside the target release are NOT_DUE, not failed | Section 9.1 |
| C7 | India telecom and messaging detail to verify (DLT registration, number series, DND scrubbing) | Section 7 |
| C8 | Voice media architecture rule (media off the application VPS) | Section 4.4 |
| C9 | Unified decision register: v2 D01 to D14 kept; v1.1 decisions still needed added as D15 to D20 with a mapping | Section 13, Appendix A.5 |
| C10 | Legacy-code inventory rule for duplicate and prototype routes | Section 1 |

---

## 0. Mission, positioning and non-negotiables
Mission: Help businesses acquire permissioned leads, converse across approved channels, qualify and serve customers, schedule next steps, run auditable campaigns, automate work, measure outcomes, and grow—all in one secure, human-supervised AI operating workspace.

Product metaphor: OS means a unified SaaS application and extensible business operating layer, not a device operating system. Lead/Customer 360 and the Omnichannel Inbox are shared foundations, not duplicates in each module.

Principles in priority order: Safety and lawful permissions; privacy and tenant isolation; truthful claims and evidence; reliability; operator control; accessible premium UX; useful AI; composable automation; performance and cost control. No customer data is used to train foundation models by default, sold, or exposed across tenants. Service processing requires a lawful basis, disclosed processors and contractual safeguards; "we don't use customer data" means no secondary use, not that a functional system never processes it.

Target: Agencies, sales/support teams, small-to-mid businesses, multi-location operations, with potential enterprise tier. Support opt-in customers in different jurisdictions only after validating applicability of communications, privacy and consumer protection rules.

Public truth: Every marketed feature must have one of: AVAILABLE (fully verified in production), BETA (authorized participants only), WAITLIST/PLANNED, or UNAVAILABLE. Do not claim WhatsApp, Instagram, calling, publishing, conversion figures, security certifications, testimonials, customer logos, price, uptime or integration functionality without evidence.
## 1. Repository and platform baseline
As observed in the October 19 repository review, source includes React/Vite/Tailwind frontend, FastAPI/Pydantic/SQLAlchemy backend, PostgreSQL/pgvector, Redis, S3-compatible/MinIO storage (non-AWS), Caddy/Docker, Cognito-oriented auth (to be replaced; no AWS, see Amendment 2026-10-20), role/org/project scoping, AI chat/knowledge/widget, lead CRUD and assignment, usage/billing primitives, workers/outbox, and several planned-product route/model stubs. .github/workflows/ includes application checks, frontend lint, and deploy-hostinger.yml. These are code-level observations, not live-provider or production certifications. Reaudit at an exact SHA before implementation. Preserve migrations and useful existing capabilities; never reset to a new template.

Legacy-code rule: the repository contains prototype and duplicate routes (for example `api/v2`, `omnichannel`, `channels`, `marketplace`, `workflows`, `workspace_intel`). Each is classified as working, disabled, planned, duplicate, or broken in the baseline audit before any module builds on it. Prototype code may be reused only after it passes the same tests as new code. Specific repository facts and rules from v1.1 remain in force (Appendix A.1).

Existing portfolio labels (Product 1 Chat, Product 2 Voice, Product 3 WhatsApp, Product 4 Omnichannel, Product 5 Workflow, Product 6 Studio, Product 7 Marketplace, Product 8 Mobile, Product 9 Enterprise, Product 10 OS) are consolidated as modules under one OraOne OS in this proposed target. Maintain migration-compatible IDs and distinguish repository code, local tests, externally verified integrations, and live availability.
## 2. Unified end-to-end journeys (contract)
1. Business signs up → verified tenant/org/project → securely onboards → installs website script → validates domain/CSP → runs an approved AI widget and captures a consented lead.
2. Connect approved WhatsApp Business account → verify webhooks and templates → consented customer contacts business → AI or human handles in shared inbox → outcome appears in Lead 360.
3. Connect approved Instagram professional account → customer initiates interaction → permitted direct message/comment workflow → authorized handoff → Lead 360.
4. Customer uploads XLSX/CSV → validation, preview, duplicate matching, consent proof and destination eligibility → rejected/ineligible rows quarantined → approved calling campaign → monitored calls with opt-out, transfer, callback, dispositions and spend caps.
5. Qualified lead → assignment → shared conversation context → appointment/quote/proposal → human-confirmed outcome → reliable analytics.
6. Authorized operator builds an automation with typed triggers/conditions/actions → dry run/test → approval → scheduled versioned activation → monitoring → reversible pause/rollback.
7. Marketplace creator submits reviewed template/integration → sandbox and security validation → administrator publishes signed/versioned listing → tenant installs with explicit permissions.
8. Admin edits provider/feature/model/campaign configuration → validated draft → test/staging → review/approval → explicit publish to an allowed environment → audit/rollback.
9. Controlled beta cohort receives a feature → metrics/error tracking and kill switch → staged expansion or rollback without exposing others.
10. Owner starts manual GitHub production workflow on protected main → hard quality gates + approval → artifact deploy to Hostinger → smoke/sanity/critical tests → monitor/rollback on failure.
11. User reports an error → trace/correlation ID → redacted log access → alert/diagnostic record → fix with tests → authorized release; never promise a guaranteed fix in seconds.
12. Privacy request → identity verification → data export/deletion/suppression propagation through DB, object storage, search and provider processors, subject to documented legal retention.
## 3. Core shared OS services

| ID | Module | Mandatory product behavior |
|---|---|---|
| OS-01 | Identity, tenancy, permissions | Application-managed identity with no Cognito or other AWS service (Amendment 2026-10-20, D21); tenant/project/field-level authorization; MFA/step-up for privileged operations; invitations; sessions/revocation; scoped API keys and audit trails |
| OS-02 | Customer/Lead 360 | Canonical tenant-scoped contact, company, lead, opportunity, conversations, lawful provenance, consent, assignments, notes, follow-ups, appointments, deals, history and imports/exports |
| OS-03 | Omnichannel Inbox | Single customer timeline with channel/source provenance, identity reconciliation requiring evidence, agent/human handoff, queue, assignment, collaboration, SLAs, human override, suppression, no duplicate sends |
| OS-04 | Policy and consent engine | Per-tenant/channel/purpose/destination jurisdiction, evidence of opt-in/lawful basis, templates/window rules, DND/suppression, recording choices, revocation, quiet hours; checked immediately before send/dial |
| OS-05 | Event/workflow platform | Durable outbox, event schemas, idempotency, retry/DLQ, immutable workflow versions, pause/resume, test mode and audit |
| OS-06 | AI gateway and knowledge | Multi-model router, tenant-isolated RAG with cited sources, prompt injection defenses, grounded replies, latency and quotas, durable cost reservation and reconciliation, evaluation datasets |
| OS-07 | Analytics | Verified raw events, definitions, funnel/cohort/source views, attribution caveats, revenue and cost only from authenticated outcomes, privacy-safe exports and reporting |
| OS-08 | Admin and governance | Separate platform super-admin and tenant owner; drafts, validation, maker/checker on sensitive config, publish, rollback, audits, support and privacy requests |
| OS-09 | Integration catalog | Official provider OAuth/token vault, least scopes, signed webhooks, health/expiry, data scopes, revocation, quotas, sandbox fixtures and versioned connectors |
| OS-10 | Operations | Health, structured redacted logs, metrics/traces, alerting, backup/restore, billing, metering, per-tenant feature flags, region-aware retention, support tooling |

## 4. All product modules — full target requirements
### 4.1 Website AI and embeddable script (OS-WEB)
- One documented versioned <script> installation with tenant/site identifier; domain allowlisting, CSP guidance, integrity/compatibility measures, graceful async loading, framework independence and no host-site CSS collisions.
- Accessible branded responsive widget; consent-aware lead collection, voice option only if permitted, streaming grounded knowledge answers, form validation, human handoff, offline/out-of-hours notices, conversation transcript controls and session privacy.
- Widget analytics use a consented, clearly scoped measurement model. No covert tracking, fingerprinting or unsupported attribution.
- SDK loader performance budget, upgrade/rollback and browser compatibility required. Site-builder adapters can be added after validation.
### 4.2 WhatsApp Business Platform (OS-WA)
- Connect only through official authorized WhatsApp Business Platform/Cloud API or contracted compliant BSP. Validate business verification, account ownership, supported access levels, webhook subscriptions, messaging windows, approved templates, sender display, opt-in, opt-out, rate limits, quality and country-specific rules.
- Two-way text, supported media, template messaging, allowed interactive messages, routing, agent assignment, AI replies with disclosure and human takeover, approved campaign segmentation.
- Delivery state must distinguish accepted, sent, delivered, read (when available), failed, blocked; webhook reconciliation and retries idempotent. Templates and policies versioned; no browser automation or unofficial WhatsApp Web scraping.
- Admin connect/disconnect, token rotation, template approval status, message costs, quality warnings, suppression and kill switch.
### 4.3 Instagram and social messaging (OS-IG)
- Official Instagram API for eligible professional accounts with correct Meta app review, permissions and token ownership; customer-initiated DM/messaging windows, supported comments/mentions and media only as permitted by granted capabilities.
- Shared inbox, FAQ suggestions, handoff, label/source, lead capture only with lawful permission. No arbitrary unsolicited DMs, password collection, scraping, simulated engagement, bot farms or unsupported personal-account APIs.
- Disclose restrictions and monitor permission expiry, webhook failures and Meta policy changes. Marketing publishing is a separate future gate.
### 4.4 Humanlike AI Voice Platform and calling (OS-VOICE)
- Natural conversational speech with latency-budgeted STT, TTS, streaming/barge-in, interruption, multiple languages and accents subject to evaluation; bounded prompts, quality and fallback to a human agent.
- Inbound calls, IVR, transferred calls, callbacks, business-hour routing, dispositions and appointments; outbound call scheduling and approved campaigns. Accurate caller ID, AI-identity disclosure, recording notice/consent where required; emergency calls and deceptive impersonation prohibited.
- Media architecture: real-time call audio runs through the telephony provider's media streaming and a separately scalable voice service, not through the main application process on the Hostinger VPS. Latency, concurrency, and cost budgets are set from measurement before any campaign is enabled.
- Excel/CSV import: secure upload, antivirus/type/size/row checks, normalized E.164 phones, duplicate/invalid row preview, per-recipient consent provenance, purpose, source, suppression/DND/opt-out checks, campaign bounds, human approval, legal/provider readiness, dry-run and caps; only eligible recipients enter dial queue. Imported phone numbers do not grant calling consent.
- Explicitly prohibit "call every uploaded number" unless independently eligible. Reject or quarantine unproven contacts and never automatically bypass DND or jurisdiction/provider requirements. Avoid unsolicited bulk commercial calls; all campaigns must comply with applicable telecom registration and authorized routes (including India's TRAI/TCCCPR framework where relevant).
- Dialer queue: rate/concurrency controls, time-zone/business-hour rules, per-destination/max-attempt caps, no-answer/busy/error retries, fraud/spend circuit breaker, opt-out during call, transcript redaction, retention controls, call review with permission, human handoff, cost/reconciliation and emergency stop. No fabricated reach, booking or lead conversion.
- Select provider only after region coverage, Indian telecom compliance, pricing, outbound AI calling acceptance, reliability and legal review. Live calling blocked until provider permission, test numbers and owner approval.
### 4.5 Omnichannel Communication Hub (OS-OMNI)
- Channel adapter contract for website, WhatsApp, Instagram, voice, permitted email/SMS and future channels. Canonical message envelope with channel IDs, direction, external message ID, delivery events, attachments, channel capabilities, sender identity, consent and audit.
- Thread stitching uses verifiable identities and reversible linking; never join users from guesswork or across tenants. Stateful handoff preserves context without exposing internal notes.
- User inbox, unified search, filters, assignments, queues, SLA timers, canned responses, conflict prevention, channel availability and outage states. Replies only through provider-authorized windows and policies.
### 4.6 Lead OS, customer management and sales (OS-CRM)
- CRM must be end-to-end, not a form list: account/contact lead passport, lead intake/qualification, pipeline and opportunity stages, ownership, priorities, tasks/reminders, meetings, quotes/proposals (where integrated), customer lifecycle, integrations, export and controlled retention.
- Rules and explainable AI scoring; proactive No Lead Left Behind queue; next-best-permitted-action suggestions; decision memory with source evidence; pipeline analytics; lost reason; stage audit; dedup merge/split reversible and tenant-isolated.
- Imported contacts remain noncontactable until the consent engine confirms permitted use. Don't score or infer protected characteristics and don't assert sales conversions without trusted events.
### 4.7 Workflow Automation Platform (OS-FLOW)
- Visual builder and advanced typed editor for versioned workflow definitions: trigger, condition, schedule, wait, branching, loops with bounds, approval gate, retry, compensation, webhook/API call and human task.
- Template library, test payloads, dry-run sandbox, simulation, logs and traces, idempotency, concurrency, rate/cost budget, stuck-run alerts, DLQ, manual resume/replay with duplication protection.
- Every side-effect rechecks RBAC, connector scope, recipient consent and suppression, spend cap and kill switches at action time. No AI-produced workflow or prompt independently grants authorization.
### 4.8 Integrations (OS-INT)
- Prioritize official supported CRM, calendar, email, commerce, forms, payments, social and webhooks by verified customer need; provide integration directory, OAuth/setup, permissions, mapping, sync states, webhook retries, conflict-resolution, secret rotation and disconnect/deletion.
- Document provider quotas, pricing, app review, test accounts, terms, rights to process and redistribute data, and region. Connectors remain NOT_AVAILABLE if rights are unverified. No guessed live integrations.
### 4.9 Marketplace and AI Studio (OS-MKT / OS-STUDIO)
- Marketplace for vetted agent templates, workflows, knowledge bundles and approved connectors. Listing states draft → review → approved → beta → published → suspended/retired, supported versions, install/remove, permission manifest, pricing/entitlements and provenance.
- AI Studio: prompt and agent builder, retrieval configuration, test lab, evaluation datasets, deployment versions, allowed tool schemas, preview/sandbox, quotas, approvals, rollback, per-tenant agent isolation, human handoff.
- Marketplace supply-chain scanning, licensing/IP checks, security sandbox, moderation, false claim review, reporting, abuse response. Publishing requires explicit authorized admin action, not mere configuration save.
### 4.10 Analytics and intelligence (OS-ANALYTICS)
- Product analytics: acquisition and channel source, conversations, first response, delivered/read where provider supplies, drop-off, qualified leads, conversions, appointment attendance, agent performance, SLA, campaign contactability, outcomes, AI quality, voice completion, churn/retention, revenue/cost margins and cohorts.
- Executive dashboard, drill-down funnels, near-real-time operations board, exports, scheduled reports and anomaly detection; each metric shows numerator/denominator, time zone, filters, source confidence, missing data and provenance.
- No silent customer surveillance or training, no fabricated ROAS or performance metrics; data minimization, retention and aggregated reporting.
### 4.11 Billing, plans and subscriptions (OS-BILL)
- Tenant subscription management, trial and entitlements, transparent billing and usage, invoices, tax handling per chosen market, provider pass-through unit economics, reserved/prepaid spend caps, metered features, webhook reconciliation and refunds/cancellations.
- Stripe sandbox currently observed; other processors, INR billing, GST and actual prices need regional and financial approval. Hard caps protect from uncontrolled voice/AI spend.
### 4.12 Beta, feature flags and safe experiments (OS-BETA)
- Flags for tenant, role, user and environment with consistent assignment, cohort eligibility, start/end, exposure audit, dependency checks and kill switch. Beta users opt in, get disclosures and simple exit/feedback.
- Shadow/read-only evaluation before action automation; staged rollout: internal → closed beta → limited production → general availability, with specified error/quality/abuse budgets and rollback.
- No beta can bypass privacy, security, approval, calling rights, data isolation or mandatory tests. Production beta is still a production deployment requiring owner approval.
### 4.13 Admin control plane and publishing (OS-ADMIN)
- Separate platform super-admin, tenant admin, operations/support and end-user roles; deny-by-default field/record/action checks and MFA/step-up for sensitive operations.
- Versioned configuration with DRAFT → VALIDATED → STAGING_TESTED → APPROVAL_PENDING → PUBLISHED and ROLLED_BACK/REJECTED, audit actor/time/diff/affected tenants, schema validation, impact preview, two-person approval for sensitive changes, dry run, rollback. Config publication is not permission to deploy new backend code, change DNS, publish social posts or bypass feature gates.
- Central administration of approved providers, channels, templates, AI models, budgets, feature flags, knowledge sources, branding, roles and permissions, rate limits, tenant lifecycle, data requests, integrations, workflows, app notices, incident kill switches and system notices.
- Tenant administrators publish only tenant-scoped approved configs; global settings and credentials belong to platform owners. No arbitrary raw code, scripts or shell commands from admin panels.
### 4.14 Observability, support and incident response (OS-OPS)
- Structured JSON logs with request ID/trace ID, tenant pseudonymous identifier, release SHA, route, timings, severity and error fingerprint; metrics, tracing, alerting, health, exception aggregation and correlation from UI errors to backend/worker/provider.
- Admin may search and download authorized, redacted, range-limited logs with RBAC, purpose, signed short-lived export links, rate/size limits, export audit and retention. No raw personal info, payment data, call recordings, API keys, chat prompts or secrets in general-purpose logs.
- Incident dashboard: impact/severity, affected tenant(s), first/last seen, dependency failures, runbook, on-call alert, mitigation flag, release provenance, rollback, ticket and postmortem. Target fast detection and triage with measured SLOs; never guarantee every issue can be corrected within seconds.
- Independent alert path from primary Hostinger VPS, graceful service degradation, offline/worker queue visibility, backups and restore drills, data integrity verification and synthetic health checks.
### 4.15 Marketing Studio (future, OS-GROWTH)
- Approved future integration for business-controlled YouTube and Instagram accounts: OAuth permissions, campaign calendar, creative brief, assets, human approval, scheduled posting through officially permitted APIs, content rights/licenses, attribution, quotas, analytics and rollback/unpublish where APIs support it.
- AI may draft copy, captions, video scripts, thumbnails and variants as reviewable drafts, never auto-publish without configured authorization. Avoid fabricated testimonials, misleading claims, repetitive spam, fake followers, automated comments or unauthorized scraping.
- Paid ads and ad-account campaign management are separate future capabilities requiring permissions, spend limits and compliance review.
### 4.16 Mobile, enterprise and extensibility (OS-EXT)
- Future mobile operator companion, notifications with privacy controls, offline-safe read caching; parity with important inbox and lead flows but no blanket background access.
- Enterprise: SSO/SCIM where approved, granular RBAC/ABAC, tenant-controlled data region and retention, audit export, customer-managed keys only if supportable, policy packages, availability and disaster-recovery contracts based on tested capacity.
- Versioned public APIs, webhooks, SDKs and sandbox documentation, deprecated/version compatibility policy; no open marketplace install bypassing server authorization.
## 5. Experience, design and complete screen inventory
Produce APP_SCREEN_MATRIX.md from this specification, including all desktop/tablet/mobile routes and modals, roles, API contract, current/beta/planned state, empty/loading/error/offline/permission/overquota states, a11y and test mapping. Group coverage: public marketing/legal/docs/status/contact/demo; signup/onboarding/account/org/workspace; universal dashboard/command palette/notifications; Lead 360 and pipeline/import wizard/campaign eligibility; omnichannel inbox; website widget; WhatsApp; Instagram; voice agent/studio/call operations; workflows builder/monitor; integrations; marketplace/editor/reviews; AI Studio; analytics/reports; billing; teams/security; beta program; privacy/data requests; platform super-admin/config publishing; incident/logs/deploy visibility; future Growth and Mobile. No dead links or staged routes that look live.

Quality: Premium coherent OraOne brand and logo; responsive 320/360/390/768/1024/1280/1440/1920; native touch and keyboard interactions; WCAG 2.2 AA target incl. 200/400% zoom, color contrast, reduced motion and screen readers; English first, localization readiness; tested Chromium/Firefox/WebKit plus real Safari/mobile where available. Error states always actionable, user-facing claims honest. Feature availability and real provider validation must be displayed truthfully.
## 6. Data model, rights and trust invariants
- PostgreSQL authoritative entities: tenant, project, user, role, customer/contact, verified identity alias, consent evidence, suppression, channel account, conversation, message, delivery event, lead, opportunity, task, event, activity, campaign, import batch/row status, call/call attempt, transcript authorization, workflow definition/version/run/step, connector credentials reference, agent version, feature flag, config draft/revision/publication, marketplace listing/review, usage reservation/cost, audit event, incident and telemetry summary. Reuse existing entities and apply additive migrations. No second contact store or parallel lead status authority.
- Multi-tenancy: apply org/project scoping in every read/write/search/export/blob URL/websocket/job/queue/cache/vector query. Cross-tenant identity matching forbidden; merge/split reversible with audit.
- Sensitive-content handling: encryption transit/at rest, key rotation, secrets in server vault/approved store, redacted logs, processor inventory/DPA, explicit retention and deletion by data class, subject access/export/correct/delete and appropriate consent legal basis; no AI model training, sale or unrelated reuse of customer data.
- Automated actions: model output is an untrusted proposal. Central deterministic policy service authorizes every tool call, message and dial using role, approved destination, channel rules, consent, suppression, time, budget and per-tenant feature flags. Replay protection and exact delivery provenance required.
- Every risk decision/version and customer-visible outcome has an audit record; do not generate misleading analytics or merge unknown identities.
## 7. Compliance, feasibility and hard release gates
1. Voice/bulk calling: A spreadsheet is not consent. Only contact recipients with documented consent or other demonstrably lawful eligibility through an authorized provider. Implement per-number checks, DND/suppression, frequency caps, appropriate AI/caller/recording disclosures, opt-out and owner campaign approval. India may require Principal Entity/telemarketer registration, appropriate numbering/routes, consent/template compliance and other TRAI/TCCCPR obligations. Do not use personal SIMs or bypass provider restrictions. Items to confirm with counsel and the chosen provider before any Indian outbound campaign: Distributed Ledger Technology (DLT) registration of the business entity, headers, and templates where required; the number series required for promotional and transactional calls; DND registry scrubbing immediately before each attempt; time-of-day limits; and the current TCCCPR amendments. These are verification items, not assumed rules.
2. WhatsApp: Meta/BSP review, phone/business ownership, permissions, opted-in marketing, approved templates/messaging windows, pricing and webhook verification. Official APIs only.
3. Instagram: eligible professional account and approved permissions; customer-initiated messaging under allowed interaction windows. No unsolicited bulk DM mechanism.
4. YouTube/Instagram publishing: separate app approvals/OAuth scopes, content IP rights, quotas, human publication control; availability varies by account and endpoint.
5. AI and recordings: provider retention/no-training settings verified, region and consent policy, appropriate voice cloning/identity safeguards; never use another person's voice without permission.
6. Privacy: legal review for India DPDP applicability and other markets, secure deletion and retention, processor contracts, breach response, sensitive-data access audit.
7. Hostinger: confirm actual VPS/CPU/RAM/IO, region, domain/TLS, backups, off-host restore, resource limits, network policy; evaluate capacity for realtime calling and avoid assuming one VPS handles media workloads.
8. No fake production: live DNS, payments, auth, outbound, provider integrations, billing, data migration, rollback and privacy tests need environment-specific evidence. No claim of readiness before all launch-required checks pass.
## 8. Release plan — complete target, gated activation

| Gate | Release slice | Outcome | External dependency |
|---|---|---|---|
| R0 | Baseline stabilization | Secure known code, migration parity, remove dummy public data, CI/observability/backup and trusted app shell | Identity method and email provider (D21), SMTP, production infrastructure evidence |
| R1 | Unified Lead and Website OS | Lead 360, pipeline, shared inbox for web, tasks, universal analytics and embedded widget, proper admin/config publishing/beta flags | Owner product approval |
| R2 | WhatsApp integration | Official two-way WhatsApp and authorized templates with unified inbox | Meta/business/BSP approval |
| R3 | Instagram integration | Official professional messaging, comments where supported, handoff | Meta app review and account permissions |
| R4 | AI Voice and eligible calling | Inbound and lawful outbound/Excel campaigns, real-time voice and transfers | Telecom provider, regional compliance, measured voice costs/latency |
| R5 | Workflow Automation and Integrations | Governed event engine, builder, verified connectors | Provider permissions |
| R6 | AI Studio and Marketplace | Versioned agent studio and vetted add-ons | Security/licensing review, payment decisions |
| R7 | Unified OS hardening | Cohesive navigation, enterprise-grade ops, deep analytics, scalability, mature beta feature management | Load and user acceptance evidence |
| R8 | Future Growth/Marketing and Mobile | YouTube/Instagram content scheduling, future mobile/enterprise modules | App review, content rights and approvals |

All modules have defined scope NOW; no future phase is claimed implemented or production active. Slice order can change by dependencies with owner sign-off. A consolidated public OS launch encompassing R0–R7 is possible only after each provider/financial/legal/quality gate passes; otherwise publicly label availability honestly and leave missing modules disabled. Internal alpha and closed beta do not authorize bypasses.
### 8.1 Build-order rule

- Channel and automation modules (OS-WA, OS-IG, OS-VOICE, OS-OMNI live adapters, OS-FLOW, OS-MKT, OS-STUDIO, OS-GROWTH) start implementation only after the R0 gates G01, G03, G04, G21, and G22 pass at TESTED_LOCAL or higher, and the shared services they depend on exist with passing tests: OS-01 (identity and tenancy), OS-02 (Customer and Lead 360), OS-04 (policy and consent), OS-05 (events and outbox), and OS-06 (AI gateway)
- Before that, those modules may have specifications, adapter contracts, fixtures, and mock-based contract tests only
- Baseline production blockers always come before new modules. No module may weaken authentication, tenant isolation, consent enforcement, or cost protection

## 9. Acceptance matrix — compulsory

| Gate | Acceptance requirement |
|---|---|
| G01 | Exact repo SHA and code inventory, migration parity, clean baseline and backup |
| G02 | Product/screen/journey matrices complete, planned functionality labeled correctly |
| G03 | Cross-tenant denial tests on all paths incl. exports/search/realtime/vector/jobs |
| G04 | Secure application identity, MFA, authorization and session lifecycle tested |
| G05 | Authenticated, consented, accessible website widget installs on unrelated domains safely |
| G06 | Lead import/capture/score/assign/follow-up/outcome history and opt-out correct |
| G07 | WhatsApp official approvals, windows/templates/webhooks and policy tests pass |
| G08 | Instagram official permissions, initiation limits, DM/reply tests pass |
| G09 | Inbound/outbound voice legality/provider verification, AI disclosure and eligible dial tests pass |
| G10 | Excel import rejects invalid/duplicate/unconsented/DND rows; manual approval and cap stops queue |
| G11 | Omnichannel identity, ordering, dedup, delivery evidence, ownership and handoff pass |
| G12 | Workflow actions are authorized, bounded, idempotent; policy checked at execution |
| G13 | Marketplace submission, scanning, review, publishing, revocation and isolation pass |
| G14 | AI Studio groundedness, tool authorization, tenant data handling and cost pass |
| G15 | Beta cohorts, flag dependencies, kill switch, rollout rollback and no bypass pass |
| G16 | Admin config publish follows review, staging validation, audit and safe rollback |
| G17 | Logs redacted, query/export RBAC audited, incident response and independent alerts tested |
| G18 | Analytics definitions trace to real events, no fabricated metrics or attribution |
| G19 | Billing webhook, entitlements, cost reservation/settlement, refunds and spend caps pass |
| G20 | WCAG 2.2 AA, responsiveness and Chromium/Firefox/WebKit testing, human review |
| G21 | OWASP Web/API/LLM security, security headers, input/output validation, secret/dependency/SBOM scans and remediation pass |
| G22 | Complete automated push/integration/nightly/manual CI test trigger suite executes and fails closed |
| G23 | Owner-only manual Hostinger deploy from main, pre/post checks, artifacts, health and rollback proof |
| G24 | Production public site has no dummy claims/forms/counts/test data and truthfully labels available modules |
| G25 | Documentation for product, host, DNS, infra, domain, DR, incident, legal, APIs, integration permissions is current |
| G26 | Full feature-by-feature and channel scenario suites including denial, abuse, failure, recovery, cost and scale pass |
| G27 | Backup/restore off-host, failure injection, performance and capacity thresholds verified |
| G28 | Real customer beta consent, segmentation, feedback and production change approvals verified |
| G29 | Marketing publishing remains disabled until rights/app approvals and editorial review pass |
| G30 | Independent audit and owner go/no-go signed with all critical blockers resolved |

Gates G07–G14 and G29 may be NOT_DUE only while the corresponding module is deliberately not being released; they cannot be waived for an all-products-ready launch.

### 9.1 Gate-to-release map

| Release slice | Gates that must pass for that slice |
|---|---|
| R0 Baseline stabilization | G01, G02, G03, G04, G17, G21, G22, G24, G25 (baseline parts), G27 (staging parts) |
| R1 Unified Lead and Website OS | All R0 gates plus G05, G06, G11 (website channel), G15, G16, G18, G19, G20, G26 (enabled modules) |
| R2 WhatsApp | G07, G11, G26 for WhatsApp |
| R3 Instagram | G08, G11, G26 for Instagram |
| R4 Voice and eligible calling | G09, G10, G11, G26 for voice |
| R5 Workflows and integrations | G12, G26 for workflows and connectors |
| R6 Studio and marketplace | G13, G14, G26 for those modules |
| R7 Unified hardening | G27 (production parts), G28 |
| R8 Growth and mobile | G29 and the module's G26 suites |
| Any production release | G23 and G30, owner only |

A gate belonging to a slice that is not in the target release is reported NOT_DUE with that slice named.
## 10. Business, pricing and economic gates
Require realistic per-message/channel/voice-minute/STT/TTS/model/token/storage/egress/support costs; compare providers by available markets/quality/price/reliability and confirm invoices/limits. No unlimited plan claims. Model per-tenant budgets, quotas, monthly hard cap, refunds and reconciliation; simulate high-call-volume cost exposure before enabling campaigns. Validate willingness to pay and product demand with permitted pilots before committing to expensive integrations or manufacturing-grade-scale infrastructure.
## 11. Public site content integrity
Before claiming oraone.in ready: remove dummy customer logos, fabricated success metrics/testimonials, fake pricing, placeholder live status, mock conversations represented as real, broken buttons, fake booking or form successes, misleading beta/available labels. Keep clearly labeled illustrative demos where they help understanding; never expose synthetic tenant records in public APIs. Verify every 2xx functional route with real backends, consented test fixture and credible error/recovery states. Audit SEO, canonical pages, legal and security disclosures and unambiguous production/contact delivery.
## 12. Required docs and truth reporting
Maintain README.md, PRODUCT_VISION.md, MISSION.md, PRODUCT_PORTFOLIO.md, FEATURE_MATRIX.md, APP_SCREEN_MATRIX.md, JOURNEY_MATRIX.md, PROVIDER_PERMISSION_MATRIX.md, DATA_CLASSIFICATION.md, SECURITY_MODEL.md, PRIVACY_RETENTION.md, THREAT_MODEL.md, API_CONTRACTS.md, HOSTINGER_DEPLOYMENT.md, DOMAIN_DNS_TLS.md, BACKUP_RESTORE.md, INCIDENT_RESPONSE.md, RUNBOOKS.md, BETA_ROLLOUT.md, COST_MODEL.md, QUALITY_AUDIT.md, PROGRESS.md, GAP_MATRIX.md and actionable blocker.txt. Prefer linking/updating existing repo documents rather than duplicating.

Every feature reports SPECIFIED / OBSERVED_CODE / TESTED_LOCAL / TESTED_STAGING / VERIFIED_EXTERNAL / VERIFIED_PRODUCTION / BETA / GATED / NOT_DUE / BLOCKED / RETIRED with requirement, phase, exact SHA, test IDs and results, owner, missing evidence and permitted activation state. No guessed percentages or hard-coded production claims.
## 13. Owner decisions still required
D01 Approve comprehensive OS scope and all-products target; D02 initial launch geography and jurisdictions; D03 provider selections, pricing, capacity and paid spend caps; D04 WhatsApp Business and Instagram ownership and app review; D05 calling purpose, consent source and telecom/AI disclosure policy; D06 recording/transcription retention, deletion and processor contracts; D07 product pricing/tax/Stripe currency; D08 exact beta cohort/rollout controls; D09 final design identity; D10 Hostinger VPS constraints and backup location; D11 privileged config publication approval boundaries; D12 analytics/attribution consent and retention; D13 marketing publishing scope; D14 acceptance of staged internal releases vs strict full public OS launch. D15 Lead status set and additive migration from the existing statuses (v1.1 D03; Appendix A.2). D16 Lead temperature semantics and the "unknown" default (v1.1 D16; rule R1). D17 Identity model: whether Customer/Contact extends or wraps the existing VisitorProfile, and how aliases, memory, and lead fields migrate (v1.1 D17; rules R2 to R4). D18 Prototype and planned-product code: keep behind disabled flags or remove until each module's gate (v1.1 D18; rule R5). D19 Launch languages for widget, workspace, and voice (v1.1 D13). D20 Data residency and cross-border processing for storage, backups, AI, and voice providers (v1.1 D14; related to D02). D21 Replacement identity approach and email provider after removing Cognito, and migration of existing Cognito users (Amendment 2026-10-20).

The project can prepare code and mocks without these decisions, but cannot silently assume them. Appendix A.5 maps the retired v1.1 decision numbers to this register.

---

Final rule: Build the complete integrated OraOne OS, not ten disconnected apps, not a chat-only product. Preserve existing architecture wherever sound, verify every integration and user journey, and refuse to equate code presence with production readiness.

---

## Appendix A: Carried forward from v1.1 (repository-grounded)

These items were in the v1.1 specification and remain in force. They are code observations and rules, not verified behaviour; the baseline audit re-verifies them on the current SHA.

### A.1 Repository facts that affect the Lead OS (observed at commit 10a6fdd)

These are code observations, not verified behaviour.

| Area | Observed | Consequence for this specification |
|---|---|---|
| Lead status | `LeadStatus`: new, contacted, qualified, won, lost | Appendix A.2 maps these to the proposed statuses with an additive migration |
| Lead temperature | `LeadTemperature`: hot, warm, cold; default and server default `warm`; described as derived from score or intent | R1 |
| Visitor identity | `VisitorProfile`: one profile per organization across channels, keyed by browser token, normalised phone, external ID, or email; stores name, email, phone, merged aliases, a rolling memory of message highlights, `lead_score`, and a free-text `lead_status` | R2, R3, R4 |
| Marketing contacts | `ContactSubmission` and `NewsletterSubscriber` are OraOne's own website records | R6 |
| Planned-product code | API packages for `omnichannel`, `channels`, `marketplace`, `workflows`; models for marketplace, workflow, and agent channels | R5 |
| Billing | Stripe only; plan and invoice currency default `usd` | D07 |
| CI and deploy | Checks run only on pushes and pull requests to `main`; production deploy is manual, `main` only, with typed confirmation and the `production` environment | Engineering goal adds development-branch CI; production stays owner-only |
| Frontend and tooling | JavaScript (not TypeScript); no frontend unit test runner; no coverage, dependency audit, or secret scanning observed in CI | Engineering standards |

Rules:
- **R1 Temperature honesty:** a lead that has not been scored shows "unknown", not "warm". Any temperature shown is labelled heuristic, with its inputs and rule version. Changing the stored default needs a migration and the D16 decision (section 13); existing values are not silently rewritten
- **R2 One authoritative status:** `Lead.status` (later the opportunity stage) is authoritative. `VisitorProfile.lead_status` and `lead_score` become derived or are retired by migration; they never contradict the lead record shown to operators
- **R3 One identity foundation:** `VisitorProfile` is the existing identity record. D17 (section 13) decides whether the section 6 Contact extends it or wraps it. No second, parallel contact store. Alias merging follows the section 6 identity rules: explainable keys, human-reversible, no cross-tenant links. Phone-keyed resolution stays inactive until OS-VOICE (release R4) is enabled
- **R4 Memory is personal data:** `VisitorProfile.memory` holds message text. It is covered by consent and the repeat-visitor rule in section 4.1, has a retention default, and is included in export, deletion, and opt-out (journey 12)
- **R5 Planned products stay unavailable:** planned-product routes and models are disabled in production or return a clear "not available" state; gate G24 and G02 verify this. Their presence in code is not evidence of availability. D18 (section 13) decides whether to keep them behind flags or remove them
- **R6 Naming:** "Contact" in this specification means a tenant's customer contact. `ContactSubmission` remains OraOne's own marketing data and is never mixed with tenant data
- **R7 Baseline currency:** observations here are tied to commit 10a6fdd. The engineering baseline audit re-verifies them on the current SHA before relying on them

### A.2 Status versus workflow state

The v1 specification's status list and lifecycle line described two different things. They are reconciled as follows:
- **Sales status** (one field, authoritative): new, contacted, qualified, meeting, proposal, won, lost, disqualified, archived
- **Workflow facts** (separate fields and events, not statuses): captured (creation event), reviewed (who and when), assigned (current owner and history), SLA clock state
- The section 6 lifecycle line (Captured → Reviewed → Qualified → Assigned → Contacted → Meeting/Proposal → Won/Lost) is an illustrative journey combining both, not the status list

Mapping from the existing `LeadStatus` values (Appendix A.1):

| Existing value | v1.1 status | Migration |
|---|---|---|
| new | new | Unchanged |
| contacted | contacted | Unchanged |
| qualified | qualified | Unchanged |
| won | won | Unchanged |
| lost | lost | Unchanged |
| (none) | meeting, proposal, disqualified, archived | Added by an additive enum migration; no existing value is renamed, reused, or rewritten |

"Meeting" and "proposal" are set only from trusted events or explicit user entry. "Archived" hides a lead from active views without deleting it. Final names and order are confirmed under D15 (section 13).

### A.3 Metric dictionary

Every metric below is computed from recorded events, in the organization's configured time zone, excluding records marked spam, test, or merged duplicate. Each report shows its numerator, denominator, window, and exclusions.

| Metric | Definition |
|---|---|
| Captured leads | Leads created from consented capture or authorized manual entry in the window |
| Time to owner | Capture timestamp to first assignment to a human owner |
| First human response time | Capture timestamp to the first human-sent or human-approved message on an enabled channel. AI auto-replies are reported separately and never counted as a human response |
| SLA attainment | Leads whose first human response met the configured business-hour target, divided by leads whose SLA clock started in the window |
| Missed lead | A lead with no owner action by its SLA deadline |
| Qualified rate | Leads moved to qualified by a human or an approved rule version, divided by captured leads |
| Meeting rate | Leads with a meeting recorded from a trusted calendar event or explicit user entry, divided by qualified leads |
| Win rate | Opportunities recorded as won, divided by opportunities closed (won plus lost) in the window |
| Weekly active operators | Distinct users who performed at least one lead or conversation action in the week |

Visitor counts appear only where measured with consent. Revenue appears only from trusted outcome data (section 4.10).

Channel extensions (for OS-WA, OS-IG, OS-VOICE once enabled): message delivery and read rates use only provider-reported states (section 4.2); call metrics count connected, completed, transferred, and opted-out calls from provider events and dispositions; campaign contactability is eligible recipients divided by imported recipients, with rejection reasons listed.

### A.5 Decision mapping from v1.1

| v1.1 decision | v2.1 decision |
|---|---|
| D01 positioning | D01 |
| D02 pilot customer profile | D14 (staged releases) and pilot plan; still needed |
| D03 lead lifecycle | D15 |
| D04 capture and outbound practices | D05 and D02 |
| D05 manual versus automated actions | D11 and section 6 automated-action rules |
| D06 identity, merge, retention | D17 (identity), D06 (recordings), D12 (analytics retention) |
| D07 tenancy model for agencies | Still needed; record under D01 scope |
| D08 integrations authorized | D03 and D04 |
| D09 cost caps and packaging | D03 and D07 |
| D10 production infrastructure | D10 |
| D11 conflicts with existing approvals | D01 |
| D12 pilot success criteria | Still needed; record under D14 |
| D13 launch languages | D19 |
| D14 data residency | D20 |
| D15 payments and currency | D07 |
| D16 temperature | D16 |
| D17 identity model | D17 |
| D18 planned-product code | D18 |

v1.1 decision numbers are retired. Use only the v2.1 numbers.

---

## Amendment 2026-10-20 — No AWS, no repository names (owner decision, global CR-02)
- Amazon Cognito and all other AWS services are removed from scope because of cost. Identity is application-managed in the FastAPI backend: secure `HttpOnly` session cookies with rotation, Argon2id password hashing and/or email one-time codes, TOTP MFA and step-up for privileged roles, session and device revocation. Object storage uses an S3-compatible, non-AWS service (MinIO on the owner's host or another approved provider).
- New decision **D21**: choose the replacement sign-in method(s) and the email delivery provider, and approve the migration plan for any existing Cognito users (re-verification by email, no password export). Until D21, build the application-managed identity behind a flag and keep existing Cognito code paths untouched but marked for removal; record the migration as READY_FOR_OWNER.
- Removing Cognito code follows the proven-unused deletion rule and lands only with passing authentication, session, tenancy and MFA tests (gate G04).
- Documents and commit messages never contain repository names or repository links.
