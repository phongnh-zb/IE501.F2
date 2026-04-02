#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PROJECT_ROOT/configs/config.sh"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; RESET='\033[0m'

up()   { echo -e "  ${GREEN}●  UP${RESET}      $1"; }
down() { echo -e "  ${RED}●  DOWN${RESET}    $1"; }
info() { echo -e "     ${YELLOW}→${RESET}          $1"; }

section() { echo -e "\n$1"; }

jps_check()  { jps 2>/dev/null | grep -q "$1"; }
port_open()  { bash -c "echo >/dev/tcp/localhost/$1" 2>/dev/null; }

# ── Hadoop ───────────────────────────────────────────────────────────────────

section "Hadoop"
jps_check "NameNode"        && up "NameNode"        || down "NameNode"
jps_check "DataNode"        && up "DataNode"        || down "DataNode"
jps_check "ResourceManager" && up "ResourceManager" || down "ResourceManager (YARN)"

# ── HBase ────────────────────────────────────────────────────────────────────

section "HBase"
jps_check "HMaster"    && up "HMaster"    || down "HMaster"

# ── HBase Thrift ─────────────────────────────────────────────────────────────

section "HBase Thrift (port $HBASE_PORT)"
if jps_check "ThriftServer"; then
    up "ThriftServer process running"
elif port_open $HBASE_PORT; then
    up "Port $HBASE_PORT open (process name differs)"
else
    down "ThriftServer — port $HBASE_PORT is closed"
fi

# ── Flask ────────────────────────────────────────────────────────────────────

section "Flask Dashboard (port $FLASK_PORT)"
if port_open $FLASK_PORT; then
    up "Listening on http://localhost:$FLASK_PORT"
else
    down "Not running on port $FLASK_PORT"
    info "Start with: python3 webapp/app.py"
fi

# ── HDFS Data ────────────────────────────────────────────────────────────────

section "HDFS paths"
if jps_check "NameNode"; then
    for CHECK_PATH in "$HDFS_BASE_PATH" "$HDFS_OUTPUT_PATH"; do
        if hdfs dfs -test -e "$CHECK_PATH" 2>/dev/null; then
            FILE_COUNT=$(hdfs dfs -ls "$CHECK_PATH" 2>/dev/null | grep -vc "^Found")
            info "$CHECK_PATH   ($FILE_COUNT files)"
        else
            info "$CHECK_PATH   (not found)"
        fi
    done
else
    info "Skipping HDFS checks — NameNode is down"
fi

# ── HBase table ──────────────────────────────────────────────────────────────

section "HBase table: $TABLE_NAME"
if jps_check "HMaster"; then
    ROW_COUNT=$(
        echo "count '$TABLE_NAME', INTERVAL => 1000000" \
        | hbase shell 2>/dev/null \
        | grep -oP '^\d+' \
        | tail -1
    )
    if [ -n "$ROW_COUNT" ]; then
        info "Row count: $ROW_COUNT"
    else
        info "Table not found or empty — run python3 main.py first"
    fi
else
    info "Skipping table check — HMaster is down"
fi

echo ""