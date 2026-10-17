# OraOne roadmap

Product numbers identify the portfolio and do not prescribe a release sequence. Product 1 is active development; Products 2–9 are planned; Product 10 is the long-term vision. See [Product portfolio](PRODUCT-PORTFOLIO.md) for exact scopes.

## Current focus — Product 1

- Keep email-only email-code and PostgreSQL-backed RBAC aligned.
- Complete authorized live authentication and protected-API verification.
- Finish webhook external-delivery, restart, and dead-letter drills.
- Establish repeatable backup/restore and deployment evidence.
- Reduce lint warnings that indicate real defects.

## Portfolio status

| Product                       | Status (see the portfolio for blockers)  |
| ----------------------------- | ---------------------------------------- |
| OraOne AI Chat Platform       | In active development                    |
| OraOne AI Voice Platform      | Blocked by a setup gap (voice binding)   |
| OraOne WhatsApp Platform      | Blocked by a setup gap (channel binding) |
| Omnichannel Communication Hub | Partly available                         |
| Workflow Automation Platform  | Partly available                         |
| AI Studio & Agent Builder     | Partly available                         |
| Marketplace                   | Partly available                         |
| Mobile Applications           | Not built in this repository             |
| Enterprise Edition            | Partly available                         |
| OraOne OS                     | Long-term vision                         |

## Shared foundations

The intended ecosystem may share identity, tenant and project governance, AI gateway capabilities, billing and usage concepts, design-system components, reusable integrations, unified administration, and future cross-product interoperability. These are future design directions, not shipped product claims.

## Release gates

- Add durable monetary/token AI budget reservation and reconciliation beyond daily message quotas.
- Complete signed payment-provider sandbox lifecycle tests.
- Add independent reviews for crawling, uploads, prompt injection, billing, and tenant isolation.
- Formalize repository governance, dependency SBOM/licensing review, and secret-history scanning.
- Verify deployment health, backups, restore, and rollback before any production claim.

No dates, commercial commitments, or completion percentages are assigned here.
