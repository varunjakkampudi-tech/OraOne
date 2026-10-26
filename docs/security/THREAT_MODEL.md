# Threat Model

This document establishes the threat model for the core architectural subsystems of OraOne using the STRIDE methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege). All evaluated controls cite exact repository file paths and line numbers. In accordance with project governance, no subsystem is treated as production-ready or live.

---

## 1. Passwordless Email-Code Authentication

### Assets

- User identity accounts and credentials (`users` table).
- Session credentials: cryptographic access and refresh JWT pairs, HttpOnly session cookies.
- Account profile data (`email`, `full_name`, `role`).

### Trust Boundary

- **Boundary**: Untrusted public internet client $\rightarrow$ FastAPI Auth Router (`backend/app/api/auth/routes.py`) $\rightarrow$ Authentication Domain Service (`backend/app/services/auth_service.py`) $\rightarrow$ Shared Guard Store / Cache (`backend/app/services/cache.py`) $\rightarrow$ Database (`backend/app/database/models/user.py`).

### Threats (STRIDE)

- **Spoofing**: Brute-forcing 6-digit numeric login codes to impersonate users; forging refresh tokens.
- **Tampering**: Modifying in-flight session cookies or auth payloads; altering tokens.
- **Repudiation**: User denying login or session renewal without audit logs.
- **Information Disclosure**: Timing attacks or divergent error messages revealing registered email addresses (account enumeration); leaking credentials or auth tokens in application logs.
- **Denial of Service**: Flooding `/api/auth/email-code/request` to exhaust transactional email quota or database connection pool; flooding OTP verification to consume CPU.
- **Elevation of Privilege**: Bypassing passwordless requirement via development login endpoints in deployed environments; reusing revoked refresh tokens.

### Existing Controls with File:Line Evidence

- **Account Enumeration Defense**: `request_email_code` returns an identical silent response whether the target address exists or not (`backend/app/api/auth/routes.py:63-65`, `backend/app/services/auth_service.py:120-139`). For unseeded addresses, an inactive placeholder account with a high-entropy random password hash is created so login is solely feasible via email OTP (`backend/app/services/auth_service.py:144-153`).
- **Send Rate Limiting**: Code delivery is capped at `MAX_CODE_SENDS = 5` per address within a 15-minute sliding window (`_LIMIT_WINDOW_SECONDS = 900`) using the shared guard store (`backend/app/services/auth_service.py:54-56`, `backend/app/services/auth_service.py:132-138`).
- **Attempt Throttling & Invalidation**: Code verification is strictly bounded to `MAX_CODE_ATTEMPTS = 5` attempts; exceeding this invalidates the pending code and refuses subsequent attempts with HTTP 429 (`backend/app/services/auth_service.py:52`, `backend/app/services/auth_service.py:183-193`).
- **Timing-Safe OTP Comparison**: Verification executes constant-time digest comparison via `hmac.compare_digest` to defeat side-channel timing analysis (`backend/app/services/auth_service.py:195`).
- **Single-Use Code Revocation**: Validated codes are atomically deleted from cache immediately upon acceptance (`backend/app/services/auth_service.py:196`).
- **Short Lifetime**: Pending OTP codes expire after `_LOGIN_CODE_TTL_SECONDS = 600` (10 minutes) (`backend/app/services/auth_service.py:47`, `backend/app/services/auth_service.py:162`).
- **Fail-Closed Guard Store**: If the shared guard cache backend is unavailable, or if an in-process cache is detected in production, authentication requests fail closed with HTTP 503 (`backend/app/services/auth_service.py:84-102`).
- **Development Login Gating**: Password sign-in (`/api/auth/dev-login`) is strictly refused and responds with HTTP 404 unless `settings.environment == "development"` and `ALLOW_DEV_PASSWORD_LOGIN=true` (`backend/app/api/auth/routes.py:88-93`, `backend/app/services/auth_service.py:227-228`, `backend/app/services/auth_service.py:248-255`). Tested in `backend/tests/test_dev_login_gating.py:21-42`.
- **HttpOnly Cookie Handling**: Session tokens are written to client response headers using HttpOnly, Secure, and SameSite attributes (`backend/app/api/auth/routes.py:76-78`, `backend/app/core/cookies.py:45-56`).
- **Session Revocation**: Refresh tokens can be individually revoked on logout or comprehensively revoked across all active devices (`backend/app/api/auth/routes.py:118-143`, `backend/app/services/auth_service.py:272-304`).
- **Verification Evidence**: Passing test suites in `backend/tests/test_email_code_auth.py:26-116` and `backend/tests/test_auth_cookies.py:18-64`.

