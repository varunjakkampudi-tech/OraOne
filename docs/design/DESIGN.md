# OraOne interface design system

This document records implementation rules for migrating approved OraOne
screens into the existing application. `DESIGN_SYSTEM.md` remains the
canonical visual and shell specification; the linked Stitch project is the
design-source reference. Keep the current logo, colors, typography, and
authenticated shell intact while connecting page designs to the FastAPI-backed
application.

## Visual direction

Calm, high-clarity enterprise software: a navy workspace frame, white task
surfaces, restrained blue actions, and cyan reserved for AI-specific signals.
Use density where it helps people scan operational records; use open space to
separate page purpose from secondary controls. Product concepts must be
visibly distinguished from released, connected services.

## Color roles

- **OraOne navy** (`#0F172A`) — global shell, headings, primary ink.
- **OraOne blue** (`#2563EB`) — primary actions, active navigation and focus.
- **Telemetry cyan** (`#06B6D4`) — AI and knowledge-grounding indicators only.
- **Canvas** — use the background token specified in `DESIGN_SYSTEM.md` and
  implemented by the existing shell; do not introduce a conflicting canvas
  color.
- **Surface** (`#FFFFFF`) — forms, dialogs, data panels and cards.
- **Muted text** (`#64748B`) — supporting copy and metadata.
- **Stroke** (`#E2E8F0`) and **hairline** (`#F1F5F9`) — outer boundaries and
  low-emphasis internal dividers.
- Status colors retain their semantic roles: success `#16A34A`, warning
  `#F59E0B`, danger `#B42318`.

Avoid introducing a competing palette, decorative neon, or gradients that
obscure status. Existing branded gradients may remain where already approved.

## Typography

- **UI and body:** Inter, matching the current application and Stitch system.
- **Code and identifiers:** preserve the system monospace stack used by the
  existing application.
- Use sentence-case labels, a compact heading scale, readable body leading,
  and tabular numerals for aligned metrics.

## Layout and components

- Preserve the current global navy header, sidebar, workspace/project context,
  and original OraOne logo.
- Follow the layout, spacing, and gutter tokens in `DESIGN_SYSTEM.md`; cap
  reading widths while allowing operational tables to use the available
  canvas.
- Use borders and whitespace before adding elevation. Cards should express
  grouping or hierarchy, not decorate every element.
- Put form labels above inputs, helper text near the relevant control, and
  actionable validation beside the field.
- Empty, loading, unavailable, and error states must explain what is known and
  what the user can do next. Never fill missing service data with invented
  metrics or success states.
- Status badges must distinguish **active**, **planned**, and **long-term
  vision** consistently.

## Responsive and interaction rules

- Collapse multi-column content into a readable single column on narrow
  screens; no horizontal page overflow.
- Keep primary touch targets at least 44 px where practical and provide clear
  keyboard focus.
- Respect reduced-motion preferences. Motion should confirm user action, not
  continuously distract from task content.
- Detail routes must retain record identity in the URL and show an explicit
  unavailable state when that record is not available in the active workspace.

## Implementation boundary

Product 1 is the only active product. Products 2–9 are planned and Product 10
is the long-term vision. Their screens may be presented as design previews, but
must state that live services and data are not connected. Google integrations
remain separate Product 1 capabilities and must not be removed as part of this
product-status distinction.
