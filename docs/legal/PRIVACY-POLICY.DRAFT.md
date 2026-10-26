# Privacy Policy — DRAFT (not approved)

Version identifier (to be set on the server once approved): `LEGAL_PRIVACY_VERSION`.
Controller / operator: [OWNER TO CONFIRM: legal entity, address, privacy contact]. Grievance officer and contact details: [OWNER TO CONFIRM; required for India under the DPDP Act and the Rules, subject to counsel].

This draft describes what the current code does. Items marked OWNER TO CONFIRM are not yet decided.

## 1. What we collect

**Account data.** Your email address, the name you give at signup, the organisation and workspace you create, your role, and sign-in records (time of sign-in, session identifiers, refresh-token records).

**Signup choices.** The version of the Terms and Privacy Policy you accepted, the time you accepted them (UTC), and your optional marketing choice, recorded whether you said yes or no.

**Customer Content you upload.** Documents (stored as files and split into text chunks and embeddings), website pages that you ask us to crawl, agent and assistant configuration, and knowledge sources.

**Conversation data.** Messages from website visitors who use the widget, and from channels you connect. This can include names, contact details and anything a person writes. Visitor identifiers are stored by the widget session.

**Lead data.** Details captured by the assistant or entered by your team, such as name, email, phone and notes, and the lead status and temperature.

**Voice data.** Where voice features are enabled, call audio is processed through voice providers, and transcripts and call records are stored. [OWNER TO CONFIRM: recording and transcript retention; whether audio is stored or only transcripts.]

**Technical data.** Server logs (request identifiers, routes, timings, status codes), error reports (with redacted fields), and security events (failed sign-ins, rate-limit events). Email addresses in logs are reduced to a one-way fingerprint.

**Billing data.** Paid billing is off in the current deployment. If it is enabled, payment processing happens with Stripe and we receive subscription status, not card numbers.

## 2. Why we use it

- To create and run your account and workspace (performance of a contract).
- To send one-time sign-in codes (performance of a contract).
- To run the assistant, search your knowledge and answer your visitors (performance of a contract).
- To keep the service secure and prevent abuse (legitimate interest, subject to counsel review).
- To send marketing messages only where you ticked the optional box (consent). You can withdraw consent at any time. [OWNER TO CONFIRM: the withdrawal route in the product.]

## 3. Providers that process your data

| Provider | Purpose | Data sent | Where it runs |
|---|---|---|---|
| Resend | Sends one-time sign-in codes by email | Your email address and the code | [OWNER TO CONFIRM: region and DPA] |
| OpenRouter (AI models) | Generates assistant answers and embeddings | Question, retrieved passages, instructions | [OWNER TO CONFIRM: underlying model providers and their data-retention terms] |
| Reranker provider (if enabled: Cohere, Jina or a local model) | Ranks search passages | Question and passages | [OWNER TO CONFIRM] |
| Meta (WhatsApp, Instagram), Telegram, Twilio | Messages and calls on channels you connect | Messages and phone numbers for those channels | Provider regions |
| ElevenLabs (if enabled) | Text-to-speech for voice | Text to be spoken | [OWNER TO CONFIRM] |
| Google (sign-in to connected integrations, if enabled) | Connects Google accounts you authorise | Data you authorise | Google |
| Stripe (only if billing is enabled) | Payments | Billing details | Stripe |
| Hosting provider (Hostinger VPS) | Runs the servers, databases and file storage | All stored data | [OWNER TO CONFIRM: the VPS location] |

We do not sell personal data. We do not use Customer Content to train AI models. [OWNER TO CONFIRM and counsel to verify each provider's no-training setting before this sentence is published.]

## 4. Where data is stored

PostgreSQL (with pgvector) holds account, conversation and knowledge data. Redis holds short-lived counters, sign-in codes (as keyed digests only) and rate-limit data. Uploaded files are kept on the server's disk in the upload directory. [OWNER TO CONFIRM: backup location, backup encryption and off-host copies.]

## 5. How long we keep data

[OWNER TO CONFIRM: retention for each category. Until set, no automatic deletion schedule is promised.] Sign-in codes expire after five minutes. Rate-limit counters expire within minutes to hours. Signup consent records are kept for as long as the account exists, so that we can show what was accepted, and [OWNER TO CONFIRM: for how long after deletion].

## 6. Security

Sign-in codes are stored only as keyed digests. Sessions use signed access tokens and rotating refresh tokens. Database access is limited by tenant. Secrets are kept in server configuration and never sent to the browser. No system is perfectly secure; please report suspected problems through the channel in the security policy.

## 7. Your rights

Depending on where you live, you may have the right to access, correct, export or delete your personal data, to withdraw consent, and to complain to a regulator. [OWNER TO CONFIRM: how requests are made, identity checks, response times. The product's data-request workflow is not yet built; this paragraph must not be published until it is.]

## 8. Children

OraOne is not directed at children. [OWNER TO CONFIRM: minimum age; counsel to review DPDP rules on children's data.]

## 9. International transfers

Some providers process data outside India. [OWNER TO CONFIRM: each transfer and its legal basis.]

## 10. Changes

[OWNER TO CONFIRM: how we notify you of material changes.]

## 11. Contact

[OWNER TO CONFIRM.]