### Residual Risk

- Mail delivery infrastructure security is external; compromise of downstream SMTP provider allows interception of login codes.
- In-process fallback cache in non-production local environments does not enforce rate limits across multiple concurrent worker processes (`backend/app/services/auth_service.py:93-94`).
- Known finding SEC-T8 (`GAP_MATRIX.md:126`): dev password login logs `auth_subject` in warning logs (`backend/app/services/auth_service.py:244`).

---

## 2. Workspace and Organization Tenancy and Authorization

### Assets

- Multi-tenant tenant boundaries, workspace data, projects, customer records, and RBAC definitions.
- Tenant isolation across database entities (`organizations`, `organization_members`, `agents`, `conversations`).

### Trust Boundary

- **Boundary**: Client request with Bearer JWT $\rightarrow$ FastAPI `get_current_organization` Dependency (`backend/app/middleware/org_context.py`) $\rightarrow$ PostgreSQL Tenant Isolation & Session Stamping $\rightarrow$ Scoped Service & Repository queries.

### Threats (STRIDE)

- **Spoofing**: Attacker injecting `X-Org-Id` or crafting JWT claims to masquerade as an agent/member of another organization.
- **Tampering**: Modifying workspace data belonging to a different tenant (IDOR).
- **Repudiation**: Non-audited cross-workspace modifications.
- **Information Disclosure**: Cross-tenant data leakage via queries lacking tenant `WHERE` clauses.
- **Denial of Service**: Tenant resource exhaustion starvation across shared database connections.
- **Elevation of Privilege**: Member elevating privileges to Owner/Admin; viewer executing mutation actions.

### Existing Controls with File:Line Evidence

- **Server-Side Tenant Resolution**: The organization ID is strictly resolved server-side by looking up the verified `auth_subject` in active `organization_members` rows (`backend/app/middleware/org_context.py:7-12`, `backend/app/middleware/org_context.py:95-126`, `backend/app/middleware/org_context.py:134-165`). Client-supplied headers like `X-Org-Id` or request body tenant identifiers are ignored (`backend/app/middleware/org_context.py:139-141`).
- **Mandatory Repository Scoping**: Endpoints receive an immutable `OrgContext` and enforce `organization_id == ctx.organization_id` on all database operations (e.g., `backend/app/api/agents/routes.py:180`, `backend/app/api/agents/routes.py:227`).
- **Database Session Stamping for RLS**: Transaction-local session variables `app.org_id` and `app.user_id` are stamped on each database session to enable PostgreSQL Row-Level Security policies (`backend/app/middleware/org_context.py:65-93`).
- **Role & Permission Enforcement**: Declarative RBAC dependency factories `require_role` (`backend/app/middleware/org_context.py:190-212`) and `require_permission` (`backend/app/middleware/org_context.py:215-246`) enforce capabilities defined in the permission matrix (`backend/app/core/permissions.py:62-120`).
- **Cross-Organization Verification Tests**: Verified through automated suites in `backend/tests/test_cross_org_authorization.py:24-110`, `backend/tests/test_phase5_org_isolation.py:20-85`, and `backend/tests/test_platform_rbac.py:10-48`.

### Residual Risk

- Application-level scoping is currently the primary line of defense: if a query omits `organization_id`, database RLS session stamping logs a warning but remains non-fatal for local backwards compatibility (`backend/app/middleware/org_context.py:14-16`, `backend/app/middleware/org_context.py:85-92`).
- Known finding SEC-T9 (`GAP_MATRIX.md:127`): routes with low tenant-reference density require systematic individual audits.
- Multi-organization membership currently resolves only to the most recently joined active organization (`backend/app/middleware/org_context.py:108-114`).

---

## 3. Public Website Chat Widget

### Assets

- Agent configuration and prompt instructions.
- Visitor chat session transcripts, lead capture PII, and customer feedback data.
- Enterprise knowledge base retrieval content accessible to the public widget.

### Trust Boundary

