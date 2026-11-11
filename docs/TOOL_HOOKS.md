# Tool lifecycle hooks

The Agent and Dashboard share `jobs/tool_hooks.py` at the Spark SQL boundary.
Web, CLI and MCP requests that use the Agent inherit this boundary. Metadata
tools do not use it; SQL/citation/semantic checks remain explicit upstream checks.

```text
SQL/evidence checks and review
  -> before_tool: OPA authorization
  -> Spark SQL
  -> after_tool: result contract and OPA authorization
  -> return validated result
```

Before-hook exceptions prevent Spark execution. After-hook exceptions prevent
result delivery. Failures are recorded in `hook_trace` with stage, tool, attempt
and exception type, without copying SQL, questions or result rows into the trace.
Agent failures continue through the existing bounded repair loop; this module
does not add retries. Dashboard failures propagate to its existing error handler.

`on_error` accepts optional trusted Python observers. Observer errors are recorded
without replacing the original exception. No custom error observer is registered
by default; failure events are always recorded by the runner.

Example extension in trusted application code:

```python
hooks = ToolHooks(
    before_tool=(authorize_request,),
    after_tool=(validate_output,),
    on_error=(record_failure,),
)
result = hooks.run('spark_sql', lambda: execute(sql), attempt=1)
```

Hooks are synchronous Python callbacks, not plugins supplied by users, the model
or RAG documents. There is no hook sandbox or interruption deadline for arbitrary
callbacks. Existing tool timeouts remain in the execution layer. These hooks do
not prove business correctness of every returned answer.

## Local verification — 5 November 2026

Executed: 4 hook lifecycle tests, 6 Dashboard tests, 23 Agent tests, and
1 metadata-to-SQL Agent flow test: 34 passed. Focused Ruff F/E9 checks passed.
These use mocked execution/policy/model boundaries, not live Spark/OPA/Ollama.
The full discovery run was interrupted while entering the MCP SDK test; it is
not reported as passing. No fresh live benchmark or container restart was done.
