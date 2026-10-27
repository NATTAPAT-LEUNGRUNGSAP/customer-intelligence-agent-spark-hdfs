# Local web application

The web form provides an analysis-period selector, defaulting to **all available data**.
Choose custom start/end dates when needed; both selected dates are included.
SQL uses the equivalent half-open range ending at midnight after the selected end date.
An explicit period or snapshot in the question takes precedence over the selector.
The answer displays which scope was used. Formula/discovery/unavailable-field requests
remain independent of the selected transaction period; snapshots still need their date.
Month names without a year and relative periods are not silently converted to all data.
The historical dataset does not become current data by choosing “today”.

“สินค้าขายดีสุด 10 อันดับ” asks whether to rank by units or revenue, without asking
for a period when the web selector already supplies one. Ask “มีข้อมูลอะไรบ้าง”
for the loaded tables and columns. No verified product-category taxonomy is present.
The API accepts optional `time_selection`: `{"mode":"all"}` or
`{"mode":"custom","start":"2011-10-01","end":"2011-10-31"}`.
API/CLI callers omitting that field keep the previous missing-period clarification.

An unqualified highest-month invoice question still retains all tied highest months
across calendar year-months for the all-data selector. A custom selector uses its
requested period instead.

Start the cluster with scripts/start.ps1 and ensure Ollama serves qwen3.5:9b at
host.docker.internal:11434 from the container. Build data with scripts/build-data.ps1
if this is a new checkout. The build emits a NEW passed manifest. Edit the manifest
argument in compose.web.yaml to that passed /app/reports/build-*.json before starting;
the checked-in default refers to the original development machine's build.

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/start-web.ps1
```

Open http://localhost:8090 after Spark initialization. The app binds the published
port to localhost only. Check readiness at /api/status or Docker logs:

The startup script builds the image with ontology/SHACL dependencies and starts
the internal OPA service. OPA must be reachable at http://opa:8181 from the web
container. If its decision cannot be obtained, the agent blocks execution or
delivery rather than bypassing policy. No OPA port is published to the host.

```powershell
docker compose -f compose.yaml -f compose.web.yaml logs --tail 30 web
docker compose -f compose.yaml -f compose.web.yaml stop web
```

Stop the web service before running batch Spark evaluations to free worker memory.
The web driver has its own hostname intelligence-web and admits one query at a time.
Do not use docker compose down -v; data is stored in named HDFS volumes.

Examples:
- How many completed invoices were recorded in October 2011?
- Top three identified customers by total completed sales in January 2011; ties by customer ID ascending.
- RFM distribution at snapshot 2011-12-01.

The HTTP backend receives only a question; it owns manifest/model configuration.
It calls the same answer(), SQL guard and Spark run_query() path as the CLI.
Questions are independent. Displayed session history is not injected into prompts.
Results, clarifications and failures get a trace in reports/web-agent-*.json.
Questions/trace files may contain user-entered information and are excluded from Git.
The UI uses textContent for model output, not raw HTML rendering.

POST /api/query requires JSON {"question":"..."}, at most 2000 characters and
Origin http://localhost:8090 or http://127.0.0.1:8090. A second concurrent query gets
409. Failed model/SQL processing returns a trace with status=failed, not fake rows.
The demo has no user authentication; it is not a public hosted service.

Current verification includes actual HTTP+Qwen+Spark execution and browser rendering,
plus unit checks for origin rejection, configuration rejection, busy handling and
trace persistence. Current evidence: reports/DELIVERY_REPORT.md and
reports/web-v2.4-demo-summary.json. Older iteration records are historical.

Current Context v2 extension was also exercised through the real HTTP API:
reports/context-web-verification.json records2040 October2011 invoices and the
selected-evidence context plan. Expanded diagnostics include context_plan,
context_blocked and actual token usage. See reports/CONTEXT_REPORT.md for the
separate controlled context experiment and its limits.

Current ontology/policy integration and expanded question results are documented in reports/GOVERNANCE_REPORT.md. The domain ontology is described in docs/GOVERNANCE.md.

The updated ontology/OPA path was verified through the actual HTTP API: reports/governance-web-verification.json records 2,040 October 2011 invoices with pre/post OPA allow decisions and a missing-period clarification with zero model calls.

Optional temporary HTTPS friend access is documented in [FRIEND_ACCESS.md](FRIEND_ACCESS.md). It adds a password gateway and outbound tunnel; the existing local backend and one-query lock remain unchanged. Actual gateway verification is in reports/friend-access-verification.json.
