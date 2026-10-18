# Architecture and flow diagrams

These diagrams use Mermaid and render on GitHub. They describe Product 1 as it is
built in this repository.

## 1. System context

Who uses OraOne and which outside services it depends on.

```mermaid
flowchart LR
  owner["Business owner<br/>(Studio)"]
  agent["Team member<br/>(inbox, leads)"]
  visitor["Website visitor"]
  dev["Developer<br/>(script, SDK, REST)"]

  subgraph oraone["OraOne Product 1"]
    web["Web app<br/>(TanStack Start)"]
    api["API<br/>(FastAPI)"]
  end

  openrouter[("OpenRouter<br/>AI models and embeddings")]
  smtp[("SMTP<br/>sign-in codes")]
  site["Customer website"]

  owner --> web
  agent --> web
  dev --> web
  visitor --> site
  site -- "widget.js" --> api
  web -- "/api" --> api
  api --> openrouter
  api --> smtp
```

## 2. Containers

How the parts run in production. Caddy is the only public entry point.

```mermaid
flowchart TB
  internet(("Internet")) --> caddy["Caddy<br/>TLS, headers, compression"]
  caddy -- "/api/*" --> backend["backend<br/>FastAPI under Gunicorn"]
  caddy -- "everything else" --> frontend["frontend<br/>Node SSR (Nitro)"]
  backend --> postgres[("PostgreSQL 16<br/>pgvector")]
  backend --> redis[("Redis<br/>rate limits, cache")]
  backend --> uploads[("Uploads volume<br/>document files")]
  workers["workers<br/>background jobs"] --> postgres
  workers --> redis
  workers --> uploads
  backend --> openrouter[("OpenRouter")]
  workers --> openrouter
```

## 3. Repository layout

```mermaid
flowchart LR
  subgraph web["src/ (web app)"]
    routes["routes/<br/>file-based pages"]
    components["components/oraone/<br/>studio, marketing, shell"]
    lib["lib/api/<br/>typed API clients"]
  end
  subgraph be["backend/app/ (API)"]
    apiroutes["api/<br/>HTTP routers"]
    services["services/<br/>business logic"]
    providers["providers/<br/>OpenRouter, embeddings"]
    db["database/models/<br/>SQLAlchemy"]
  end
  public["public/widget.js<br/>embeddable loader"]

  routes --> components --> lib
  lib -- "/api" --> apiroutes --> services --> db
  services --> providers
  public -. "served to customer sites" .-> apiroutes
```

## 4. Sign-in (passwordless email code)

```mermaid
sequenceDiagram
  autonumber
  actor U as User
  participant W as Web app
  participant A as API
  participant M as Email (SMTP)
  U->>W: Enter email
  W->>A: POST /api/auth/email-code/request
  A->>M: Send six-digit code (10 min, single use)
  A-->>W: 200 (same for known and unknown emails), or 503 if sending fails
  U->>W: Enter code
  W->>A: POST /api/auth/email-code/verify
  A-->>W: Set httpOnly access and refresh cookies
  W->>A: GET /api/auth/identity
  A-->>W: User, organization and project (created on first sign-in)
  W-->>U: Open Studio
```

## 5. Assistant reply (Studio playground and website widget)

```mermaid
sequenceDiagram
  autonumber
  actor V as Visitor or team member
  participant C as Client (Studio or widget.js)
  participant A as API
  participant R as Knowledge search
  participant O as OpenRouter
  V->>C: Message
  C->>A: POST message (conversation or widget session)
  A->>A: Check widget status and domain, rate limit
  A->>R: Find relevant knowledge chunks
  R-->>A: Sources (may be empty)
  A->>A: Route to a model the plan allows
  A->>O: Chat completion with sources and history
  O-->>A: Answer
  A->>A: Save message, usage and audit event
  A-->>C: Answer, sources, suggested questions
  C-->>V: Show answer
```

## 6. Model selection

```mermaid
flowchart TD
  start(["Request needs a reply"]) --> pin{"AI_FORCE_MODEL set?"}
  pin -- yes --> forced["Use the pinned model"]
  pin -- no --> asked{"Agent model allowed<br/>on the org's plan?"}
  asked -- yes --> use["Use the agent's model"]
  asked -- no --> budget{"Over monthly budget?"}
  budget -- yes --> cheap["Cheapest allowed model"]
  budget -- no --> strategy["Org routing strategy<br/>(balanced, fastest, quality)"]
  strategy --> fallback["Fallback chain on provider error"]
```

## 7. Website widget: install and go live

```mermaid
flowchart LR
  a["Create or choose an assistant<br/>(Studio)"] --> b["Create chat widget<br/>(Add to website)"]
  b --> c["Allow domains<br/>(optional, empty = any site)"]
  c --> d["Copy the script tag,<br/>SDK or React code"]
  d --> e["Paste on the site"]
  e --> f{"Widget published?"}
  f -- no --> g["Visitors see nothing"]
  f -- yes --> h["widget.js loads config<br/>and opens a visitor session"]
  h --> i["Visitors chat<br/>(section 5)"]
```

## 8. Widget loader at runtime

```mermaid
sequenceDiagram
  autonumber
  participant P as Customer page
  participant L as widget.js
  participant A as API
  P->>L: Script loads (data-widget-id)
  L->>A: GET /api/widget/config?key=...
  A-->>L: Theme, settings (no secrets)
  L->>L: Render launcher in Shadow DOM
  P->>L: Visitor opens chat
  L->>A: POST /api/widget/session (visitor id)
  A-->>L: Session and prior messages
  L->>A: POST /api/widget/chat
  A-->>L: Grounded answer
```

## 9. Studio journey for a new owner

```mermaid
flowchart LR
  signin["Sign in<br/>email code"] --> home["Assistants"]
  home --> new["New assistant"]
  new --> edit["Configure and test<br/>(playground)"]
  edit --> install["Add to website"]
  home --> inbox["Inbox"]
  home --> leads["Leads"]
  home --> knowledge["Knowledge"]
  home --> more["More: integrations, team,<br/>analytics, billing, API keys"]
```

## 10. Lazy loading

Studio screens and the public and workspace page routes load their code when the
route is entered. Each shows a `RouteLoader` while it loads, and the router shows
`NavigationProgress` during navigations. Heavy charts load only where they are used.