- **Boundary**: Anonymous public browser visitor $\rightarrow$ Public Widget API (`backend/app/api/widgets/public.py`) $\rightarrow$ Widget Service (`backend/app/services/widget_service.py`) $\rightarrow$ RAG Answer Pipeline $\rightarrow$ Lead & Session Stores.

### Threats (STRIDE)

- **Spoofing**: Impersonating other visitors to access private chat transcripts; forging visitor IDs.
- **Tampering**: Injecting prompt injections or malicious context into assistant chat prompts.
- **Repudiation**: Unattributed lead submissions or malicious input.
- **Information Disclosure**: Exposing internal organization knowledge outside widget knowledge scope; leaking configuration secrets.
- **Denial of Service**: Scripted automated requests exhausting token budgets, storage, or rate limits by rotating `visitor_id`.
- **Elevation of Privilege**: Bypassing domain allow-list restrictions; invoking non-published widget configurations.

### Existing Controls with File:Line Evidence

- **Public Key & Status Gating**: All widget endpoints require a valid public key and enforce `WidgetStatus.published` before allowing chat or streaming (`backend/app/api/widgets/public.py:6-7`, `backend/app/api/widgets/public.py:105-109`).
- **Domain Allow-List Validation**: Widget verifies `Origin` and `Referer` headers against registered domains when an allow-list is configured (`backend/app/api/widgets/public.py:110-118`).
- **Visitor Session Cryptographic Tokens**: When a visitor starts a session, the server generates a cryptographically secure random token (`secrets.token_urlsafe(32)`) and stores only its SHA-256 digest in the database (`backend/app/api/widgets/public.py:165-178`, `backend/app/api/widgets/public.py:284-297`). Subsequent requests must present this token via `X-Widget-Session` header, verified with `hmac.compare_digest` (`backend/app/api/widgets/public.py:170-178`).
- **Dual Rate Limiting**: Enforces both a per-visitor limit (`backend/app/api/widgets/public.py:122-130`) and a per-client-IP limit (`backend/app/api/widgets/public.py:140-156`) to thwart attacks rotating client-generated `visitor_id` values.
- **Context Sanitization**: Visitor context fields are restricted to an explicit allow-list of keys (`_MAX_CONTEXT_KEYS`) with values capped at 300 characters (`backend/app/api/widgets/public.py:75-84`, `backend/app/api/widgets/public.py:185-192`).
- **Retrieval Scope Limitation**: Public widget RAG retrieval queries only knowledge base IDs explicitly bound to the widget or agent (`backend/app/api/widgets/public.py:195-215`).
- **Fail-Closed Legacy Visitor Handling**: Historical session rows lacking a token hash fail closed and are denied transcript access (`backend/app/api/widgets/public.py:175-177`).
- **Verification Evidence**: Automated security tests in `backend/tests/test_product_widget_security.py:225-478` and `backend/tests/test_widget_domain_policy.py:20-80`.

### Residual Risk

- `Origin` and `Referer` headers can be forged by non-browser clients (such as curl or scripts); the codebase documents this courtesy check explicitly (`backend/app/api/widgets/public.py:8-10`).
- Known finding SEC-T5 (`GAP_MATRIX.md:123`): `widget_event` allows calls with `require_published=False` (`backend/app/api/widgets/public.py:957-969`).

---

## 4. Inbound Webhooks: Stripe, Meta, Twilio, and Telegram

### Assets

- Subscription status and commercial billing states (`subscriptions`, `billing_webhook_events`).
- Omnichannel customer communication channels and agent reply dispatch.
- Telephony call sessions and voice agent controls.

### Trust Boundary

- **Boundary**: External third-party webhook dispatchers (Stripe, Twilio, Meta, Telegram) $\rightarrow$ Public Webhook Endpoints (`/api/billing/webhook`, `/api/channels/*`, `/api/voice/*`) $\rightarrow$ Adapters & Signature Verification $\rightarrow$ Omnichannel Inbound Service.

### Threats (STRIDE)

- **Spoofing**: Forged webhook payloads simulating payment completions or fake customer messages.
- **Tampering**: In-flight tampering of webhook parameters, message bodies, or financial metadata.
- **Repudiation**: Webhook events processed without idempotent tracing or event IDs.
- **Information Disclosure**: Leaking provider tokens in logs or URL paths.
- **Denial of Service**: Webhook flooding causing redundant downstream model executions or out-of-order state transitions.
- **Elevation of Privilege**: Upgrading workspace subscription tier through fraudulent Stripe webhooks.

