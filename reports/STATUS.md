# Web time selection

Web defaults to all available data; custom dates include both selected dates.
Explicit question periods/snapshots override selection. The chosen scope is visible.
Best-selling product requests ask units versus revenue when unspecified.
100 unit tests passed; 4 actual authenticated HTTPS checks passed, including
October invoice count 2040 and question-over-selector precedence.
See web-time-unit-tests.txt and web-time-https-verification.json.
The earlier 196/200 development evaluation was not rerun on this source.

# Product-category availability fix

The exact reported Thai question now returns that no product taxonomy exists,
with product_id/description alternatives, before the time-period policy.
95 unit tests passed; 3 actual authenticated HTTPS checks passed in Thai/English.
See product-category-unit-tests.txt and product-category-https-verification.json.
The 196/200 bilingual run below predates this routing/schema-evidence change;
it has not been rerun on this source.

# Current verification status

Latest live-model development run: bilingual-development-final.json.
Thai 97/100; English 99/100; total 196/200.
SQL results 156/160; grounded formula lookup 24/24; clarification 16/16.
This is an exposed development bank, not an independent holdout.
Source/model fingerprints and bank fingerprints match before/after the complete run.

- Unit tests: 93 passed (bilingual-unit-tests.txt).
- Actual OPA integration: 3 passed (bilingual-opa-integration.txt).
- Numeric RAG formula fixtures on actual Spark: 16/16 (bilingual-formula-integration.json).
- Public authenticated HTTPS feature checks: 5/5 (bilingual-web-verification.json).
- Password/Origin/public Spark smoke checks: 13/13 (friend-access-verification.json).
- Retrieval Recall@6 before/after on the same corrected bank: 0.6450 → 0.9850.
- Evidence packet byte reduction on identical selected references: 0.2106; all ID/text hashes match.

4 development questions still do not match the oracle. See BILINGUAL_ANALYTICS_REPORT.md
and bilingual-quality-summary.json for the actual results and limitations.
The web app is restored; the temporary HTTPS link uses the existing credentials.
The records below are historical and do not describe current-source measurements.

<!-- preserved-history -->
# Work resumed

Resumed on 27 October 2026 (Asia/Bangkok). Docker cluster is running.
Fresh Spark/HDFS smoke passed (resumed-smoke.log); 93 unit tests and 3 actual
OPA integration checks passed. A new complete bilingual evaluation is running
into bilingual-development-final.json. No completed score is claimed yet.
The preserved 67/200 report remains partial. Web is stopped during evaluation.
Changes are not yet committed or pushed.
# Work paused at the user's request

Current-source bilingual evaluation was stopped at **67/200** cases, all 67
correct so far. This is PARTIAL, not a completed 200-case result.
See [RESUME.md](RESUME.md) and bilingual-development-paused.json.
The web container was restored. This task's changes are not yet committed/pushed.
Latest unit tests: 93 passed. Formula fixtures: 16/16 actual Spark checks.
Continue only when the user explicitly resumes.

The records below are historical and do not describe the latest source.

# Earlier verification status

Monthly comparison fix: the exact reported question “เดือนไหนออเดอร์เยอะสุด”
executed through authenticated public HTTPS with Qwen/OPA/Spark and returned
November 2011, 2,769 completed invoices. Full trace, including rejected/failed
attempts before successful self-correction, is in month-comparison-https-result.json.
All 60 unit tests passed (month-comparison-unit-tests.txt). The new scope rule is
limited to unqualified month/order superlatives and displays its all-data default.
Historical acceptance metrics below were not rerun for this source change.

Dataset discovery fix: “มีข้อมูลอะไรบ้าง” now returns the three loaded tables,
actual columns and manifest dates instead of requesting an analysis period.
Thai policy clarifications are localized. Actual authenticated public HTTPS
checks are recorded in dataset-discovery-web-verification.json; 57 unit tests
passed in dataset-discovery-unit-tests.txt. The acceptance benchmark below
predates this routing/localization change and is not a fresh run of this source.

Current source: RDF/OWL domain ontology + SHACL, mandatory OPA/Rego pre/post
Spark decisions, bounded SQL semantics and stronger post-tool contracts.

- Completed current-source run: acceptance-376b19a376714e218c6197ab5c9b27c4.json
- Source/model fingerprints before and after run match.
- Newly authored supported-family combinations: 60/60 (52 SQL + 8 clarification).
- Exposed regression: 80/80. Unit tests: 53 passed. Actual OPA integration: 3 passed.
- Context: 12 distinct questions, 36 trials; clean12/12, managed12/12,
  unfiltered10/12 with 1 pre-model and 1 repair-stage budget stop.
- All context arms use RAG. This is not proof of general model-internal context rot prevention.
- Earlier 59/60 run retained; its cases became regression after CTE/NaN fixes.
- Spark/HDFS smoke passed: smoke-c26e5eebbef34b579f83488c6a5913e4.json.

Current HTTP verification passed: governance-web-verification.json (2,040 October 2011 invoices; actual ontology/OPA/Qwen/Spark). Local web app is running at localhost:8090.

See GOVERNANCE_REPORT.md and governance-quality-summary.json for current results.
The following records are historical and their freeze claims do not describe
current source. Do not relabel old holdouts as unseen current-source measurements.

---

# Earlier verification status - v2.4

Current extension: Context v2, measured in context-v2-fc31fe03f55a442ba0c39f9969c72d7b.json.
31 unit tests passed; exposed v6 regression20/20; managed stress21/21 trials on3
repeated tasks, with all selected ID/text retained and zero budget rejections.
Unfiltered control:9 stopped before model,3 during repair,1 other failure,8 correct.
Current source includes this extension and differs from frozen v2.4. The older
v2.4 results below remain version-specific historical evidence, not a current-source
freeze claim. See CONTEXT_REPORT.md and context-quality-summary.json.
The first metadata-compacting candidate regressed to18/20 and was not adopted.
Token preflight remains heuristic; model-internal context rot is not generally solved.

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
