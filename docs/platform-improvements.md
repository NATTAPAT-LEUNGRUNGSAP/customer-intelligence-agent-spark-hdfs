> Historical audit/source validation: for the integrated deployed system and current test results, see [CURRENT_STATE.md](CURRENT_STATE.md). Main web is now8090; preview8091 is stopped.

# Storage roles, bounded conversation and charts — 3 November 2026

## Browser demonstration follow-up

The in-app browser subsequently reached the preview and a real UI demonstration completed: October invoices **2,040**, the Thai follow-up “แล้วเดือนก่อนล่ะ” resolved to September with **1,837**, and a Thai top-five-country question displayed the table and bar chart. Screenshots are included in the delivery. This supersedes the initial visual-access limitation described below.

The demonstration exposed two real defects: Thai country-ranking wording without the literal word “อันดับ” was mistaken for a scalar request, and the model could omit LIMIT while the reviewer still approved. Fixed breakdown recognition for explicit Thai ranked-country/output requests and added a deterministic outer-LIMIT check plus a ranking-limit request constraint for recognized English/Thai top-N phrases. Regression tests preserve scalar treatment of “ยอดขายรวมใน 5 ประเทศเท่าไร”. These narrow checks do not claim complete natural-language ranking understanding. The expanded Python suite now contains 121 tests.

## What changed

- HDFS permissions enabled. The application tree is owned by `ci_etl:ci_readers`, directories use 750 and files 640. New files inherit group permissions with umask 027. `ci_analyst` is a reader; legacy `spark` is temporarily mapped to the reader group so the existing web process can keep reading. `spark-job` remains the ETL service; new `analytics-job`, `ask.ps1`, `evaluate.ps1` and the web service use the analyst identity.
- Web, MCP and agent CLI now ask HDFS itself to confirm READ/EXECUTE is allowed and WRITE is denied on the build root and its application parents before serving queries. They refuse to start under a writer identity or when permissions are disabled. The older `--require-read-only` option remains accepted for compatibility; the check is always performed.
- The local running HDFS deployment was migrated using a metadata/config backup. No existing Parquet table was rebuilt or overwritten. A separate preview web container runs as `ci_analyst` on **http://localhost:8091**. The old web at 8090 remains on its old code, now constrained by the same storage permissions. Ollama was found stopped and restarted using its existing executable/default local configuration; no model was downloaded and no network binding was widened.
- Server-side browser sessions keep at most eight compact questions/statuses for 30 minutes. Month-before/month-after follow-ups reuse only the last successful question and preserve the metric/country while shifting an unambiguous one-month period. The resolved question is displayed. Arbitrary references such as “those customers” are clarified rather than guessed. Previous SQL, rows, errors and hidden reasoning are not supplied as conversational instructions.
- Per-session quota is 20 accepted questions per 30-minute lifetime, with a maximum of 128 active sessions. Cookies use HttpOnly and SameSite=Strict. These are anonymous browser sessions, **not authenticated per-user quotas**: a new cookie can start a new session. Multi-user production use still requires authentication and a shared quota store. Restarting the process loses history/quotas.
- Bar, chronological line and numeric scatter charts are built in the browser from server-provided, result-contract-validated data. Axes are selected from actual returned columns; no model HTML, JavaScript or plotting code is executed. Charts cap at 100 points and warn if partial; exact returned table values remain visible. A scalar answer alone has no chart. Line charts require date/year-month x-values; scatter needs numeric x and y.
- Metadata inspection now includes loaded column types/nullability, manifest row counts, table grain, declared logical keys and a customer relationship. Keys are explicitly labelled as logical, not database-enforced; counts are build-time metadata. Full metadata is fetched on demand instead of duplicating it in every model prompt.
- Added focused Ruff checks and typed checks for the new input/session/chart modules, four Node chart-renderer tests, and CI steps. This is incremental coverage, not strict typing/lint cleanup of the entire legacy project.

## Validation

