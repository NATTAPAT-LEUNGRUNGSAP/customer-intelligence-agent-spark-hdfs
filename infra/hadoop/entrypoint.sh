#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  namenode)
    if [ ! -f /data/name/current/VERSION ]; then
      hdfs namenode -format -nonInteractive
    fi
    exec hdfs namenode
    ;;
  datanode) exec hdfs datanode ;;
  *) echo 'Expected namenode or datanode' >&2; exit 2 ;;
esac