### Existing Controls with File:Line Evidence

- **Stripe Webhook Signature Verification**: Webhook handler enforces presence of `STRIPE_WEBHOOK_SECRET` (failing closed with HTTP 503 if absent) and verifies payload cryptographic signature via `stripe.Webhook.construct_event` (`backend/app/api/billing/routes.py:211-228`). Disabled paid billing returns HTTP 410 (`backend/app/api/billing/routes.py:202-206`).
- **Stripe Replay & Stale Protection**: Idempotency is enforced by persisting `event_id` in `billing_webhook_events`; duplicate event deliveries return `"duplicate"` and abort (`backend/app/services/billing_service.py:500-510`). Stale events older than the current subscription timestamp are rejected (`backend/app/services/billing_service.py:520-527`). Verified in `backend/tests/test_billing_webhook_replay.py:25-95`.
- **Meta (WhatsApp / Instagram) HMAC Validation**: Handshake verification echoes `hub.challenge` only when `hub.verify_token` matches in constant time (`backend/app/api/omnichannel/routes.py:241-250`). Inbound messages require HMAC-SHA256 signature verification over the raw body using `meta_whatsapp_app_secret` via `x-hub-signature-256` header (`backend/app/api/omnichannel/routes.py:256-261`). Verified in `backend/tests/test_meta_whatsapp.py:20-85` and `backend/tests/test_meta_instagram.py:20-75`.
- **Twilio Request Signing**: Twilio SMS and Voice webhooks verify cryptographic signatures over the full URL and form parameters against `twilio_auth_token` using `channel_adapters.verify_twilio_signature` (`backend/app/api/omnichannel/routes.py:288-301`, `backend/app/api/voice/routes.py:65-83`). Fails closed if public base URL or token is missing (`backend/app/api/voice/routes.py:71-73`). Verified in `backend/tests/test_twilio_signature.py:20-70`.
- **Telegram Webhook Authentication**: Authenticated via per-binding `telegram_webhook_secret` checked against `X-Telegram-Bot-Api-Secret-Token` header using `hmac.compare_digest` (`backend/app/api/omnichannel/routes.py:121-125`, `backend/app/api/omnichannel/routes.py:144-150`). Generic endpoints reject Telegram with HTTP 404 (`backend/app/api/omnichannel/routes.py:307-309`).
- **Provider Message Deduplication**: Message processing deduplicates on `provider_message_id` to prevent double-replies on network retries (`backend/app/services/omnichannel_service.py:120-145`).

### Residual Risk

- Known finding SEC-T1 (`GAP_MATRIX.md:119`): Telegram bot token is stored unencrypted in `AgentChannel.configuration["bot_token"]` (`backend/app/api/omnichannel/routes.py:94`).
- Known finding SEC-T2 (`GAP_MATRIX.md:120`): Telegram bot token appears in URL path (`backend/app/api/omnichannel/routes.py:221`), creating exposure in HTTP access logs.
- Known finding SEC-T3 (`GAP_MATRIX.md:121`): Inbound email webhook uses a single deployment-wide secret rather than per-binding secrets (`backend/app/api/omnichannel/routes.py:128-133`).
- Known finding SEC-T7 (`GAP_MATRIX.md:125`): Unguarded `uuid.UUID(org_id)` conversion on Stripe metadata can raise unhandled exception on malformed UUID (`backend/app/services/billing_service.py:516`).

---

## 5. AI Model Call Path and Token Limits

### Assets

- Upstream LLM provider API credentials (OpenRouter).
- Financial quotas, organization AI usage budgets, and rate allowances.
- System prompts, proprietary prompt engineering, and conversational grounding data.

### Trust Boundary

- **Boundary**: User or visitor prompt input $\rightarrow$ RAG / Omnichannel pipeline $\rightarrow$ Usage Pre-Reservation Service (`backend/app/services/usage_service.py`) $\rightarrow$ AI Provider Client $\rightarrow$ Usage Settlement.

### Threats (STRIDE)

