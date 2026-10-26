# Ontology, policy and semantic contracts

The production agent still generates its own SQL. There is no gold-query catalog
in its prompt or execution path. Verification SQL exists only under evaluation/.

## Domain ontology

ontology/customer-intelligence.ttl is an RDF/OWL graph with Metric, Table, Grain
and Evidence classes. Nine metric instances connect business labels in English
and Thai to a source table, formula, grain and evidence section. Three table
instances describe the actual analytics views. This is a formal domain graph,
not automatic schema matching for unknown organizations.

ontology/shapes.ttl specifies SHACL cardinality, datatype and class constraints.
jobs/ontology.py loads and validates the graph, checks metric/table grain
agreement and caches the validated mapping until the files change. RAG resolves
matching labels and adds missing metric/schema evidence dependencies. Unknown
labels do not get an invented mapping. The trace records matching concepts and
the ontology hash. Formula strings document definitions and never execute SQL.

## OPA/Rego

compose.yaml starts an internal OPA service. Python sends trusted AST facts to
/v1/data/analytics/decision. Rego enforces a read-only analytics operation, an
allowed source table, attempt count and output cap. After Spark, deterministic
result violations are sent to the same engine. A deny, unavailable service,
undefined result or malformed decision blocks delivery. The agent does not
accept policy facts from the browser or the model.

This policy concerns analytics tool use. It does not authenticate users, provide
tenant isolation or replace the SQL AST/function whitelist.

## Checks before and after Spark

Before the tool, AST validation checks syntax/allowed functions and views.
Contracts check identified populations, source grain, explicit English month or
month-span/half-open-date filters, snapshot equality, transaction types and a
known join fan-out pattern. Unsupported equivalent SQL can be rejected; these
checks are deliberately narrower than full SQL semantic equivalence.

After the tool, checks cover result shape, row width/cap, finite numbers, scalar
aggregate row shape, integer nonnegative COUNT outputs, selected grouping keys,
identified IDs and repeat fractions in [0,1]. Each applicable check can reject a
result and trigger bounded repair. Range/shape checks cannot prove an answer is
correct; the evaluation harness separately compares actual rows against gold.

## Evaluation terminology

- Gold SQL: a developer-authored reference query, guarded and executed by Spark
  to obtain the expected table. It is never sent to the production agent.
- Expected evidence: labeled knowledge IDs which retrieval should return for a
  question. ID validity and relevance do not establish semantic entailment.
- New-question evaluation: questions and gates are recorded before model output,
  with source/model/knowledge/ontology/policy fingerprints checked afterward.
  Once a result informs a fix, those questions become regression cases.
- Context comparison: the same RAG facts with no optional background, with that
  background omitted, or with it retained. All conditions use RAG. Budget stops
  are distinguished from executed wrong answers and other failures.

Run the real OPA integration test separately from offline unit tests:

```powershell
docker compose up -d opa
docker compose run --rm --no-deps --entrypoint python3 spark-job /app/tests/integration_governance.py
```

See [OPA policy language](https://www.openpolicyagent.org/docs/policy-language)
and [W3C SHACL](https://www.w3.org/TR/shacl/) for the standards used here.
