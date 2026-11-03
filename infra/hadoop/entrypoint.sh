#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  namenode)
    if [ ! -f /data/name/current/VERSION ]; then
      hdfs namenode -format -nonInteractive
    fi
    # Bootstrap the fixed application root after the server becomes available.
    # Only runs mkdir/chown/chmod on this root, never on stored table contents.
    (
      for attempt in $(seq 1 60); do
        if hdfs dfsadmin -safemode get 2>/dev/null | grep -q 'Safe mode is OFF'; then
          if hdfs dfs -mkdir -p /customer_intelligence &&
             hdfs dfs -chown ci_etl:ci_readers /customer_intelligence &&
             hdfs dfs -chmod 750 /customer_intelligence; then
            exit 0
          fi
        fi
        sleep 2
      done
      echo 'HDFS root bootstrap failed' >&2
      exit 1
    ) &
    exec hdfs namenode
    ;;
  datanode) exec hdfs datanode ;;
  *) echo 'Expected namenode or datanode' >&2; exit 2 ;;
esac