- **Spoofing**: Impersonating an organization to consume its AI token balance.
- **Tampering**: Prompt injection manipulating the LLM into disregarding context boundaries or instruction guidelines.
- **Repudiation**: AI usage incurred without persistent metered consumption logs.
- **Information Disclosure**: Indirect prompt injection extracting proprietary system prompts or cross-tenant knowledge chunks.
- **Denial of Service**: Maliciously crafting queries with massive token lengths to exhaust organization daily/monthly quotas or trigger unexpected provider billing overages.
- **Elevation of Privilege**: Bypassing quota checks to invoke premium models without appropriate subscription tiers.

### Existing Controls with File:Line Evidence

- **Tiered Token Quotas in Plan Catalogue**: Plan definitions establish strict quota limits (Free plan allows 100 messages/day and 250,000 tokens/month) (`backend/app/services/billing_service.py:68-73`).
- **Daily Ceiling Guard**: Global and per-organization daily token caps (`DEFAULT_DAILY_AI_TOKENS = 500_000`) limit exposure against runaway model queries (`backend/app/services/usage_service.py:388-395`).
- **Two-Phase Reservation & Settlement Commit**: Before invoking an external AI provider, estimated token usage (prompt estimation + `max_tokens`) is reserved against both daily and monthly counters via `reserve_ai_tokens` (`backend/app/services/rag_answer.py:253-259`, `backend/app/services/usage_service.py:398-412`).
- **Graceful Budget Degradation**: If reservation fails due to budget exhaustion (`_BudgetExhausted`), the system does not fail with an error or call the paid LLM; it falls back to extractive answers directly from retrieved knowledge passages (`backend/app/services/rag_answer.py:258-259`).
- **Settlement and Full Failure Refund**: Real model token usage is settled in a `finally` block; failed or aborted LLM calls are refunded in full (`backend/app/services/rag_answer.py:271-275`, `backend/app/services/usage_service.py:414-419`).
- **Prompt Injection Delimiters**: Visitor-supplied inputs are encapsulated inside isolation delimiters (`<<<VISITOR_DATA_START>>>` and `<<<VISITOR_DATA_END>>>`) with explicit instructions forbidding instruction override (`backend/app/services/rag_answer.py:240-245`).
- **Verification Evidence**: Automated tests in `backend/tests/test_ai_budget.py:28-90` and `backend/tests/test_ai_reply_safety.py:13-54`.

### Residual Risk

- Token estimation prior to generation is heuristic (`_estimate_prompt_tokens`); edge cases with rare Unicode encodings may cause slight deviations before final settlement.
- Quota enforcement toggle (`AUTHZ_ENFORCE_QUOTAS`) defaults to `False` in test environments (`backend/app/services/authorization.py:76`).

---

## 6. Knowledge Document Upload and Search Path

### Assets

- Proprietary customer documents, source files (PDF, DOCX, TXT), and extracted textual content.
- Vector embeddings and full-text search indexes stored in PostgreSQL (`document_chunks`).
- Local filesystem storage repository (`uploads/`).

### Trust Boundary

- **Boundary**: Authenticated Tenant User $\rightarrow$ Document Upload Route (`backend/app/api/knowledge/routes.py`) $\rightarrow$ Upload Limit Validations $\rightarrow$ Local Storage Service (`backend/app/services/storage.py`) $\rightarrow$ Chunking & Embedding Pipeline $\rightarrow$ Hybrid RAG Retrieval Engine (`backend/app/services/rag_service.py`).

### Threats (STRIDE)

- **Spoofing**: Uploading documents into a foreign organization's knowledge base.
- **Tampering**: Path traversal attacks overwriting system binaries or other tenant files during upload.
- **Repudiation**: Document creation, deletion, or version updates occurring without audit events.
- **Information Disclosure**: Retrieving another tenant's vector chunks or full-text entries via hybrid search (cross-tenant leakage).
- **Denial of Service**: Uploading zip bombs / decompression bombs (e.g., recursive OOXML `.docx` files) or huge files to crash memory or fill disk storage.
- **Elevation of Privilege**: Executing unauthorized writes on knowledge bases without `kb.write` permission.

### Existing Controls with File:Line Evidence

