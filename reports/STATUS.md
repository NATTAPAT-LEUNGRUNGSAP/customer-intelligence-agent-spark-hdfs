# Current verification status - v2.4

Date: 26 October 2026 (Asia/Bangkok). Deadline: 9 November 2026.

## Current decision

Mandatory-RAG v2.4 passes the predeclared project gates on 20 new supported-family
combinations (v6). This small developer-authored benchmark is not external validation
or proof of general perfect accuracy. Raw failures from prior iterations are retained.
See DELIVERY_REPORT.md and delivery-quality-summary.json.

- Freeze: freeze-rag-v2.4.json; current source/model fingerprints verified to match.
- End-to-end: rag-v2.4-holdout-d2b7e5379bbf4781941a21125feb7039.json.
- Retrieval: retrieval-v2.4-holdout-016e4ba10a0c490a9283ea2ff74eb2e1.json.
- 20/20 correct: 17 executed SQL queries + 3 policy clarifications; zero failures.
- Recall@6=100%, MRR@6=0.8917, nDCG@6=0.8934, context coverage=100%.
- Retrieval p95=16.69ms; warm-query p95=5.43s; 35 local model calls.
- Clarification/citation-ID validity/relevant citation rate=100%.
- Timing excludes Spark startup. Citation validity is structural across traces,
  not proof of semantic entailment; failed answers always count wrong in accuracy.

## Implemented delivery

- Local web application at http://localhost:8090 connects to actual Qwen/RAG/Spark.
  It displays result tables, clarification/errors, SQL/evidence and trace details.
  See docs/WEB_APP.md and scripts/start-web.ps1.
- Context engineering: evidence selection, latest repair state, heuristic 6000-token
  input budget and actual Ollama token telemetry. Exact tokenizer preflight and
  general context-rot prevention are NOT established.
- Pre-tool AST guard, identified-population and scalar-output contracts; limited
  post-tool invariants; date-trunc validation; up to three correction attempts.
- Retrieval separates imperative return from refund lines and understands repeat
  phrasing. Core logic remains custom Python, not OPA or a formal ontology.
- Presentation: presentation/customer-intelligence-v2.4-release.pptx, 14 slides with actual
  architecture/workflow, harness components, context engineering and measured results.
- Git initialized on main; public repo name customer-intelligence-agent-spark-hdfs
  published for NATTAPAT-LEUNGRUNGSAP. Remote push verified; GitHub CI unit job
  succeeded (run40284829764). See github-publication.json for the URL and evidence.

## Actual development verification

- Unit suite: 25 passed in Docker; unit-tests-v2.4.txt is included as evidence.
- Exposed v5 regression: 20/20 correct; not a fresh holdout score.
- HDFS/Spark smoke fcde70a71325433185dbaace442f66c9 passed this continuation:
  2 workers, replication setting2, 3 rows, totals C001=1500/C002=2500.
- Earlier development stress (v2.2): 0/400/1200 distractor characters correct;
  oversized prompt blocked before model/SQL. Do not call this general robustness.
- Current runtime build/data: 1,067,371 sales lines, 40,077 orders, 3,450 snapshot
  customers; versioned passed manifest c81fa72c3c174a96bf8c03195b9e6f5e.
- Hadoop3.4.1/HDFS two DataNodes, Spark4.1.3/two workers, replication2.
- Local Qwen3.5:9b, RTX5070 12GB, host RAM approximately32GB, context8192.

## Retained history and limitations

- v2.2 fresh v4: 18/20; overall gates FAILED. Syntax and overbroad knowledge rule.
- v2.3 fresh v5: 18/20; overall gates FAILED (MRR0.825, citations95%).
- Prior development failures and reverted prompt experiment remain in raw reports.
- Historical frozen v2.1 results: FINAL_REPORT.md; they do not describe current code.
- No threshold was lowered. Future tuning requires a new freeze; exposed cases
  remain regression. Never call reruns of v6 an unseen holdout.
- Single physical host, no authentication, best-effort cancellation; local demo only.
- OPA, formal ontology and cross-organization schema matching are not implemented.
- MongoDB Policy Storage and Churn/Campaign are excluded from delivery.
- Actual GitHub CI unit step passed. A fresh-checkout full data acquisition/build
  on a separate machine is not yet verified.
- Fresh local Git checkout source inventory matches the host and covered frozen core;
  its own unit suite passed25 tests. Evidence: git-checkout-verification.json and
  checkout-unit-tests.txt. Static web files/PowerShell launchers are recorded in a
  supplemental post-verification host inventory because spark-job does not mount them.
- Actual browser v2.4 demo: trace600f1d5f170a49b1a04e4673f1342375, correct identified
  customer ranking, source/model match frozen core. web-v2.4-demo-summary.json.
