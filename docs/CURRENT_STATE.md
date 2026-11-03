# Current integrated system — 3 November 2026

The two chats now use one integrated checkout and main web service at **http://localhost:8090**.
The former preview container at 8091 was stopped after main-service checks passed.
The original current deck remains 31 slides; its runtime diagrams/metrics have not been updated for these features.

## Incorporated work

- Preserved this checkout's aggregation fixes, multi-dimension result checks and explicit product-ID sorting.
- Added optional metadata planning/list_tables/describe_table, observation-driven turns and recorded agent events within the existing three-turn budget.
- Added a real optional stdio MCP server with analytics/metadata tools. The web host still invokes Python directly; it is not an internal MCP client.
- Added targeted input guard, bounded anonymous conversation sessions/follow-up and data-derived bar/line/scatter charts.
- Main dashboard has shared date/country controls, four KPIs and monthly/country/product/RFM sections. Dashboard uses trusted fixed queries through guards/OPA; AI still uses mandatory RAG and model-generated SQL.
- Added analyst startup read/write-access checks and separate analytics-job. The HDFS permission migration performed in the other chat was preserved, not repeated. No build data was rebuilt or overwritten.
- During integration, an actual AI count query failed on citations three times. Added exact allowed citation IDs to the prompt/repair feedback without bypassing citation validation; repeated deployed checks passed afterward.

## Actual integrated validation

- Full Python suite: **136/136**, including MCP SDK tests and prior aggregation regressions (local-integration-unit-tests-full.txt).
- Node chart renderer: **4/4** (local-integration-chart-tests.txt).
- Configured Ruff/mypy, JavaScript syntax and Compose validation passed. These checks are scoped, not whole-project strict type coverage.
- Main 8090 HTTP: **6/6** checks with actual standalone Spark/HDFS/OPA and the actual model on AI paths (local-integration-http-verification.json).
- Dashboard all-data, October and October/Germany returned all five sections; October KPIs: sales1154979.30, invoices2040, AOV566.17, buyers1364; Germany:31638.42,58,545.49,38.
- AI October2040 → September1837 follow-up and Germany58 matched expected invoice counts.
- Main dashboard visually inspected in browser; screenshot integrated-dashboard-main.png.
- Other-chat claims of independent15/15 section gold, MCP9/9 and writer/reader checks are retained as historical source validation, not relabelled as a rerun of this merged revision.
- No complete 200-question run or new independent holdout on this integrated revision. Previous196/200 and aggregation3/8→6/8 refer to their recorded prior sources.

## Limits and operational notes

Hadoop is still simple auth, not Kerberos; a host/Docker operator can impersonate identities.
HMAC pseudonymization is limited to exact customer_id export columns in the MCP adapter. It does not cover aliases/free text or all web/CLI data and is not anonymity/general DLP.
Input guard covers targeted patterns, not all prompt injections. Sessions/quotas are anonymous, in-process, and reset on restart; they are not authenticated per-user governance.
RFM charts filter purchasers who exist in the prebuilt2011-12-01 snapshot, not a newly computed snapshot. Product codes include M/DOT/POST and similar source entries.
MCP requires requirements-mcp.txt and an operator-supplied secret; no public MCP HTTP listener or long-running MCP service was deployed. No key was checked into Git.

After successful integration and deployment, the user requested removal of unused versions. Removed the ignored integration rollback/snapshot directory, legacy overrides, old diagnostic source copies and the stopped8091 preview container. Removed319 verified redundant source files from the former checkout, plus its Git and lint caches; no unique source changes were discarded. The current committed checkout and its Git history remain the source of truth.

The former source location now retains only the Python validation environment (and a pointer README); the environment remains at its existing absolute path so installed tool launchers keep working. It is not an old running app. Current main web uses only this checkout.

Normal startup uses current compose.yaml + compose.web.yaml as ci_analyst. Do not repeat HDFS migration unless separately required. HDFS tables, raw datasets, credentials and current136-test validation dependencies were preserved.
