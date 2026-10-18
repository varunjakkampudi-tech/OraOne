# OraOne vision and mission

> **Draft for owner review.** This wording is a proposal, not an approved statement.
> It is built only from existing product statements in this repository (`README.md`,
> `docs/PRODUCT-PORTFOLIO.md`, `docs/architecture/COMPLETE-PLAN.md` and
> `src/content/site/marketing.ts`). It contains no customer claims, results, statistics or
> dates. Do not publish it, or use it on the website or in sales material, until the owner
> confirms it. The open decisions are listed at the end and in `blocker.txt`.

## Vision (draft)

One AI operating system for every conversation: every channel, every customer and every
follow-up in one place, with an AI that answers from the business's own information and
hands over to its team when a person is needed.

## Mission (draft)

Help businesses answer each enquiry quickly and accurately, using their own documents,
and make sure the people who can act on it see it, with its history.

## Principles

These follow from behaviour the code and the public copy already describe.

1. **Answers come from the business's own material.** The assistant answers from the
   documents the business uploads. When those documents do not cover a question, the
   assistant says so rather than inventing an answer. If the model is unavailable, the
   assistant shows the matching passages and marks them as not generated.
2. **People stay in charge of commitments.** The assistant does not confirm appointments.
   Order-specific problems and requests that need judgement go to a person.
3. **No professional advice.** An assistant for a legal or accountancy practice describes
   the services and what to prepare. It gives no legal or tax advice.
4. **Consent and contact limits are enforced by the system.** Outbound calls, workflow
   messages and campaigns check consent, the do-not-contact list, opt-outs, quiet hours
   and a daily attempt cap before anything is sent.
5. **Honest status.** Every capability is labelled as built, live-needs-account or planned.
   OraOne does not describe a planned or unverified capability as live.

## Where OraOne stands today

This is a status summary, not part of the vision. The detailed status is in
[PRODUCT-PORTFOLIO](PRODUCT-PORTFOLIO.md).

- **Website AI chat** is built and is the starting point of the platform. It is not yet
  launched to customers. Production needs a mail service for sign-in codes and an AI
  provider account.
- **Phone, WhatsApp and Instagram** code is in the repository. None of them can be switched
  on by a customer yet, because the link between a number or account and an assistant has
  no screen or API.
- **The omnichannel inbox, workflows and marketplace** are partly built.
- **OraOne OS** is a long-term vision. It is not a product in this repository.

## What this draft does not claim

- No customer numbers, testimonials, results, savings or growth figures. The industry
  examples in the public copy are illustrative workflows, not customers.
- No launch date, availability promise or pricing commitment. Free access is the current
  setting (`ORAONE_FREE_ACCESS_ONLY`), and billing is not part of the offering.
- No statement on data location or on model training. Those need the owner's confirmation
  first (see below).

## Decisions for the owner

1. Confirm or replace the vision and mission wording above.
2. Confirm the target customers. The draft says "businesses" on purpose.
3. Confirm the data statements before they are published: data stored in India (the
   Mumbai server), and customer data not used to train models. Both are pending in
   `blocker.txt` item 12.
4. Confirm whether "OraOne OS" is the name for the long-term vision, as the portfolio
   currently says.
5. Confirm the public copy. `src/content/site/marketing.ts` says phone and WhatsApp are
   "planned", while the portfolio records them as built with setup gaps. One of them must change.
