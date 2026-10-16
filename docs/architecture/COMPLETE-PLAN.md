# OraOne complete plan

The target architecture is shown in [oraone-complete-plan.webp](assets/oraone-complete-plan.webp). Every lead, from any source, is answered by the AI or a human, then recorded in the CRM with its details and conversation history.

## Flow

1. **Sources.** Phone calls (incoming and missed), WhatsApp (messages, voice notes, images and documents), website (contact forms, chat widget, callback requests), integration layer (script tag, NPM package, JS SDK, REST API), email (inquiries, support emails, forwarded leads), social media (Instagram, Facebook, LinkedIn and others), and other sources (Google Business, marketplaces, offline entries, manual import).
2. **OraOne AI agent (intake and orchestration).** Detects the source, understands intent, auto-responds, reads files (CV and documents), extracts details, qualifies the lead, and routes it to the AI or a human.
   - Intent detection: service, pricing, support, job, partnership and more.
   - File and CV parsing: details from PDFs, images and documents.
   - Lead enrichment: location, budget, timeline.
   - Qualification: lead score and scope.
   - Auto reply: an instant response in the same channel.
   - Smart routing: AI or human, based on rules.
3. **Conversation.** The AI handles it by default, or a human takes over.
   - **AI handles conversation (default):** answers questions, shares information and links, collects the required details, handles objections, and qualifies and updates the CRM. It talks in the customer's channel (call, WhatsApp, chat or email).
   - **Human handles conversation (when needed):** the team member gets real-time notifications, sees the full history, uses AI suggestions, updates details manually, and continues in the same channel.
4. **OraOne CRM and unified inbox.** Every lead is recorded automatically: profile, conversation history, parsed details, scope and lead score, attached files, status and owner (AI or human), tasks and reminders, and analytics such as conversion tracking.
5. **Outcomes.** Book a meeting (automatic or manual, with calendar integration), create a task (follow-up, call or email, assigned to a team member), send a follow-up (reminders and sequences over WhatsApp, email or SMS), manage the deal through the pipeline to closure, collaborate (internal notes and mentions), and report (lead sources, conversion, team performance).

## Status in this repository

| Area         | Plan item                                                           | Status                                                            |
| ------------ | ------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Sources      | Phone calls                                                         | Not built                                                         |
| Sources      | WhatsApp                                                            | Not built                                                         |
| Sources      | Website contact forms and chat widget                               | Chat widget built; contact forms not built                        |
| Sources      | Callback requests                                                   | Not built                                                         |
| Sources      | Integration layer: script tag, JS SDK, REST API                     | Built                                                             |
| Sources      | Integration layer: NPM package                                      | Not built                                                         |
| Sources      | Email (inquiries, support, forwarded leads)                         | Not built                                                         |
| Sources      | Social media                                                        | Not built                                                         |
| Sources      | Other sources (Google Business, marketplaces, manual import)        | Not built                                                         |
| Agent        | Intent detection                                                    | Partly built (RAG answers; no intent classification)              |
| Agent        | File and CV parsing                                                 | Not built (document upload exists for knowledge)                  |
| Agent        | Lead enrichment                                                     | Not built                                                         |
| Agent        | Qualification and lead score                                        | Partly built (score and status on leads)                          |
| Agent        | Auto reply in the same channel                                      | Built for web chat only                                           |
| Agent        | Smart routing (AI or human)                                         | Partly built (escalation setting and endpoint)                    |
| Conversation | AI handles conversation                                             | Built for web chat                                                |
| Conversation | Human handles conversation (notifications, history, AI suggestions) | Partly built (inbox and history; no notifications or suggestions) |
| CRM          | Lead profile, conversation history, parsed details                  | Partly built (web only; no parsed details)                        |
| CRM          | Attached files (CV, documents, images)                              | Partly built (knowledge documents only)                           |
| CRM          | Status and owner                                                    | Partly built (status; no owner assignment)                        |
| CRM          | Tasks and reminders                                                 | Not built                                                         |
| CRM          | Analytics and conversion tracking                                   | Partly built (analytics page; no conversion tracking)             |
| Outcomes     | Book meeting                                                        | Not built                                                         |
| Outcomes     | Create task                                                         | Not built                                                         |
| Outcomes     | Send follow-up (WhatsApp, email, SMS)                               | Not built                                                         |
| Outcomes     | Manage deal through pipeline                                        | Partly built (lead status only)                                   |
| Outcomes     | Collaborate (internal notes, mentions)                              | Not built                                                         |
| Outcomes     | Reports                                                             | Partly built (analytics page)                                     |

## Notes

- Channels that need outside accounts (WhatsApp Business, telephony, email, social platforms, calendar) need a feasibility, cost and terms check before integration.
- The product roadmap places voice and WhatsApp in other products. Confirm scope before building channels into Product 1.
