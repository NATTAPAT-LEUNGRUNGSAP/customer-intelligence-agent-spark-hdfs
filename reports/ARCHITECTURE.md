# Customer Intelligence

```mermaid
flowchart LR
  U[UCI ZIP + provenance hashes] --> C[CSV staging]
  C --> B[Spark ETL + reconciliation]
  B --> H[Versioned Parquet on HDFS]
  H --> V[Three Spark temporary views]
  UI[Local browser UI :8090] --> Q[User question]
  Q --> R[Cached BM25 + bilingual topic retrieval]
  K[Schema, metrics, syntax, Thai glossary] --> R
  O[OWL/RDF domain ontology + SHACL] --> R
  R --> P[Evidence policies: period, availability, snapshot]
  P --> M[Local Ollama model generates SQL + citations]
  P -->|clarification| T
  V --> S[Actual schemas + dataset bounds]
  S --> M
  M --> CV[Citation validation]
  CV --> G[Read-only AST validation]
  G --> PC[Identified population contract]
  PC --> SC[Business SQL contracts]
  SC --> OPA[OPA/Rego pre-tool decision]
  OPA --> D[Evidence consistency review]
  D --> E[Spark execution with deadline and row cap]
  D -->|bounded correction| M
  V --> E
  E --> RC[Result envelope and applicable invariants]
  RC --> OP[OPA/Rego post-tool decision]
  OP --> T[Result rows + trace + references]
  RC -->|bounded error feedback| M
  E -->|bounded error feedback| M
```

HDFS has one NameNode and two DataNodes, replication 2. Spark has one master
and two workers. Everything runs on one physical Windows host under Docker
Desktop Linux, while Ollama runs on the Windows host GPU. This demonstrates
multiple processes/nodes, not resilience to loss of the physical machine.

SQL is generated dynamically. Gold SQL in evaluation is exclusively a test oracle,
not an agent query catalog. Model prose is not measured evidence; Spark rows,
build reconciliation and evaluation reports are the evidence. SQL guard reduces
the allowed query surface, but the unauthenticated local stack is not a production
security boundary. A local web application now calls the same guarded agent path.
Heuristic context budgeting rejects oversize prompts; repair history retains only
the latest rejected proposal/error. Exact token preflight is not implemented. Production deployment
is separate. See PRESENTATION_BRIEF.md for the revised delivery requirements.

Current source results: GOVERNANCE_REPORT.md. OPA decisions are required; unavailable or undefined decisions block execution/delivery. The ontology covers the project domain; it does not automatically map an unknown enterprise schema.
