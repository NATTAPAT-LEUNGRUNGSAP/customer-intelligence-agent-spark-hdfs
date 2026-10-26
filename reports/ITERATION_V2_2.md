# Development iteration v2.2 — 26 October 2026

Historical development record. Current source is v2.4; see DELIVERY_REPORT.md.
The later v2.2 v4 holdout failed overall gates (18/20); retained separately.
Statements below describe the earlier development checkpoint, not current status.

Current source differs from frozen v2.1. Preserve FINAL_REPORT.md and its raw reports
as version-specific historical evidence. No fresh holdout score exists for v2.2.

## Implemented

- Local web application at localhost:8090 calls the actual mandatory-RAG agent and
  guarded Spark path, showing result rows, clarification/errors, SQL/evidence and trace.
- Identified population AST contract requires an explicit customer_id IS NOT NULL
  conjunct in orders scopes for explicitly identified-customer questions. This is
  a narrow conservative contract, not general business-semantic verification.
- Limited post-execution checks catch NULL customer IDs and out-of-range fractions
  when applicable. Wrong but plausible fractions still require stronger checks/evaluation.
- More explicit identified-population/repeat denominator instructions.
- Heuristic input budget 6000 tokens, context setting 8192, capped output, original
  question/facts plus latest repair only. Required evidence is retained; oversize
  prompts fail rather than silently dropping policy. Estimate uses UTF-8 bytes/2
  plus framing and is NOT an exact tokenizer or guaranteed upper bound.
- Ollama prompt_eval_count/eval_count recorded on successful calls. Post-generation
  reserve check does not guarantee detection of input silently truncated by a server.
- Git initialized; CI unit configuration and public repository documentation prepared.
- Presentation created in the live artifact session, with editable text/tables/diagram.

## Actual runs

- Smoke: smoke-fcde70a71325433185dbaace442f66c9.json — passed, 2 Spark workers,
  HDFS roundtrip 3 rows, totals 1500/2500, replication setting 2.
- Initial new unit run: 20 passed; revised run: 21 passed
  (iteration-unit-tests-v2.log). Includes HTTP origin/config/busy/trace tests.
- First iteration regression: iteration-regression-1f4a695e507840cc95757b372dbf88b8.json,
  15/16 correct. Repeat fraction included anonymous population: 0.23033707865
  versus gold 0.22947131609. Retained as failed checks, not overwritten.
- Revised iteration: iteration-regression-0fce36716fa14affb29463bc3284a808.json,
  status=completed, checks_passed=true, 16/16 correct. Dev10, three exposed failures
  hold04/hold08/fresh08, three invoice-count questions with 0/400/1200 distractor
  characters. Fresh08 now returns IDs 12346,14646,15749, not an anonymous group.
- Oversized prompt: failed with model_calls=0 and no SQL execution. The bounded
  loop records three local budget rejections; no external model calls are made.
- Actual web query: October 2011 invoices=2040, trace bce23c8f6a7d404795362d751656013c.
  Actual browser ranking demo: trace f75c84946bf94b58a8195199ec9e3e0e,
  identified IDs/GBP totals 12346/77183.6000,14646/26476.6800,15749/22998.4000.
  These initial UI traces precede the final AST-contract revision; subsequent
  regression above covers the revised backend. web-demo.png/web-result.png show UI.

## Remaining acceptance work

Regression/stress cases are exposed and small; this is not a fresh holdout or proof
that context rot is solved. Test more families/positions/lengths before stronger claims.
Create a new frozen candidate and fresh evaluation before claiming v2.2 acceptance.
Verify fresh checkout/data build, publish the authorized GitHub repo after sign-in,
and rehearse slides/demo. OPA and formal ontology are not implemented. Excluded
MongoDB and Churn/Campaign topics are not project deliverables.
