# Customer Intelligence Agent with Spark & HDFS — v2.4

Date: 26 October 2026 (Asia/Bangkok). Deadline: 9 November 2026.

Current measured project-gate decision: **PASS**.
Small developer-authored benchmark on supported families; not external certification.
The 20 v6 country/period/subgroup combinations were authored before freeze and not run
through the agent before the final evaluation. This is not a test of unseen domains.

| Metric | Actual | Gate |
|---|---:|---:|
| Recall@6 | 100.00% | >=95% |
| MRR@6 | 0.8917 | >=0.85 |
| nDCG@6 | 0.8934 | >=0.80 |
| Retrieval p95 | 16.69 ms | <=50 ms |
| Spark result accuracy | 20/20 (100%) | >=90% |
| Clarification accuracy | 100% | 100% |
| Citation ID validity across traces | 100% | 100% |
| Relevant evidence citation rate | 100% | >=95% |
| Warm query p95 | 5.43 s | <=20 s |

Executed=17; failed/error=0; model calls=35.
Warm-query timing excludes Spark application/view startup. Citation validity concerns
supplied evidence IDs, including IDs retained on failed attempts; it does not certify
correct answers or entailment. Failed answers always count wrong in accuracy.

## Implemented application and harness

- Local web UI calls actual RAG/Agent/Spark, with rows, SQL/evidence and trace.
- SQL generation remains dynamic; no gold SQL or query catalog is provided to the agent.
- Identified population AST and limited result contracts; scalar-pair output contract.
- Date-trunc syntax validation with corrective feedback; bounded three-attempt repair.
- Retrieval separates imperative return from refund lines and recognizes repeat phrasing.
- Context selection, latest repair state, heuristic budget and actual Ollama token telemetry.
- Git source and CI configuration prepared. GitHub creation/push still awaits user sign-in.

## Actual checks and retained failures

- Smoke fcde70a71325433185dbaace442f66c9: 2 workers, 3-row HDFS roundtrip, totals 1500/2500.
- Unit suite: 25 passed in Docker (candidate-v2.4-unit-tests-complete.log).
- v2.4 exposed regression-v5: 20/20 correct; separate from new v6 result above.
- Earlier context stress: 0/400/1200 distractor characters, correct invoice count2040;
  oversized prompt blocked before model/SQL. This does not prove long-context robustness.
- v2.2 new v4: 18/20; overall gate FAIL. Bad date_trunc and an overbroad Inactive rule.
- v2.3 new v5: 18/20; overall gate FAIL. MRR0.825 and citation validity95%.
- All raw reports/freeze records retained. No threshold was lowered.
- An extra-output prompt experiment regressed exposed v4 to18/20; reverted before freeze.

## Final-case failures

None in these 20 cases; this is not a claim of general perfect accuracy.

## Reproduction and limits

See README.md, docs/WEB_APP.md, evaluation/README.md and freeze-rag-v2.4.json.
Raw current results: rag-v2.4-holdout-d2b7e5379bbf4781941a21125feb7039.json; retrieval-v2.4-holdout-016e4ba10a0c490a9283ea2ff74eb2e1.json.
The source/corpus/config/model hashes match the pre-run freeze; no runtime tuning
after this final run. Historical v2.1 scores remain in FINAL_REPORT.md.
Single physical host; no user authentication; best-effort Spark cancellation.
Context input size is a heuristic, not exact tokenization; post-generation counts cannot
guarantee detection of server-side truncation. No general context-rot solution is claimed.
OPA, formal ontology/cross-organization schema matching remain unimplemented.
MongoDB Policy Storage and Churn/Campaign are excluded from this delivery.
Fresh-checkout end-to-end build and actual GitHub CI execution remain to verify.
