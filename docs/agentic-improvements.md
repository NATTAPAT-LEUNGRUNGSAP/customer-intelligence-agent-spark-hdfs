> Historical audit/source validation: for the integrated deployed system and current test results, see [CURRENT_STATE.md](CURRENT_STATE.md). Main web is now8090; preview8091 is stopped.

# Evidence and implementation — 3 November 2026

Latest follow-up: [storage roles, conversation, charts, metadata and CI](platform-improvements.md). Earlier counts and live comparisons below are historical.

Update: [shared web/MCP/CLI input validation and targeted injection checks](input-guard.md) now use a uniform 2,000-character limit. Earlier live comparison results describe the revision before this input-guard change.

Target baseline: `76629c472bdde02c8c4490bf95a5bece468c1ea2` (main).
All changes are local; no GitHub branch, push, PR, deployment or source-data modification.

## Sources read and decisions

| Primary source | Relevant evidence | Application here |
| --- | --- | --- |
| [StreamLink, arXiv 2505.21575v1](https://arxiv.org/html/2505.21575v1), sections 3.1–3.3 and 4 | Local domain-aware generation, Spark/Hadoop coordination, syntax/security checking, separate execution-accuracy and interception experiments | Preserve local Ollama, mandatory retrieval, AST guard, OPA, reviewer, bounded Spark action. These already existed; they are not newly implemented StreamLink features. |
| [Spark Streaming + agents, arXiv 2501.14734v1](https://arxiv.org/html/2501.14734v1), sections 2.6, 5, 6 | Conditional workflow, loops, observations, state and human oversight; quantitative experiments concern cardinality estimation | Add bounded metadata-tool selection and observation-driven next generation, with inspectable trace. No streaming/Kafka/LangGraph migration. The paper's cardinality results are not evidence of this project's agent accuracy. |
| [datenwissenschaften/agentic-data-analyst](https://github.com/datenwissenschaften/agentic-data-analyst/tree/3e52549680a67c227bf876e3468cb53d244f3d4b), README and database.py | Metadata discovery, deterministic checks before reviewer, bounded query execution | Implement allowlisted metadata tools using existing registered Spark schemas. Current source uses DuckDB, Anthropic and plain tool calls; it does **not** supply MCP or PySpark. MCP here is an original adapter, not copied functionality. |

No paper benchmark numbers are presented as measurements of this project. No reference code was copied.

## Actual changes

- `jobs/agent.py`: optional structured `plan` action labels and `tools`; metadata requests are validated, observed and fed back to generation **before** SQL execution. They share the existing three-attempt budget. Existing responses without tools remain supported. `agent_trace` records retrieval, plan/tool observations, reviewer approval, result row count/truncation, repair and failed stop. No hidden chain-of-thought is requested.
- `jobs/agent_tools.py`: `list_tables` and `describe_table` accept only the three existing analytics views and only known argument keys. Four calls per attempt; eight short plan labels maximum. No rows, arbitrary code, file paths or SQL execution tools.
- `jobs/mcp_server.py`: optional local stdio FastMCP server with schema tools plus high-level `analyze(question)`. Analysis uses existing RAG → SQL/semantic/metric guards → OPA → reviewer → bounded PySpark → result contracts. No raw SQL execution endpoint. Existing web and CLI interfaces stay compatible.
- `jobs/pseudonymization.py`: HMAC-SHA256 of exact `customer_id` result columns at the MCP export boundary, using a required secret of at least 32 bytes. Stable within a key, different across keys, preserves nulls and source values. Stored IDs, joins, source CSV and formulas remain intact.
- `jobs/evaluate_agent_trace.py`: measured counts for execution, repaired execution, metadata observations and model calls from saved JSON arrays. Accuracy deliberately stays null; existing expected-result evaluators remain necessary.
- `tests/test_agent_tools.py`: six additional tests for tool allowlisting, observation-driven replanning, bounded loops, export pseudonyms, actual MCP SDK registration/invocation and evaluation semantics. CI installs optional MCP requirements to exercise the SDK test.

## Running

Existing install and app commands continue to work. For MCP, install `requirements-mcp.txt` in the existing Spark environment (PySpark is supplied by the existing Spark runtime). Set `OLLAMA_MODEL`, the existing `OPA_URL`/`OLLAMA_URL`, and a randomly generated `CUSTOMER_PSEUDONYM_KEY` of at least 32 bytes via the environment. Do not put the key in source control or chat.

```sh
python jobs/mcp_server.py --manifest /path/to/passed-manifest.json --knowledge /app/knowledge
python -m unittest discover -s tests -v
python jobs/evaluate_agent_trace.py saved-answer-array.json
```

The manifest must pass the existing HDFS-root validation. Keep MCP on stdio; no HTTP listener or remote service was added. Metadata schema is already in the generation prompt; optional tools add explicit inspection and observation, not access to previously hidden data. Metadata-only turns consume attempts, so repeated tool requests can exhaust the budget without executing.

In the Spark Linux container, use `bash scripts/mcp_stdio.sh --manifest /app/reports/build-<run-id>.json`. Set `PYSPARK_SUBMIT_ARGS` for the desired Spark master, for example `--master local[1] --conf spark.hadoop.dfs.client.use.datanode.hostname=true pyspark-shell`. The launcher imports the installed Spark/Py4J libraries and starts Python directly. Do **not** wrap this stdio server in `spark-submit`: Spark's Python runner merges Python stderr into stdout and can corrupt JSON-RPC with dependency warnings. The launcher keeps diagnostic messages separate from protocol output.

## Validation and limits

Initial local Windows Python 3.13.15 validation: all 100 pre-existing tests passed before addition; suite has 106 tests. Actual MCP SDK 1.26.0 was installed and its tool registration/invocation exercised. Model, OPA and Spark execution are fixtures in unit tests. Existing HTTP contract test uses a local test server. Subsequent live validation of Spark/HDFS/OPA/Ollama, MCP subprocess transport and Thai questions is documented in [the live-validation report](live-validation-2026-11-03.md). Docker access worked with the necessary execution permission; the initial restricted attempt did not access Docker.

MCP/Pydantic emits an upstream `IncompleteFieldDefinitionWarning` about lifespan settings; tool tests pass. The Linux Spark image also passed all 106 unit tests. Python 3.11 GitHub CI has been updated but was not run remotely.

Pseudonymization is an opt-in MCP export feature, **not anonymization or general DLP**: it handles exact `customer_id` output columns, not aliases, derived IDs, SQL literals, free text or all identifying fields. The CLI/web retain their previous behavior. Do not expose sensitive data remotely without extending lineage-aware output policy and reviewing free-text/alias cases. Keys must be managed and rotated by the operator; rotating a key breaks cross-export linkage. Aggregate disclosure controls and authentication are outside this change.

For a real evaluation, run existing acceptance/bilingual expected-result suites against the same passed manifest/model before and after. Compare result equality, policy failures, model calls and latency. Trace execution rate alone must never be reported as accuracy or an improvement percentage.
