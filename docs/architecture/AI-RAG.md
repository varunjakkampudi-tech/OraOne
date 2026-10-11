# AI and RAG

The knowledge path stores document metadata and embeddings in PostgreSQL and pgvector. Uploads use the storage abstraction, then backend services parse, chunk, embed, and retrieve context for answer generation.

The model interface is OpenAI-compatible and can target OpenRouter through server-side credentials. Provider selection, quotas, retries, and usage accounting live in backend services. A daily message quota exists; durable monetary/token spend ceilings remain open.

Production-like environments reject explicit mock inference. Credentialed provider smoke tests, cost reconciliation, prompt-injection review, and failure drills remain required.

## AI chat and RAG sequence

<!-- diagram: docs/diagrams/ai-chat-rag-sequence.mmd -->
```mermaid
sequenceDiagram
  participant V as Visitor
  participant W as Widget
  participant A as Chat API
  participant C as Agent configuration
  participant R as Scoped retrieval
  participant K as Knowledge chunks
  participant O as OpenRouter
  participant D as PostgreSQL
  V->>W: Send message
  W->>A: Chat request
  A->>C: Load agent and policy
  A->>R: Retrieve within organization scope
  R->>K: Query pgvector and knowledge records
  K-->>R: Relevant chunks
  R-->>A: Context
  A->>O: Grounded prompt
  O-->>A: Model response
  A->>D: Persist conversation and usage
  A-->>W: Response
```

## Knowledge ingestion flow

<!-- diagram: docs/diagrams/knowledge-ingestion.mmd -->
```mermaid
flowchart LR
  Submit[Document upload or website URL] --> Validate[Validate tenant and input]
  Validate --> Store[Store object or crawl content]
  Store --> Parse[Parse and normalize text]
  Parse --> Chunks[Create chunks]
  Chunks --> Embed[Embedding path]
  Embed --> Index[(PostgreSQL and pgvector)]
  Index --> Ready[Retrieval ready]
  Worker[Background worker] -. processes queued work .-> Parse
  Fallback[Local hash embedding fallback] -. local development only .-> Embed
  Provider[Configured semantic embedding provider] -. optional provider .-> Embed
```