- **Authorization & Ownership Checks**: Knowledge base mutation requires `Permission.KB_WRITE` (`backend/app/api/knowledge/routes.py:410`). The knowledge base is verified to belong to the authenticated caller's tenant via `_kb_for_org` (`backend/app/api/knowledge/routes.py:422-428`). Any assigned folder is verified against the same organization (`backend/app/api/knowledge/routes.py:433-441`).
- **Streaming Upload Size Cap**: File streaming utilizes `read_capped(file, _DEFAULT_MAX_BYTES)` with a 25 MiB cap (`_DEFAULT_MAX_BYTES = 26214400`); reading aborts immediately when the limit is exceeded, preventing memory exhaustion from unbuffered bodies (`backend/app/api/knowledge/routes.py:395`, `backend/app/api/knowledge/routes.py:444-445`, `backend/app/services/upload_limits.py:28-45`).
- **Decompression Bomb Protection**: Office OOXML files (`.docx`, `.xlsx`, `.pptx`) are inspected via `assert_office_package_safe`, which uncompresses archive members under a running uncompressed size ceiling (100 MiB) and member ratio limit (100:1) to prevent zip bombs (`backend/app/api/knowledge/routes.py:447`, `backend/app/services/upload_limits.py:48-70`).
- **Isolated Storage Paths**: Object keys are namespaced by organization and knowledge base ID (`org/<org-id>/kb/<kb-id>/<uuid>__<safe-filename>`), with filenames sanitized to alphanumeric characters to eliminate path traversal (`backend/app/api/knowledge/routes.py:481-488`, `backend/app/services/storage.py:42-50`). Local storage rejects symlinks and enforces POSIX mode 0700 permissions (`backend/app/services/storage.py:30-38`).
- **Content Checksum Deduplication**: Computes SHA-256 checksums to detect duplicate uploads and support immutable document versioning (`backend/app/api/knowledge/routes.py:451-471`, `backend/app/api/knowledge/routes.py:490-502`).
- **Strict Tenancy in Hybrid Retrieval**: The search engine constructs both vector cosine similarity and full-text search queries with mandatory SQL filters: `DocumentChunk.organization_id == organization_id` and `DocumentChunk.project_id == project_id` (`backend/app/services/rag_service.py:162`, `backend/app/services/rag_service.py:178`).
- **Audit Logging**: Uploads, updates, version additions, and soft deletes emit persistent audit records with user and organization IDs (`backend/app/api/knowledge/routes.py:344-356`, `backend/app/api/knowledge/routes.py:381-388`, `backend/app/api/knowledge/routes.py:514-520`).
- **Verification Evidence**: Automated tests in `backend/tests/test_knowledge_source_security.py:20-95`, `backend/tests/test_rag_scope_contract.py:20-80`, and `backend/tests/test_phase6_knowledge.py:25-110`.

### Residual Risk

- Non-Office archive formats or unexpected binary file extensions bypass OOXML decompression inspection, relying solely on the 25 MiB raw byte limit.
- Document text extraction is currently handled in background tasks; unhandled extraction errors are captured on the document row (`Document.processing_error`) rather than raising immediate HTTP errors.

---

## 7. Threat Model Summary and Unassessed Areas

| Area                          | Status   | Primary Mitigations                                                              | Unassessed Aspects / Known Deficiencies                                                     |
| ----------------------------- | -------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Passwordless Email Sign-In    | ASSESSED | 5-attempt lockout, 10m TTL, fail-closed guard cache, constant-time compare       | SEC-T8 (auth_subject logged in dev warning log)                                             |
| Multi-Tenant Authorization    | ASSESSED | Token-derived org ID, mandatory repository WHERE scoping, RLS session stamps     | SEC-T9 (systematic per-query audit across low-density routes open)                          |
| Public Website Chat Widget    | ASSESSED | Hashed visitor session tokens, dual visitor/IP rate limits, public-key gating    | SEC-T5 (widget_event allows require_published=False)                                        |
| Inbound Webhooks              | ASSESSED | Cryptographic HMAC validation (Stripe, Twilio, Meta), event replay deduplication | SEC-T1 (plaintext Telegram token), SEC-T2 (token in URL path), SEC-T3 (shared email secret) |
| AI Model Call & Token Budget  | ASSESSED | Two-phase reserve/settle commits, daily/monthly ceilings, extractive fallback    | Heuristic prompt token estimation margin of error                                           |
| Knowledge Document Upload/RAG | ASSESSED | 25 MiB streaming cap, zip-bomb protection, path sanitization, SQL tenant filters | Parsing edge cases for non-OOXML document formats                                           |
