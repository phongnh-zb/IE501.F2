#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PROJECT_ROOT/configs/config.sh"

# Hadoop takes a while to start, so we only start it if it's not running
if ! jps | grep -q "NameNode"; then
    echo ">>> [START] Starting Hadoop (HDFS)..."
    start-all.sh
else
    echo "✔ Hadoop (HDFS) is already running."
fi

# Similarly, only start if not running
if ! jps | grep -q "HMaster"; then
    echo ">>> [START] Starting HBase..."
    start-hbase.sh
else
    echo "✔ HBase Master is already running."
fi

# For Thrift, we always Kill and Restart to avoid "Broken Pipe" or "Timeout" errors
echo ">>> [RESET] Refreshing HBase Thrift Server..."

# Find and kill old Thrift process (if any)
# 'xargs -r' prevents errors if no pid is found
jps | grep ThriftServer | awk '{print $1}' | xargs -r kill -9 2>/dev/null

# Wait for OS to release the port (important)
echo "-> Waiting for port $HBASE_PORT release..."
sleep 2

# Restart
echo ">>> [START] Starting new Thrift Server (Port $HBASE_PORT)..."
hbase thrift start -p "$HBASE_PORT" --infoport "$HBASE_THRIFT_INFO_PORT" > /dev/null 2>&1 &

echo "✔ Thrift start command sent."

# ── HDFS safe mode ────────────────────────────────────────────────────────────
# After a restart the NameNode enters safe mode while verifying block replication.
# On a single-node pseudo-distributed cluster it may never exit automatically.
# Waiting briefly then forcing exit prevents the ETL from failing with
# "Name node is in safe mode."
echo ">>> [HDFS] Waiting for NameNode to initialise..."
sleep 5
if jps | grep -q "NameNode"; then
    echo ">>> [HDFS] Forcing safe mode exit..."
    hdfs dfsadmin -safemode leave 2>/dev/null && echo "✔ HDFS safe mode cleared." || echo "  (safe mode already off or NameNode not ready)"
fi

# ── Docker (optional — dashboard only) ───────────────────────────────────────
# Docker is not required for the pipeline. This block starts the web dashboard
# container if Docker is available and the daemon is running.
if command -v docker &>/dev/null; then
    if docker info &>/dev/null 2>&1; then
        echo ">>> [DOCKER] Daemon is running — starting dashboard container..."
        docker compose -f "$PROJECT_ROOT/docker-compose.yaml" up -d 2>/dev/null \
            && echo "✔ Dashboard container started." \
            || echo "  (docker compose failed — check docker-compose.yaml)"
    else
        echo ">>> [DOCKER] Daemon not running — skipping dashboard container."
        echo "  Start Docker Desktop manually to run the web dashboard via Docker."
        echo "  Or run directly: python3 webapp/app.py"
    fi
else
    echo ">>> [DOCKER] Not installed — skipping."
fi