| Check | Result |
| --- | --- |
| Python unit suite | 120/120 on Windows and Linux Spark image |
| Chart renderer unit checks | 4/4; negative bars, safe text, line/scatter axes, truncation |
| Ruff and mypy | Passed on configured scope |
| Compose validation and JavaScript syntax | Passed |
| Real HDFS + analyst Spark | 5/5: read-only startup, 40,077 invoices read, richer metadata, DataFrame write denied, SQL write denied |
| Real writer-role Spark | 2/2: ETL writes disposable fixture, writer startup rejected for analytics |
| Direct HDFS CLI | 7/7: ETL create, analyst read, append/chmod/rename/delete denied, unmapped identity denied |
| Live web HTTP API + Ollama/OPA/Spark/HDFS | 10/10: October gold, cookie flags, September follow-up gold, visible scope, session isolation, country gold, chart data, input cap, override rejection, quota |

MCP was also checked against the same read-only deployment; see `platform-validation.json` in the delivery for the final result. The independent gold queries were executed directly against the same HDFS build. The web check uses only three model-backed questions; quota tests use grounded formula responses requiring no model. This is a functional smoke test, not a new accuracy benchmark. Previous paired accuracy/latency reports describe earlier revisions and must not be presented as measurements of this version.

The in-app browser could not reach the host's localhost, and native Chrome computer-use was not approved. Therefore no visual screenshot QA is claimed. JavaScript renderer tests and live API checks passed; the user should inspect the preview layout in their own browser. GitHub CI was edited but not run remotely. Spark live tests used local[1]/local[2] with real HDFS; the standalone worker deployment and a brand-new cluster bootstrap were not exercised in this revision.

## Security boundary

Hadoop remains in **simple authentication mode**. Server-side permissions genuinely reject writes made as `ci_analyst`, including when the application SQL guard is bypassed. They do not authenticate the name against a hostile process controlling Docker/the host: such a process can impersonate `ci_etl` or the superuser. This is a local role separation, not a Kerberos-secured multi-tenant cluster. Do not expose HDFS or Spark directly to untrusted clients. For that setting, deploy strong authentication, network isolation and separately managed credentials. See the [Apache HDFS permissions guide](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsPermissionsGuide.html).

The Spark startup check is scoped to the protected application tree. It does not create a global filesystem/network sandbox comparable to DuckDB's disabled external access. Existing AST/function/table allowlists, OPA, semantic checks, reviewer, deadlines and result contracts remain mandatory. Pseudonymization still applies only to exact `customer_id` export columns through MCP. Prompt-injection and alias/free-text limitations described in the earlier reports remain.

## Using and rolling back the local deployment

Open http://localhost:8091 and ask `How many completed invoices were recorded in October 2011?`, then `แล้วเดือนก่อนล่ะ` with the follow-up checkbox enabled. For a chart, ask for sales by country/month, then select chart type and axes below the result. Start a separate browser session for independent history; do not use new sessions as a substitute for authenticated quota enforcement.

For the updated checkout, use `analytics-job` for analysis and `spark-job` for ETL. Rebuild/prepare data through `scripts/build-data.ps1`; query through `scripts/ask.ps1`. Direct analysis containers/MCP must set `HADOOP_USER_NAME=ci_analyst` and use the configured HDFS network. Do not run analytics under `ci_etl`.

The delivery includes `hdfs-permissions-backup.zip` and `rollback-local-hdfs.ps1`. The rollback helper restores the inspected original XML configs and each recorded owner/group/mode, then restarts the NameNode; it does not delete tables. Original backup location is under this chat's `work/hdfs-permissions-backup`. The helper is for this exact inspected local deployment, not a generic migration tool. Restoring old disabled permissions would remove the new storage protection and cause new analytics services to refuse startup. Stop the preview first if rolling back. Test fixtures remain only under `/customer_intelligence/security_validation`; production tables were not modified.

No commit, push, remote branch, PR or external publication was performed.
