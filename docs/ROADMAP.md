# OraOne roadmap

Product numbers identify the portfolio and do not prescribe a release sequence. Product 1 is in active development. Products 2 to 7 and 9 have code in this repository at the statuses in the portfolio; Product 8 is not in this repository; Product 10 is the long-term vision. See [Product portfolio](PRODUCT-PORTFOLIO.md) for exact scopes.

## Current focus — Product 1

- Keep email-only email-code and PostgreSQL-backed RBAC aligned.
- Complete authorized live authentication and protected-API verification.
- Finish webhook external-delivery, restart, and dead-letter drills.
- Establish repeatable backup/restore and deployment evidence.
- Reduce lint warnings that indicate real defects.

## Portfolio status

| Product                       | Status (see the portfolio for blockers) |
| ----------------------------- | --------------------------------------- |
| OraOne AI Chat Platform       | Live-needs-account                      |
| OraOne AI Voice Platform      | Live-needs-account                      |
| OraOne WhatsApp Platform      | Live-needs-account                      |
| Omnichannel Communication Hub | Built (partial)                         |
| Workflow Automation Platform  | Built (partial)                         |
| AI Studio & Agent Builder     | Built (partial)                         |
| Marketplace                   | Built                                   |
| Mobile Applications           | Planned (not in this repository)        |
| Enterprise Edition            | Built (partial)                         |
| OraOne OS                     | Planned (long-term vision)              |

Status labels are defined in the [portfolio](PRODUCT-PORTFOLIO.md). "Partial" means some of the
product's listed features are missing.

## Shared foundations

The intended ecosystem may share identity, tenant and project governance, AI gateway capabilities, billing and usage concepts, design-system components, reusable integrations, unified administration, and future cross-product interoperability. These are future design directions, not shipped product claims.

## Release gates

- Add durable monetary/token AI budget reservation and reconciliation beyond daily message quotas.
- Complete signed payment-provider sandbox lifecycle tests.
- Add independent reviews for crawling, uploads, prompt injection, billing, and tenant isolation.
- Formalize repository governance, dependency SBOM/licensing review, and secret-history scanning.
- Verify deployment health, backups, restore, and rollback before any production claim.

No dates, commercial commitments, or completion percentages are assigned here.
