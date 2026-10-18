# OraOne product portfolio

The product numbers are identifiers, not a fixed launch or development sequence. Product 1 is the
active foundational product in this repository. The statuses below describe what the code does
today. They are not a release claim.

Status checked against commit `e6f8237` on branch `feat/product1-launch`, with a clean working tree
when this page was written. A commit is not a live service.

## Status labels

- **Built**: the code exists in this repository and has automated tests. It is not a claim that the
  feature is live for customers.
- **Live-needs-account**: the code is built, but a live service needs accounts, mail, provider keys or
  a setup step before a customer can use it.
- **Planned**: not built in this repository.

Viswatra is documented only as the intended portfolio-level brand direction. This repository does not
establish a legal corporate relationship or ownership structure.

## Status by product

| ID  | Product                       | What the code does today                                                                                                                                                              | Status             | Blockers                                                                                                                                                                                                        |
| --- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | OraOne AI Chat Platform       | Website chat and widgets, knowledge documents and search, assistants, leads, the inbox, team, billing foundations, usage and analytics, API keys, webhooks, the configuration console | Live-needs-account | Sign-in codes need a mail server, which is not configured. Needs an OpenRouter key. Production release gates below                                                                                              |
| 2   | OraOne AI Voice Platform      | Answers calls on a Twilio number, spoken replies (Twilio voice or ElevenLabs), transfer to a team number, outbound call campaigns                                                     | Live-needs-account | Needs a Twilio account. No screen or API creates the voice binding. Live calls not verified                                                                                                                     |
| 3   | OraOne WhatsApp Platform      | Inbound and reply handling through Twilio or the Meta WhatsApp Cloud API                                                                                                              | Live-needs-account | Needs a Twilio or Meta account. No screen or API creates the WhatsApp binding. No approved-template support. Account verification is external                                                                   |
| 4   | Omnichannel Communication Hub | One inbox across channels, one customer memory across channels, de-duplication of provider deliveries, STOP handling, Instagram direct messages                                       | Built              | Partial. Staff replies are not delivered outside OraOne on WhatsApp, Instagram, SMS or email. Email replies are not sent by the application. Channel bindings are database-only; Instagram needs a Meta account |
| 5   | Workflow Automation Platform  | Manual, schedule and event triggers; AI, knowledge, condition, transform, delay, approval, webhook and send steps; versions                                                           | Built              | Partial. Send steps need channel bindings and email delivery, which is not connected. The integration trigger is not fired. Notifications are recorded only                                                     |
| 6   | AI Studio & Agent Builder     | Assistants with instructions, knowledge, versions, playground, analytics and installation; operator helper assistants                                                                 | Built              | The wider Product 6 scope is planned: no visual builder and no customer-defined tools                                                                                                                           |
| 7   | Marketplace                   | Built-in catalogue: eight agent templates, one workflow recipe, two integration blueprints                                                                                            | Built              | No third-party publishing. Integration blueprints need the provider's OAuth settings on the server                                                                                                              |
| 8   | Mobile Applications           | Not in this repository. A signed message endpoint for a mobile or desktop SDK exists in the code                                                                                      | Planned            | No mobile application code here                                                                                                                                                                                 |
| 9   | Enterprise Edition            | Role-based access, platform roles, tenant isolation tests, audit records, the configuration console                                                                                   | Built              | Partial. No SSO, SAML, OIDC or SCIM. No enterprise deployment controls. No admin log viewer                                                                                                                     |
| 10  | OraOne OS                     | The name of the signed-in home page (`/studio`), which lists the product areas and their status                                                                                       | Planned            | Long-term vision. Not a product yet                                                                                                                                                                             |

## Capabilities that cut across products

| Capability                                       | Lives in                            | Status             | Blockers                                                                                                                                                             |
| ------------------------------------------------ | ----------------------------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Calls (outbound campaigns)                       | Product 2                           | Live-needs-account | Needs the voice binding (no screen or API creates it) and a Twilio account. Campaigns advance only on Twilio callbacks                                               |
| Marketing (contact forms, consent and campaigns) | Not a separate portfolio product    | Built              | Partial. Email delivery is not connected. SMS and WhatsApp sends need bindings. Campaigns run inside the request                                                     |
| Leads and import                                 | Product 1                           | Built              | Imported consent is self-attested, and is recorded as such                                                                                                           |
| Integrations (OAuth connect)                     | Product 1                           | Live-needs-account | Each provider needs its own OAuth client on the server. Six providers can connect. Only Google Drive syncs data. Zapier, Make and inbound triggers are not available |
| Outbound webhooks                                | Product 1                           | Built              | Customer endpoints must be HTTPS and public                                                                                                                          |
| Configuration console                            | Product 1 (platform administration) | Built              | Saved values depend on the encryption key. Publishing takes effect after an API restart. Other admin pages are empty states until their services are connected       |

## Product 1 release gates

Product 1 is in active development. Production availability is not claimed here. The following
evidence is still required, and is separate from the code:

- live identity, with sign-in codes delivered by a verified mail service;
- live provider tests for OpenRouter, and for any channel you enable;
- provider webhooks verified on the public HTTPS address;
- backup and restore evidence, as described in [BACKUP-RESTORE](operations/BACKUP-RESTORE.md);
- a deployment check on the target server, following [DEPLOYMENT](operations/DEPLOYMENT.md) and
  [HOSTINGER-DEPLOYMENT](HOSTINGER-DEPLOYMENT.md);
- cost controls (rate limits, `AI_FORCE_MODEL` or plan limits) confirmed for the expected load;
- a hosted CI run on the commit being released. The 14 October 2026 audit recorded earlier hosted
  runs, not runs on the audited checkpoint;
- owner approval of the release commit. A clean working tree is not a release approval.

## Product 1 evidence boundary

The current repository contains code for website agents, chat and public API routes, knowledge
ingestion and retrieval, leads, workflows, integrations, the admin configuration console, billing
foundations, tenant administration, RBAC, widget delivery, and webhook foundations. A similarly named
screen, route, or prototype does not make a future standalone product launched or commercially
available.

Production availability is not claimed here. Live identity, provider, payment, external webhook,
backup/restore, deployment, and cost-control gates remain separate evidence requirements.

## Shared ecosystem foundations

The intended future ecosystem may share identity, tenant and project governance, an AI gateway,
billing and usage concepts, design-system components, reusable integrations, unified administration,
and cross-product interoperability. These are architectural direction, not proof that every product or
capability exists today.

Do not publish fictional release dates, completion percentages, customer numbers, or availability claims.
