#!/bin/bash

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}✔  $1${RESET}"; }
info() { echo -e "${YELLOW}→  $1${RESET}"; }

echo ">>> Stopping Student Dropout Prediction services..."

# --- 1. Thrift Server (must go first — clients hold connections to it) ---
THRIFT_PID=$(jps 2>/dev/null | grep ThriftServer | awk '{print $1}')
if [ -n "$THRIFT_PID" ]; then
    info "Stopping HBase Thrift Server (PID $THRIFT_PID)..."
    kill "$THRIFT_PID" 2>/dev/null
    sleep 2
    ok "Thrift Server stopped."
else
    ok "Thrift Server was not running."
fi

# --- 2. HBase (before Hadoop — HBase WAL depends on HDFS) ---
if jps 2>/dev/null | grep -q "HMaster"; then
    info "Stopping HBase..."
    stop-hbase.sh
    ok "HBase stopped."
else
    ok "HBase was not running."
fi

# --- 3. Hadoop (HDFS + YARN, must go last) ---
if jps 2>/dev/null | grep -q "NameNode"; then
    info "Stopping Hadoop (HDFS + YARN)..."
    stop-all.sh
    ok "Hadoop stopped."
else
    ok "Hadoop was not running."
fi

echo ""
echo ">>> All services stopped."