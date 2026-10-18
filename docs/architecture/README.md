# Architecture

Start here for the production architecture. The documents below were checked against the code
at commit `e69494d`. Uncommitted working-tree changes are named where they matter.

| Document                                    | Read it for                                                                                                                              |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| [SYSTEM](SYSTEM.md)                         | Containers, request flow, channel flow, AI flow, outbound contact, workflows, admin, security boundaries. Mermaid diagram for each flow. |
| [DATA](DATA.md)                             | The 84 tables, key relationships, the Alembic head, and retention rules.                                                                 |
| [DEPLOYMENT-DIAGRAM](DEPLOYMENT-DIAGRAM.md) | Host layout, DNS records, Caddy TLS, firewall, and the GitHub deploy and rollback path.                                                  |
| [diagram.html](diagram.html)                | One-page SVG overview. Open it in a browser. No external scripts.                                                                        |

Older and supporting documents:

- [System overview](SYSTEM-OVERVIEW.md)
- [Authentication and RBAC](AUTHENTICATION-RBAC.md)
- [AI and RAG](AI-RAG.md)
- [Events and workers](EVENTS-WORKERS.md)
- [Environment and storage](../guides/ENVIRONMENT.md)

Mermaid sources are in ../diagrams. The local validator checks source-to-embed parity, and this branch's ten sources were parsed with Mermaid 11.12.0 in an isolated temporary validation environment. GitHub rendering is presentation evidence, not runtime evidence.

## OraOne ecosystem context

<!-- diagram: docs/diagrams/system-context.mmd -->

```mermaid
flowchart TB
  Viswatra[Viswatra portfolio direction]
  Viswatra -. intended portfolio brand .-> Ecosystem[OraOne ecosystem]
  Ecosystem --> P1[Product 1: OraOne AI Chat Platform]
  Ecosystem --> P2[Product 2: OraOne AI Voice Platform]
  Ecosystem --> P3[Product 3: OraOne WhatsApp Platform]
  Ecosystem --> P4[Product 4: Omnichannel Communication Hub]
  Ecosystem --> P5[Product 5: Workflow Automation Platform]
  Ecosystem --> P6[Product 6: AI Studio & Agent Builder]
  Ecosystem --> P7[Product 7: Marketplace]
  Ecosystem --> P8[Product 8: Mobile Applications]
  Ecosystem --> P9[Product 9: Enterprise Edition]
  Ecosystem --> P10[Product 10: OraOne OS]
  Shared[Shared foundations: identity, governance, AI gateway, usage, integrations]
  P1 --> Shared
  P2 -. planned .-> Shared
  P3 -. planned .-> Shared
  P4 -. planned .-> Shared
  P5 -. planned .-> Shared
  P6 -. planned .-> Shared
  P7 -. planned .-> Shared
  P8 -. planned .-> Shared
  P9 -. planned .-> Shared
  P10 -. long-term vision .-> Shared
```
