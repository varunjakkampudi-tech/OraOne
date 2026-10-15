# Route acceptance (283-entry reference inventory)

Generated from `frontend/e2e/real-route-audit.mjs`. The audit signs in as the local QA account (a normal `user`, workspace owner) against the **real local API**, visits every non-layout destination (`$param` → synthetic UUID), and runs axe-core (WCAG 2.0/2.1/2.2 A+AA, critical/serious only) at 1440 px plus horizontal-overflow checks at 390/768/1440 px.
Classification uses the runtime final URL plus the `App.js` route element. Rendering is **not** functional acceptance; see the Product 1 ledger for persisted-operation evidence.
The supplied 272-path product brief was not provided in the repository or this task, so reconciliation is against the 283-entry `route-inventory.json` (7 layout entries are not navigable).

## Summary

- functional page: 170
- alias / redirect: 84
- restricted (platform admin): 19
- planned-product preview: 2
- restricted (auth required): 1

- Destinations audited: 276
- With API 5xx: 0
- With console/page errors: 146
- With axe critical/serious violations (1440 px): 0
- With horizontal overflow at any width: 0
- Navigation timeouts: 0

| Reference path | Final path | Class | H1 | 5xx | Console errs | axe (1440) | Overflow 390/768/1440 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/` | `/` | functional page | OraOne | 0 | 0 | none | -/-/- |
| `/about` | `/about` | functional page | Building the futureof conversations | 0 | 0 | none | -/-/- |
| `/acceptable-use` | `/terms` | alias / redirect | Terms of Service | 0 | 0 | none | -/-/- |
| `/app` | `/app/dashboard` | alias / redirect | Good morning, OraOne | 0 | 0 | none | -/-/- |
| `/app/account` | `/app/settings` | alias / redirect | Settings | 0 | 0 | none | -/-/- |
| `/app/account/notifications` | `/app/account/notifications` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/account/preferences` | `/app/account/preferences` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/account/profile` | `/app/account/profile` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/account/security` | `/app/account/security` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/account/sessions` | `/app/account/sessions` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/activity` | `/app/activity` | functional page | Activity & Notifications | 0 | 0 | none | -/-/- |
| `/app/analytics` | `/app/analytics` | functional page | Analytics | 0 | 0 | none | -/-/- |
| `/app/analytics/customer-360` | `/app/customer-360` | alias / redirect | Customer 360° | 0 | 3 | none | -/-/- |
| `/app/analytics/optimization` | `/app/analytics/optimization` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/analytics/revenue` | `/app/analytics/revenue` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/billing` | `/app/billing` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/billing/invoices` | `/app/billing` | alias / redirect | Plans & subscription | 0 | 0 | none | -/-/- |
| `/app/billing/payment-methods` | `/app/billing` | alias / redirect | Plans & subscription | 0 | 0 | none | -/-/- |
| `/app/billing/plans` | `/app/billing` | alias / redirect | Plans & subscription | 0 | 0 | none | -/-/- |
| `/app/billing/subscription` | `/app/billing` | alias / redirect | Plans & subscription | 0 | 0 | none | -/-/- |
| `/app/billing/usage` | `/app/usage` | alias / redirect | Usage & limits | 0 | 0 | none | -/-/- |
| `/app/customers` | `/app/leads` | alias / redirect | Leads | 0 | 0 | none | -/-/- |
| `/app/customers/$customerId` | `/app/customers/00000000-0000-4000-8000-000000000999` | functional page | Customer profile | 0 | 2 | none | -/-/- |
| `/app/inbox` | `/app/conversations` | alias / redirect | Unified Inbox | 0 | 0 | none | -/-/- |
| `/app/inbox/$conversationId` | `/app/conversations/00000000-0000-4000-8000-000000000999` | alias / redirect | Unified Inbox | 0 | 3 | none | -/-/- |
| `/app/integrations` | `/app/integrations` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/integrations/$id` | `/app/integrations/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/integrations/catalog` | `/app/integrations/catalog` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/integrations/connected` | `/app/integrations/connected` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/integrations/webhooks` | `/app/integrations/webhooks` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/leads` | `/app/leads` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/leads/$leadId` | `/app/leads/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/notifications` | `/app/notifications` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products` | `/app/products` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/ai-studio` | `/app/products/ai-studio` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/ai-studio/agents` | `/app/products/ai-studio/agents` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/ai-studio/agents/$id` | `/app/products/ai-studio/agents/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/ai-studio/agents/$id/builder` | `/app/products/ai-studio/agents/00000000-0000-4000-8000-000000000999/builder` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/ai-studio/agents/new` | `/app/products/ai-studio/agents/new` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/ai-studio/analytics` | `/app/products/ai-studio/analytics` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/ai-studio/evaluations` | `/app/products/ai-studio/evaluations` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/ai-studio/knowledge` | `/app/products/ai-studio/knowledge` | functional page | Knowledge | 0 | 0 | none | -/-/- |
| `/app/products/ai-studio/models` | `/app/products/ai-studio/models` | functional page | Models | 0 | 0 | none | -/-/- |
| `/app/products/ai-studio/overview` | `/app/products/ai-studio/overview` | functional page | AI Studio & Agent Builder | 0 | 0 | none | -/-/- |
| `/app/products/ai-studio/playground` | `/app/products/ai-studio/playground` | functional page | Playground | 0 | 0 | none | -/-/- |
| `/app/products/ai-studio/prompts` | `/app/products/ai-studio/prompts` | functional page | Prompts | 0 | 0 | none | -/-/- |
| `/app/products/ai-studio/publishing` | `/app/products/ai-studio/publishing` | functional page | Publishing | 0 | 0 | none | -/-/- |
| `/app/products/ai-studio/settings` | `/app/products/ai-studio/settings` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/products/ai-studio/tools` | `/app/products/ai-studio/tools` | functional page | Tools | 0 | 0 | none | -/-/- |
| `/app/products/ai-studio/traces` | `/app/products/ai-studio/traces` | functional page | Traces | 0 | 0 | none | -/-/- |
| `/app/products/ai-studio/versions` | `/app/products/ai-studio/versions` | functional page | Versions | 0 | 0 | none | -/-/- |
| `/app/products/automation` | `/app/products/automation` | functional page | Workflow Automation Platform | 0 | 0 | none | -/-/- |
| `/app/products/automation/actions` | `/app/products/automation/actions` | functional page | Actions | 0 | 0 | none | -/-/- |
| `/app/products/automation/analytics` | `/app/products/automation/analytics` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/errors` | `/app/products/automation/errors` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/executions` | `/app/products/automation/executions` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/executions/$id` | `/app/products/automation/executions/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/overview` | `/app/products/automation/overview` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/settings` | `/app/products/automation/settings` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/templates` | `/app/products/automation/templates` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/triggers` | `/app/products/automation/triggers` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/workflows` | `/app/products/automation/workflows` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/workflows/$id` | `/app/products/automation/workflows/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/automation/workflows/$id/builder` | `/app/products/automation/workflows/00000000-0000-4000-8000-000000000999/builder` | functional page | Workflow builder | 0 | 0 | none | -/-/- |
| `/app/products/automation/workflows/new` | `/app/products/automation/workflows/new` | functional page | Create a workflow | 0 | 0 | none | -/-/- |
| `/app/products/chat` | `/app/products/chat` | functional page | Chat workspace | 0 | 0 | none | -/-/- |
| `/app/products/chat/analytics` | `/app/analytics` | alias / redirect | Analytics | 0 | 0 | none | -/-/- |
| `/app/products/chat/assistants` | `/app/agents` | alias / redirect | AI assistants | 0 | 0 | none | -/-/- |
| `/app/products/chat/assistants/$id` | `/app/agents` | alias / redirect | AI assistants | 0 | 2 | none | -/-/- |
| `/app/products/chat/assistants/$id/analytics` | `/app/products/chat/assistants/00000000-0000-4000-8000-000000000999/analytics` | functional page | Agent analytics | 0 | 2 | none | -/-/- |
| `/app/products/chat/assistants/$id/behavior` | `/app/agents` | alias / redirect | AI assistants | 0 | 2 | none | -/-/- |
| `/app/products/chat/assistants/$id/editor` | `/app/agents` | alias / redirect | AI assistants | 0 | 2 | none | -/-/- |
| `/app/products/chat/assistants/$id/install` | `/app/products/chat/assistants/00000000-0000-4000-8000-000000000999/install` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/assistants/$id/knowledge` | `/app/products/chat/assistants/00000000-0000-4000-8000-000000000999/knowledge` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/assistants/$id/playground` | `/app/products/chat/assistants/00000000-0000-4000-8000-000000000999/playground` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/assistants/$id/quality` | `/app/products/chat/assistants/00000000-0000-4000-8000-000000000999/quality` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/assistants/$id/versions` | `/app/products/chat/assistants/00000000-0000-4000-8000-000000000999/versions` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/assistants/$id/widget` | `/app/products/chat/assistants/00000000-0000-4000-8000-000000000999/widget` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/assistants/demo/instructions` | `/app/products/chat/assistants/demo/instructions` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/assistants/demo/models` | `/app/products/chat/assistants/demo/models` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/assistants/demo/settings` | `/app/products/chat/assistants/demo/settings` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/assistants/new` | `/app/products/chat/assistants/new` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/conversations` | `/app/products/chat/conversations` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/knowledge` | `/app/products/chat/knowledge` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/knowledge/coverage` | `/app/products/chat/knowledge/coverage` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/knowledge/documents` | `/app/products/chat/knowledge/documents` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/knowledge/search` | `/app/products/chat/knowledge/search` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/knowledge/websites` | `/app/products/chat/knowledge/websites` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/settings` | `/app/products/chat/settings` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/chat/templates` | `/app/products/chat/templates` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/enterprise` | `/app/products/enterprise` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/enterprise/access` | `/app/products/enterprise/access` | functional page | Access | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/audit` | `/app/products/enterprise/audit` | functional page | Audit | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/compliance` | `/app/products/enterprise/compliance` | functional page | Compliance | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/governance` | `/app/products/enterprise/governance` | functional page | Governance | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/overview` | `/app/products/enterprise/overview` | functional page | Enterprise Edition | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/provisioning` | `/app/products/enterprise/provisioning` | functional page | Provisioning | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/reports` | `/app/products/enterprise/reports` | functional page | Reports | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/security` | `/app/products/enterprise/security` | functional page | Security | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/settings` | `/app/products/enterprise/settings` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/sso` | `/app/products/enterprise/sso` | functional page | Single sign-on | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/support` | `/app/products/enterprise/support` | functional page | Support | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/teams` | `/app/products/enterprise/teams` | functional page | Teams | 0 | 0 | none | -/-/- |
| `/app/products/enterprise/usage` | `/app/products/enterprise/usage` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace` | `/app/products/marketplace` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/categories` | `/app/products/marketplace/categories` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/developer` | `/app/products/marketplace/developer` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/explore` | `/app/products/marketplace/explore` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/installed` | `/app/products/marketplace/installed` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/integrations/$id` | `/app/products/marketplace/integrations/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/items/$id` | `/app/products/marketplace/items/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/publishers/$id` | `/app/products/marketplace/publishers/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/settings` | `/app/products/marketplace/settings` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/submissions` | `/app/products/marketplace/submissions` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/marketplace/templates/$id` | `/app/products/marketplace/templates/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/mobile` | `/app/products/mobile` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/mobile/availability` | `/app/products/mobile/availability` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/mobile/features` | `/app/products/mobile/features` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/omnichannel` | `/app/products/omnichannel` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/omnichannel/analytics` | `/app/products/omnichannel/analytics` | functional page | Analytics | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/assignments` | `/app/products/omnichannel/assignments` | functional page | Assignments | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/channels` | `/app/products/omnichannel/channels` | functional page | Channels | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/channels/connect` | `/app/products/omnichannel/channels/connect` | functional page | Connect a channel | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/conversations` | `/app/products/omnichannel/conversations` | functional page | Conversations | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/customers` | `/app/products/omnichannel/customers` | functional page | Customers | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/overview` | `/app/products/omnichannel/overview` | functional page | Omnichannel Communication Hub | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/routing` | `/app/products/omnichannel/routing` | functional page | Routing | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/segments` | `/app/products/omnichannel/segments` | functional page | Segments | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/settings` | `/app/products/omnichannel/settings` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/sla` | `/app/products/omnichannel/sla` | functional page | Service levels | 0 | 0 | none | -/-/- |
| `/app/products/omnichannel/team-inbox` | `/app/products/omnichannel/team-inbox` | functional page | Team inbox | 0 | 0 | none | -/-/- |
| `/app/products/oraone-os` | `/app/products/oraone-os` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/business-graph` | `/app/products/oraone-os/business-graph` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/command-center` | `/app/products/oraone-os/command-center` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/customer-lifecycle` | `/app/products/oraone-os/customer-lifecycle` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/governance` | `/app/products/oraone-os/governance` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/intelligence` | `/app/products/oraone-os/intelligence` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/operations` | `/app/products/oraone-os/operations` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/orchestration` | `/app/products/oraone-os/orchestration` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/overview` | `/app/products/oraone-os/overview` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/reports` | `/app/products/oraone-os/reports` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/settings` | `/app/products/oraone-os/settings` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/oraone-os/workflows` | `/app/products/oraone-os/workflows` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/voice` | `/app/products/voice` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/voice/agents` | `/app/products/voice/agents` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/voice/agents/$id` | `/app/products/voice/agents/00000000-0000-4000-8000-000000000999` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/voice/agents/new` | `/app/products/voice/agents/new` | functional page | Create an agent | 0 | 0 | none | -/-/- |
| `/app/products/voice/analytics` | `/app/products/voice/analytics` | functional page | Analytics | 0 | 0 | none | -/-/- |
| `/app/products/voice/calls` | `/app/products/voice/calls` | functional page | Calls | 0 | 0 | none | -/-/- |
| `/app/products/voice/calls/$id` | `/app/products/voice/calls/00000000-0000-4000-8000-000000000999` | functional page | 00000000 0000 4000 8000 000000000999 | 0 | 0 | none | -/-/- |
| `/app/products/voice/campaigns` | `/app/products/voice/campaigns` | functional page | Campaigns | 0 | 0 | none | -/-/- |
| `/app/products/voice/numbers` | `/app/products/voice/numbers` | functional page | Phone numbers | 0 | 0 | none | -/-/- |
| `/app/products/voice/overview` | `/app/products/voice/overview` | functional page | OraOne AI Voice Platform | 0 | 0 | none | -/-/- |
| `/app/products/voice/playground` | `/app/products/voice/playground` | functional page | Playground | 0 | 0 | none | -/-/- |
| `/app/products/voice/settings` | `/app/products/voice/settings` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/products/whatsapp` | `/app/products/whatsapp` | functional page | OraOne WhatsApp Platform | 0 | 0 | none | -/-/- |
| `/app/products/whatsapp/accounts` | `/app/products/whatsapp/accounts` | functional page | Business accounts | 0 | 0 | none | -/-/- |
| `/app/products/whatsapp/agents` | `/app/products/whatsapp/agents` | functional page | Agents | 0 | 0 | none | -/-/- |
| `/app/products/whatsapp/agents/new` | `/app/products/whatsapp/agents/new` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/analytics` | `/app/products/whatsapp/analytics` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/automation` | `/app/products/whatsapp/automation` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/campaigns` | `/app/products/whatsapp/campaigns` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/connect` | `/app/products/whatsapp/connect` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/contacts` | `/app/products/whatsapp/contacts` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/conversations` | `/app/products/whatsapp/conversations` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/overview` | `/app/products/whatsapp/overview` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/settings` | `/app/products/whatsapp/settings` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/templates` | `/app/products/whatsapp/templates` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/products/whatsapp/templates/new` | `/app/products/whatsapp/templates/new` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/search` | `/app/search` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/settings` | `/app/settings` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/settings/api-keys` | `/app/settings/api-keys` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/settings/audit` | `/app/settings/audit` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/settings/billing` | `/app/billing` | alias / redirect | Plans & subscription | 0 | 0 | none | -/-/- |
| `/app/settings/branding` | `/app/branding` | alias / redirect | Branding | 0 | 0 | none | -/-/- |
| `/app/settings/data` | `/app/settings/data` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/settings/developers` | `/app/developers` | alias / redirect | Developer Platform | 0 | 0 | none | -/-/- |
| `/app/settings/general` | `/app/settings/general` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/settings/members` | `/app/team` | alias / redirect | Team & Access | 0 | 0 | none | -/-/- |
| `/app/settings/models` | `/app/ai-models` | alias / redirect | AI Model Router | 0 | 0 | none | -/-/- |
| `/app/settings/notifications` | `/app/settings/notifications` | functional page | Settings | 0 | 0 | none | -/-/- |
| `/app/settings/operations` | `/app/operations` | alias / redirect | Operations & Security | 0 | 0 | none | -/-/- |
| `/app/settings/projects` | `/app/settings/projects` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/settings/security` | `/app/settings/security` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/settings/tasks` | `/app/settings/tasks` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/settings/teams` | `/app/settings/teams` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/settings/webhooks` | `/app/settings/webhooks` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/team` | `/app/team` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/team/activity` | `/app/team/activity` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/team/invitations` | `/app/team/invitations` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/team/members` | `/app/team/members` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/team/permissions` | `/app/team/permissions` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/team/roles` | `/app/team/roles` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/workspaces` | `/app/workspaces` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/workspaces/$id/settings` | `/app/workspaces/00000000-0000-4000-8000-000000000999/settings` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/app/workspaces/new` | `/app/workspaces/new` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/auth/callback` | `/auth/callback` | functional page |  | 0 | 3 | none | -/-/- |
| `/auth/error` | `/login` | restricted (auth required) | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/auth/forgot-password` | `/forgot-password` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/auth/invitation` | `/signup` | alias / redirect | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/auth/mfa` | `/verify-email` | alias / redirect | Verify Your Email | 0 | 3 | none | -/-/- |
| `/auth/reset-password` | `/app/dashboard` | alias / redirect | Good morning, OraOne | 0 | 0 | none | -/-/- |
| `/auth/session-expired` | `/app/dashboard` | alias / redirect | Good morning, OraOne | 0 | 0 | none | -/-/- |
| `/auth/sign-in` | `/app/dashboard` | alias / redirect | Good morning, OraOne | 0 | 0 | none | -/-/- |
| `/auth/sign-up` | `/app/dashboard` | alias / redirect | Good morning, OraOne | 0 | 0 | none | -/-/- |
| `/auth/verify-email` | `/verify-email` | alias / redirect | Verify Your Email | 0 | 0 | none | -/-/- |
| `/changelog` | `/products` | alias / redirect | The OraOne ecosystem | 0 | 0 | none | -/-/- |
| `/contact` | `/contact` | functional page | Let's talk aboutyour business | 0 | 0 | none | -/-/- |
| `/cookies` | `/cookie-policy` | alias / redirect | Cookie Policy | 0 | 0 | none | -/-/- |
| `/demo` | `/products` | alias / redirect | The OraOne ecosystem | 0 | 0 | none | -/-/- |
| `/docs` | `/documentation` | alias / redirect | Build, ship and scale with OraOne. | 0 | 0 | none | -/-/- |
| `/docs/ai-chat` | `/documentation` | alias / redirect | Build, ship and scale with OraOne. | 0 | 0 | none | -/-/- |
| `/docs/api` | `/documentation` | alias / redirect | Build, ship and scale with OraOne. | 0 | 0 | none | -/-/- |
| `/docs/getting-started` | `/documentation` | alias / redirect | Build, ship and scale with OraOne. | 0 | 0 | none | -/-/- |
| `/docs/integrations` | `/documentation` | alias / redirect | Build, ship and scale with OraOne. | 0 | 0 | none | -/-/- |
| `/docs/webhooks` | `/documentation` | alias / redirect | Build, ship and scale with OraOne. | 0 | 0 | none | -/-/- |
| `/features` | `/products` | alias / redirect | The OraOne ecosystem | 0 | 0 | none | -/-/- |
| `/help` | `/documentation` | alias / redirect | Build, ship and scale with OraOne. | 0 | 0 | none | -/-/- |
| `/help/contact` | `/contact` | alias / redirect | Let's talk aboutyour business | 0 | 0 | none | -/-/- |
| `/integrations` | `/integrations` | functional page | Integrate with Your Favorite Tools | 0 | 0 | none | -/-/- |
| `/onboarding` | `/onboarding/agent` | alias / redirect | Welcome to OraOne! 👋 | 0 | 0 | none | -/-/- |
| `/onboarding/ai-chat` | `/onboarding/ai-chat` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/onboarding/complete` | `/onboarding/complete` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/onboarding/install` | `/onboarding/install` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/onboarding/knowledge` | `/onboarding/knowledge` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/onboarding/profile` | `/onboarding/profile` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/onboarding/test` | `/onboarding/test` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/onboarding/use-case` | `/onboarding/use-case` | functional page | Couldn’t verify your session | 0 | 3 | none | -/-/- |
| `/onboarding/workspace` | `/onboarding/workspace` | functional page | Tell us about your business | 0 | 0 | none | -/-/- |
| `/owner` | `/owner` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/ai-models` | `/owner/ai-models` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/audit` | `/owner/audit` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/billing` | `/owner/billing` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/entitlements` | `/owner/entitlements` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/errors` | `/owner/errors` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/feature-flags` | `/owner/feature-flags` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/infrastructure` | `/owner/infrastructure` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/monitoring` | `/owner/monitoring` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/organizations` | `/owner/organizations` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/organizations/$id` | `/owner/organizations/00000000-0000-4000-8000-000000000999` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/products` | `/owner/products` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/security` | `/owner/security` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/settings` | `/owner/settings` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/subscriptions` | `/owner/subscriptions` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/support` | `/owner/support` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/usage` | `/owner/usage` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/users` | `/owner/users` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/owner/users/$id` | `/owner/users/00000000-0000-4000-8000-000000000999` | restricted (platform admin) | Restricted area | 0 | 2 | none | -/-/- |
| `/platform` | `/products` | alias / redirect | The OraOne ecosystem | 0 | 0 | none | -/-/- |
| `/pricing` | `/pricing` | functional page | Simple, transparent pricing | 0 | 0 | none | -/-/- |
| `/privacy` | `/privacy` | functional page | Privacy Policy | 0 | 0 | none | -/-/- |
| `/products` | `/products` | functional page | The OraOne ecosystem | 0 | 0 | none | -/-/- |
| `/products/ai-chat` | `/products/ai-chat` | functional page | OraOne AI Chat Platform | 0 | 0 | none | -/-/- |
| `/products/ai-studio` | `/products/ai-studio` | functional page | AI Studio & Agent Builder | 0 | 0 | none | -/-/- |
| `/products/ai-voice` | `/products/ai-voice` | functional page | OraOne AI Voice Platform | 0 | 0 | none | -/-/- |
| `/products/automation` | `/products/automation` | functional page | Workflow Automation Platform | 0 | 0 | none | -/-/- |
| `/products/enterprise` | `/products/enterprise` | functional page | Enterprise Edition | 0 | 0 | none | -/-/- |
| `/products/marketplace` | `/products/marketplace` | functional page | Marketplace | 0 | 0 | none | -/-/- |
| `/products/mobile` | `/products/mobile` | functional page | Mobile Applications | 0 | 0 | none | -/-/- |
| `/products/omnichannel` | `/products/omnichannel` | functional page | Omnichannel Communication Hub | 0 | 0 | none | -/-/- |
| `/products/oraone-os` | `/products/oraone-os` | functional page | OraOne OS | 0 | 0 | none | -/-/- |
| `/products/whatsapp` | `/products/whatsapp` | functional page | OraOne WhatsApp Platform | 0 | 0 | none | -/-/- |
| `/refund-policy` | `/terms` | alias / redirect | Terms of Service | 0 | 0 | none | -/-/- |
| `/reset-password` | `/app/dashboard` | alias / redirect | Good morning, OraOne | 0 | 0 | none | -/-/- |
| `/roadmap` | `/products` | alias / redirect | The OraOne ecosystem | 0 | 0 | none | -/-/- |
| `/security` | `/security` | functional page | Security and data handling | 0 | 0 | none | -/-/- |
| `/solutions` | `/solutions` | functional page | Solutions for Every Industry | 0 | 0 | none | -/-/- |
| `/solutions/customer-support` | `/solutions` | alias / redirect | Solutions for Every Industry | 0 | 0 | none | -/-/- |
| `/solutions/enterprise` | `/solutions` | alias / redirect | Solutions for Every Industry | 0 | 0 | none | -/-/- |
| `/solutions/lead-generation` | `/solutions` | alias / redirect | Solutions for Every Industry | 0 | 0 | none | -/-/- |
| `/solutions/sales` | `/solutions` | alias / redirect | Solutions for Every Industry | 0 | 0 | none | -/-/- |
| `/solutions/small-business` | `/solutions` | alias / redirect | Solutions for Every Industry | 0 | 0 | none | -/-/- |
| `/status` | `/contact` | alias / redirect | Let's talk aboutyour business | 0 | 0 | none | -/-/- |
| `/studio` | `/studio` | planned-product preview | AI Studio & Agent Builder | 0 | 0 | none | -/-/- |
| `/studio/assistants/$id` | `/studio/assistants/00000000-0000-4000-8000-000000000999` | planned-product preview | 00000000 0000 4000 8000 000000000999 | 0 | 0 | none | -/-/- |
| `/terms` | `/terms` | functional page | Terms of Service | 0 | 0 | none | -/-/- |
