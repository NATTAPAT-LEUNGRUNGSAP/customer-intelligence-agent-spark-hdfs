> Historical audit/source validation: for the integrated deployed system and current test results, see [CURRENT_STATE.md](CURRENT_STATE.md). Main web is now8090; preview8091 is stopped.

# Live validation — 3 November 2026

## Scope and reproducibility

Compared baseline commit `76629c472bdde02c8c4490bf95a5bece468c1ea2` with the local improved agent on the same existing HDFS build `c81fa72c3c174a96bf8c03195b9e6f5e`. Real services: Spark 4.1.3 / Java 17, Python 3.10.12 in the existing Spark image, OPA 1.0.1, Ollama `qwen3.5:9b` (digest `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`), MCP SDK 1.26.0.

Separate temporary containers used Spark `local[2]` for comparison and `local[1]` for MCP. They read Parquet from the original HDFS namenode/datanodes; they did not use the shared standalone Spark workers. Existing web service continued running. No ETL, HDFS table rebuild, source-data modification or GitHub write occurred.

The paired comparison used all ten existing `evaluation/dev.json` cases: eight numeric/ranking/snapshot queries and two clarifications. Gold SQL executed independently against the same loaded views; comparisons used existing `evaluate.same_result`. Baseline/improved order alternated by question. These are exposed development questions, not an independent holdout. A warm, shared local model and query/cache effects mean the latency numbers are observations, not a reliable speedup estimate.

## Final comparison

| Measure | Baseline | Improved |
| --- | ---: | ---: |
| Correct answers, including clarifications | 9 / 10 | 10 / 10 |
| Actual model calls | 18 | 16 |
| Total answer wall time | 29.06 s | 23.64 s |
| Rejected attempts | 4 | 0 |
| Metadata observations on these ten ordinary questions | 0 | 0 |

The baseline product-ranking case `dev08` exhausted attempts because citations failed validation. No rejected SQL was executed. Baseline `dev01` also needed citation repair. Improved answered both correctly in this run. This small comparison does not establish general accuracy or attribute causality to the tools: neither version selected metadata tools on the ordinary ten questions, because schemas were already supplied.

## Additional live checks

- Six existing Thai questions: **6/6 correct** (four SQL results, two policy clarifications). These were selected for varied families, not a full run of the 200-question bilingual bank.
- Explicit schema-inspection request: the real model selected `describe_table`, received one actual loaded-schema observation, then generated/reviewed/executed SQL and matched the independent invoice-count gold. Three model calls total. This is evidence of a requested tool action, not spontaneous tool selection on ordinary questions.
- Controlled recovery: the first real model response was deliberately overridden with `DROP TABLE orders`; the guard blocked it before execution. Following repair and reviewer calls used the real model, with real OPA/Spark. Exactly one safe SQL query executed and matched gold. This is a fault-injection check, not a claim that the model spontaneously made and repaired this mistake.
- Real OPA decisions: **5/5 expected outcomes** for allowed read, write prohibition, private table prohibition, attempt limit and invalid fraction. Denied tests submitted policy facts; no destructive query was attempted against HDFS.
- MCP subprocess over stdio: **7/7 checks passed**: registration, metadata, unknown-table denial, empty-input denial, actual guarded PySpark analysis, pseudonymized `customer_id`, and omission of internal SQL/attempts/trace from exported results.
- Final Linux unit suite: **106/106 passed**, including the 100 original tests and actual MCP SDK tests. No test was removed. Windows had also passed 106/106 earlier. Remote CI was not triggered.

## Problems found and fixed during live testing

1. Starting the MCP server through `spark-submit` merged Python warnings into protocol stdout. Added `scripts/mcp_stdio.sh`, which starts Python directly with the installed Spark/Py4J libraries. Final MCP tests used this launcher successfully. An upstream lifespan-settings warning still appears on stderr, without corrupting the protocol.
2. The original optional-tool prompt caused a real model to return a clarification when explicitly asked to inspect schema. Clarified the metadata-turn JSON format and the transition from observation to SQL. The final explicit-tool test passed. The complete ten-question paired comparison was repeated after this prompt change; the table above is the final run, not the earlier run.

## Evidence and remaining limits

The delivery's `live-validation-evidence.zip` contains final paired results, extended Thai/tool/recovery results, MCP results, Linux unit output, model provenance, baseline agent source, and the three test harnesses. The initial run artifacts are retained separately inside that archive for audit. Test harnesses expect the checkout at `/app` and evidence directory at `/validation`. The comparison harness is run with the existing Spark image's `spark-submit`; the MCP client runs with Python and launches the server using `scripts/mcp_stdio.sh`. MCP test dependencies were installed into `/validation/mcpdeps`, outside the project and source data.

No full acceptance/200-question suite, fresh holdout, repeated statistical experiment, distributed-worker comparison, remote deployment or GitHub CI run was performed. MCP pseudonymization remains limited to exact `customer_id` columns; aliases/derived identifiers/free text are not general DLP. See [implementation details and privacy limits](agentic-improvements.md).
