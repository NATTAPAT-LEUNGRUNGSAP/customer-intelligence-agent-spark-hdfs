# Presentation

Current deck: [customer-intelligence-docker-guide.pptx](customer-intelligence-docker-guide.pptx), 30 slides in Thai/English.

The deck explains business terms in short on-slide notes and uses editable native
process diagrams, connectors, text and tables. It includes the implemented
RDF/OWL domain ontology with SHACL, mandatory OPA/Rego decisions before/after
Spark, semantic and result checks, and current measured outcomes.

Current measurements: 60/60 newly authored combinations, 80/80 exposed regression,
53 unit tests and 3 actual OPA integration tests. Context uses 12 distinct questions
in 3 conditions, 36 trials total, with RAG in every condition. All measurements and
limits are documented in reports/GOVERNANCE_REPORT.md. No software/release labels
or delivery time-box framing appear on the slides.

Text, including table cells, is in slide-text-docker-guide.json. Live object IDs and
source notes are in outline-docker-guide.ndjson. Earlier decks remain historical.
User-supplied reference images are not embedded or published. All 30 slides were
rendered and reviewed. The file was not opened in Microsoft PowerPoint.

The live deck and exported PowerPoint are the same presentation, not alternative
content. Use only the current deck linked above for the next review.

Added a benefit/evidence summary and seven topic examples for RAG, ontology, SQL semantics, OPA/post-tool checks, context, the web API and evaluation. Short code excerpts are labeled where simplified. The eight added slides were rendered and visually reviewed; other layouts are preserved with updated page numbers. This presentation-only edit does not rerun or relabel the existing runtime benchmarks.

Docker pages 5-7 explain all configured service roles, long-running versus job containers, named volumes versus host bind mounts, temporary Spark data, host-side Ollama and the driver/master/executor distinction. These three pages were rendered and visually checked. Contents were verified against Compose and HDFS configuration; no new runtime test is claimed for this slide-only change.
