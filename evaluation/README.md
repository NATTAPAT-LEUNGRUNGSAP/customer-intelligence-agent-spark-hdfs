# RAG quality protocol v2

RAG is mandatory. There is one system and one evaluation mode. There is no no-RAG
ablation or CLI switch. Old paired reports remain historical evidence under
reports/archive/v1 and original JSON files; they are not current acceptance criteria.

## Data separation

- dev.json: 10 development questions.
- test.json: 20 EXPOSED former test questions, now regression only; never call them
  a new held-out test for v2.
- retrieval_dev_v2.json: 12 development questions with hand-authored evidence IDs.
- rag_holdout_v2.json: first new set was executed; retrieval Recall@6=90.83%
  failed the 95% gate, so this is now exposed regression-v2, not fresh holdout.
- rag_holdout_v3.json: 20 further new combinations with prewritten evidence labels;
  freeze runtime code, knowledge, settings and model digest before its first run.
- quality_gates_v2.json: thresholds declared before the new holdout run.

Gold SQL and relevance labels are evaluator-only. They are never in the model
prompt. The retrieval corpus contains metric rules, schema, syntax and policies,
not question-specific answers or executable query templates.

## Direct measurements

1. Retrieval: Recall@6 (relevant IDs found / labeled relevant IDs), MRR@6, binary
   nDCG@6, precision@6, actual supplied-context coverage and retrieval latency p95.
   BM25/bilingual scoring is followed by schema/syntax dependency expansion;
   measurements assess this complete retrieval pipeline, not bare lexical scoring.
   Rank metrics use ranked results only; always-supplied policy chunks are counted
   only in context coverage. All qrels and missing evidence are retained.
2. Grounding: citations must exist in supplied context; relevant-evidence citation
   rate means at least one cited ID intersects the hand-labeled evidence set.
   These are structural/relevance checks, NOT a proof of textual entailment.
3. End-to-end: compare Spark result values against separately executed gold SQL.
   Numeric tolerance 1e-4 absolute / 1e-6 relative; required row order is checked;
   truncated answers fail. Valid SQL execution alone never means a correct answer.
4. Clarification: must return no SQL execution. New holdout labels also require the
   appropriate period/availability/snapshot policy citation. Reasons remain visible
   for independent review; this is not independent human certification.
5. Efficiency: model warm-up/load is recorded separately, then measure warm query
   end-to-end p95 (retrieval + generation + evidence review + Spark). Model calls,
   retries, retrieval/context size, exact corpus hashes and all errors are retained.
   This is per-question timing after Spark/session/view setup, not cold CLI wall time.
   ask.ps1 starts a Spark application per invocation, so its full wall time is higher.

## Gates

Retrieval Recall@6 >=0.95, MRR@6 >=0.85, nDCG@6 >=0.80, p95 <=50 ms.
End-to-end accuracy >=0.90, clarification accuracy 1.00, citation validity 1.00,
relevant-evidence citation rate >=0.95, warm query p95 <=20 seconds.

A report status of completed means all cases ran; quality_passed is a separate
field. A failed gate must be reported, not relabeled as a pass or removed.
Small authored datasets and similar question families do not establish general
accuracy. Freeze again and create another new set if tuning after holdout results.

## Run

python3 /app/jobs/evaluate_retrieval.py --split dev
scripts/evaluate.ps1 -Manifest /app/reports/build-RUNID.json -Split dev
scripts/evaluate.ps1 -Manifest /app/reports/build-RUNID.json -Split regression
scripts/evaluate.ps1 -Manifest /app/reports/build-RUNID.json -Split regression-v2

After freeze:
python3 /app/jobs/evaluate_retrieval.py --split holdout
scripts/evaluate.ps1 -Manifest /app/reports/build-RUNID.json -Split holdout
# Current v2.4 protocol update — 26 October 2026

Current holdout maps to rag_holdout_v6.json. Prior v4/v5 sets are now exposed
regression-v4/regression-v5; do not call reruns fresh. Runtime was frozen in
reports/freeze-rag-v2.4.json before any v6 agent outputs. New combinations use the
same supported task families and are developer-authored, not external-domain tests.
Current results: reports/DELIVERY_REPORT.md and delivery-quality-summary.json.
Do not replace or erase the failed v2.2/v2.3 raw reports. Gates were not lowered.

From v2.4, failed responses retain previously validated evidence IDs with an explicit
citation_scope saying there is no successful answer. Citation ID validity therefore
measures structural validity across traces, including failed attempts; it is not
semantic correctness. Failed/error responses always count WRONG in result accuracy.
The current final run has 17 executed queries, 3 correct clarifications, zero failures.
Metrics also report executed and failed/error counts for visibility.

The older protocol description below is historical where version/file names differ.

# Current expanded acceptance procedure

`acceptance.json` contains 60 new supported-family combinations for the latest
source-frozen run. `acceptance_exposed.json` contains the earlier 60-case set,
which scored 59/60 and then informed the transparent-CTE fix. It is regression,
alongside the older 20 cases, giving 80 regression questions. Three cases in
`acceptance_pilot_exposed.json` were exposed before the first aborted run stopped
and were excluded from subsequent fresh sets. These are authored project cases,
not an external benchmark or unseen task families.

`jobs/evaluate_acceptance.py` writes source/model/knowledge/ontology/policy hashes
before output. It stops before new questions if any regression case fails. Gold
SQL runs through the SQL guard on Spark. Agent outputs are evaluated by actual
result tables, not SQL string equality or an LLM judge. All failures/stops count
wrong. Existing gate thresholds remain unchanged. The final report verifies that
covered files and the model did not change during measurement.

The context experiment reuses 12 questions after exposure: no optional background,
3,000 characters omitted, and those characters retained. Every condition uses
RAG and the same selected evidence, with front/middle/end placement across cases.
There are 36 trials, not 36 independent tasks. Budget stops before the model and
during repair are separate from other failures. This measures input management
under that setup, not general prevention of model-internal context rot.

Current evidence and plain-language definitions: `reports/GOVERNANCE_REPORT.md`.
Prior raw reports remain historical and are not relabeled as current results.

