# OraOne product portfolio

The product numbers are identifiers, not a fixed launch or development sequence. Product 1
is the active foundational product. The status below is what the repository's code does
today. It is not a release claim.

This page was updated from the working tree at the time of writing. Much of the code that
supports Products 2 to 6 is not yet committed. Treat the statuses as the state of the code,
and check the release gates before you describe any product to a customer.

Viswatra is documented only as the intended portfolio-level brand direction; this repository does not establish a legal corporate relationship or ownership structure.

## Status by product

| ID  | Product                       | What the code does today                                                                                                                                                                    | Status                                                          | Blockers                                                                                                                                                   |
| --- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | OraOne AI Chat Platform       | Website chat and widgets, knowledge documents and search, assistants, leads, the inbox, team, billing foundations, usage and analytics, API keys, webhooks, the admin configuration console | In active development. Available in code; release gates pending | Production release gates (see below). Working-tree changes not yet committed                                                                               |
| 2   | OraOne AI Voice Platform      | Answers calls on a Twilio number, spoken replies (Twilio voice or ElevenLabs), transfer to a team number, outbound call campaigns                                                           | Blocked by a setup gap                                          | No screen or API creates the voice binding. Live calls not verified                                                                                        |
| 3   | OraOne WhatsApp Platform      | Inbound and reply handling through Twilio or the Meta WhatsApp Cloud API                                                                                                                    | Blocked by a setup gap                                          | No screen or API creates the WhatsApp binding. No approved-template support. Meta and Twilio account verification is external                              |
| 4   | Omnichannel Communication Hub | One inbox across channels, one customer memory across channels, de-duplication of provider deliveries, STOP handling                                                                        | Partly available                                                | Staff replies and email replies are not delivered outside OraOne. Channel bindings are database-only                                                       |
| 5   | Workflow Automation Platform  | Manual, schedule and event triggers; AI, knowledge, condition, transform, delay, approval, webhook and send steps; versions                                                                 | Partly available                                                | Send steps depend on channel bindings and on email delivery, which is not connected. The integration trigger is not fired. Notifications are recorded only |
| 6   | AI Studio & Agent Builder     | Assistants with instructions, knowledge, versions, playground, analytics and installation; operator helper assistants                                                                       | Partly available                                                | No visual builder. No customer-defined tools. Wider Product 6 scope not built                                                                              |
| 7   | Marketplace                   | Built-in catalogue: eight agent templates, one workflow recipe, two integration blueprints                                                                                                  | Partly available                                                | No third-party publishing. Integration blueprints need the provider's OAuth settings on the server                                                         |
| 8   | Mobile Applications           | Not in this repository. A signed message endpoint for a mobile or desktop SDK exists in the code                                                                                            | Not built                                                       | No mobile application code here                                                                                                                            |
| 9   | Enterprise Edition            | Role-based access, platform roles, tenant isolation tests, audit logs, the configuration console                                                                                            | Partly available                                                | No SSO, SAML, OIDC or SCIM found. Enterprise deployment controls are not built                                                                             |
| 10  | OraOne OS                     | Name used for the Studio overview only                                                                                                                                                      | Long-term vision                                                | Not a product yet                                                                                                                                          |

## Capabilities that cut across products

| Capability                                       | Lives in                            | Status                        | Blockers                                                                                                     |
| ------------------------------------------------ | ----------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Calls (outbound campaigns)                       | Product 2                           | Blocked by a setup gap        | Needs the voice binding; campaigns advance only on Twilio callbacks                                          |
| Marketing (contact forms, consent and campaigns) | Not a separate portfolio product    | Partly available              | Email delivery not connected; SMS and WhatsApp sends need bindings. Campaigns run inside the request         |
| Leads and import                                 | Product 1                           | Available                     | Imported consent is self-attested, and is recorded as such                                                   |
| Integrations (OAuth connect)                     | Product 1                           | Partly available              | Six providers can connect. Only Google Drive syncs data. Zapier, Make and inbound triggers are not available |
| Outbound webhooks                                | Product 1                           | Available                     | Customer endpoints must be HTTPS and public                                                                  |
| Configuration console                            | Product 1 (platform administration) | Available in the working tree | Saved values depend on the encryption key. Needs a restart to take effect                                    |

## Product 1 release gates

Product 1 is in active development. Production availability is not claimed here. The
following evidence is still required, and is separate from the code:

- live identity, with sign-in codes delivered by a verified mail service;
- live provider tests for OpenRouter, and for any channel you enable;
- provider webhooks verified on the public HTTPS address;
- backup and restore evidence, as described in [BACKUP-RESTORE](operations/BACKUP-RESTORE.md);
- a deployment check on the target server, following [DEPLOYMENT](operations/DEPLOYMENT.md);
- cost controls (rate limits, `AI_FORCE_MODEL` or plan limits) confirmed for the expected load;
- a hosted CI run on the commit being released. The 14 October 2026 audit recorded earlier
  hosted runs, not runs on the audited checkpoint;
- the working-tree changes committed and reviewed.

## Product 1 evidence boundary

The current repository contains code for website agents, chat and public API routes,
knowledge ingestion and retrieval, leads, workflows, integrations, the admin configuration
console, billing foundations, tenant administration, RBAC, widget delivery, and webhook
foundations. A similarly named screen, route, or prototype does not make a future standalone
product launched or commercially available.

Production availability is not claimed here. Live identity, provider, payment, external
webhook, backup/restore, deployment, and cost-control gates remain separate evidence
requirements.

## Shared ecosystem foundations

The intended future ecosystem may share identity, tenant and project governance, an AI gateway, billing and usage concepts, design-system components, reusable integrations, unified administration, and cross-product interoperability. These are architectural direction, not proof that every product or capability exists today.

Do not publish fictional release dates, completion percentages, customer numbers, or availability claims.
