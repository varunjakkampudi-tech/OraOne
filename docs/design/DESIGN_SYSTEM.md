# OraOne design system reference

## Authority and scope

The user-designated approved OraOne dashboard is the canonical shell reference. Preserve its logo/wordmark, navy header, workspace switcher, sidebar structure, icon style, typography, spacing, blue accent, content background, and card treatment. Change only page content and the appropriate single active navigation state unless the user authorizes a shell change.

The existing Stitch project is `OraOne Unified AI Design System`: <https://stitch.withgoogle.com/projects/3000613067453175610>. Its listed tokens are Primary `#2563EB`, Secondary `#0F172A`, Tertiary `#06B6D4`, Neutral `#F8F7F4`, and Inter. Existing OraOne logo assets are in that project; do not generate a replacement logo. Confirm repository asset usage before implementation.

## Customer workspace navigation

Use the approved information architecture supplied for this design effort:

- Workspace: Overview, Unified Inbox, Customers & Leads, Analytics
- AI Products: AI Chat, AI Voice, WhatsApp, Omnichannel, Automation, AI Studio
- Management: Integrations, Team & Access, Billing & Usage, Workspace Settings
- Footer: System Status, Help & Support

Do not add a customer-facing Owner Console, Super Admin, OraOne OS, preview controls, or Stitch annotations. Keep platform administration separate. Workspace role labels must not be presented as platform roles.

## Truthful product representation

Product 1 is the active implementation. Products 2–9 are planned; Product 10 is a long-term vision. A navigation item or reference shell is not proof of an implemented capability. Use clearly labelled illustrative sample data in design-only screens; never present it as live. Avoid fabricated uptime, SLA, delivery, or production claims.

## Shared interaction rules

- Exactly one relevant navigation item is active.
- Workspace context is visible and consistent, but is not described as an authorization boundary.
- Keep sidebar navigation independently scrollable and its footer fixed within the viewport.
- Include loading, empty, error, permission-denied, and responsive states where they are meaningful to the real route.
- Use accessible names for icon-only actions and preserve keyboard focus visibility.
