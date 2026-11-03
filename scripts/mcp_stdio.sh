#!/usr/bin/env bash
# Start Python directly: spark-submit merges Python stderr into protocol stdout.
set -euo pipefail
export SPARK_HOME="${SPARK_HOME:-/opt/spark}"
py4j_archives=("$SPARK_HOME"/python/lib/py4j-*-src.zip)
if [[ ! -f "${py4j_archives[0]}" ]]; then
  printf 'Py4J archive not found under SPARK_HOME\n' >&2
  exit 1
fi
export PYTHONPATH="$SPARK_HOME/python:${py4j_archives[0]}${PYTHONPATH:+:$PYTHONPATH}"
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$project_root/jobs/mcp_server.py" "$@"
