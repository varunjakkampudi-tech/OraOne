# OraOne: market position and roadmap (October 2026)

This document records the review run on 18 October 2026, after the round-four fixes. It is an
internal planning note, not a claim of product performance. Every price below was read from the
vendor's public page on that date. Re-check before any external use.

## Where OraOne sits

OraOne is closest to a challenger in website AI support for small businesses. It has the technical
base for a customer conversation platform, and an early architecture for a wider AI operating platform.
It has no paying customers and no verified live customer outcomes yet.

## Competitors (public pricing, checked 18 Oct 2026)

| Product      | Public price                                                       | Notable features                                                    | Source                                    |
| ------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------- | ----------------------------------------- |
| Intercom Fin | $0.99 per resolution outcome; seats from $29/mo annual             | Outcome billing, procedure handoffs, prospect qualification         | intercom.com/pricing                      |
| Zendesk AI   | From $19/agent/mo; a per-resolution rate on secondary sources only | Automated resolutions, triage, calls and texts into tickets         | zendesk.com/pricing                       |
| Zoho SalesIQ | Base price not extracted                                           | Up to 10 Zia agents per portal; LLM token allowance on higher tiers | zoho.com/agents/pricing.html              |
| Chatbase     | $40, $150, $500/mo monthly billing                                 | Message credits, team seats, branding removal on paid tiers         | chatbase.co/pricing                       |
| Tidio Lyro   | From $29/mo; $0.58 to $0.65 per conversation on annual billing     | Per-conversation billing, 50 free conversations                     | tidio.com/blog/chatbot-pricing            |
| WATI         | Base fee not extracted; add-on users $24 and $69/user/mo           | WhatsApp API, AI with human handoff, 7-day trial                    | wati.io/pricing                           |
| Freshchat    | $49 per 100 AI sessions after 500 free                             | Freddy AI agent, agent copilot $29/agent/mo                         | freshworks.com/live-chat-software/pricing |
| Tawk.to      | Free; AI Assist from $29/mo                                        | Free plan, 24/7 knowledge-base bot                                  | tawk.to/why-free                          |
| Crisp        | $0, $45, $95, $295 per workspace/mo                                | WhatsApp and SMS channels; multilingual AI on the top tier only     | crisp.chat/en/pricing                     |

Zendesk's per-resolution rate and the WATI and Zoho base prices were not confirmed on the vendor page
during this run.

## Where OraOne can stand out (proposals, not commitments)

1. Quote in rupees, with the WhatsApp message fee passed through at cost. Measure: trial-to-paid conversion.
2. A free starter that needs only UPI or a phone number to sign up. Measure: signup to first live conversation within 24 hours.
3. A monthly cap on per-resolution charges, so bills do not swing with volume. Measure: month-3 churn and bill variance.
4. Hindi and one regional language in the base plan. Measure: non-English conversations resolved without handoff.
5. Shared WhatsApp inbox and human handoff included in the base seat price. Measure: seats per account, time to first human reply.
6. Let the assistant book appointments and take orders, not only answer. Measure: bookings or orders per 100 AI conversations.

None of these can be measured until a live pilot runs. The pricing choices are owner decisions.

## Setup friction (brainstorm, not yet built)

The 15-minute setup goal is blocked by mail delivery and the AI provider key, which must be
configured first. After that, in order of effort:

1. Business hours and handoff contact step (S). Contact fields exist on escalations.
2. Test with your own questions before embedding (S). Uses the existing playground.
3. Embed helper and "check my site" for the owner's web developer (S). Builds on the install step.
4. Add business details by URL or pasted text (M).
5. Industry starter packs (M).
6. First real conversation alert (M). Blocked on mail delivery.
7. Setup progress saved to the account, not the browser (S).
8. Weekly value summary by email (M). Blocked on mail delivery.

## Engineering priorities from the review (status after round four)

Done in code, with tests: project-scoped API keys; explicit widget escalation creating a queue
item; numeric, negation and qualifier checks in grounding; grounding enforced in the signed-in chat
runtime; shared-store API rate limits that fail closed; leased escalation claims; per-recipient
escalation retry; outbox backoff; scheduler in-flight tracking on shutdown; proxy waits for healthy
services; worker restarts when a loop dies; widget visitors get no knowledge base unless the owner binds one;
visitor memory keyed per widget; keys stop working when their project is deleted or archived; crypto and
market questions are out of scope.

Still open, with the reason:

- Citation verification (the cited passage must support the sentence). Needs labelled examples.
- Confidence-based handoff. Needs calibration data from real conversations.
- Semantic (model-based) entailment. Adds cost and latency; a product decision.
- Streaming replies are not grounding-checked. Needs buffering, a product decision.
- Usage metering on the agentless chat path, and a model allowlist for caller-chosen models.
- Subscription enforcement on public API routes (the authorization pipeline is not called on v1 routes).
- Dashboard screen for the escalation queue.
- Marketing campaigns still send during the run rather than from a durable queue.
- Per-organization daily spending caps.
- Browser tests against a real backend.
