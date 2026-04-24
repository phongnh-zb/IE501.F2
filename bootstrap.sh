#!/usr/bin/env bash
# ============================================================
#  Student Dropout Prediction System — bootstrap.sh
#  Full pipeline from scratch in one command.
#
#  What this script does:
#    1. Stop any running services (safe if nothing is running)
#    2. Hand off to main.py which handles:
#         verify env → start services → setup HDFS →
#         ETL → train → save to HBase
#
#  Usage: bash bootstrap.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"

_header() {
  echo ""
  echo "============================================"
  echo "  $1"
  echo "============================================"
}

{
  _header "Student Dropout Prediction System — Full Pipeline Bootstrap"
  echo "  Log: $LOG_FILE"
  echo "  Started: $(date '+%Y-%m-%d %H:%M:%S')"

  # Stop any leftover services before a clean run.
  # || true prevents abort if services were not running.
  echo ""
  echo ">>> Stopping existing services (if any)..."
  bash "$SCRIPT_DIR/scripts/stop_services.sh" || true

  # Delegate everything else to main.py:
  # verify env → start services → setup HDFS → ETL → train → HBase
  echo ""
  echo ">>> Handing off to main.py..."
  python3 -u "$SCRIPT_DIR/main.py"

  _header "Bootstrap complete"
  echo "  Finished: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "  Log saved: $LOG_FILE"
  echo ""
  echo "  Start the dashboard: python3 webapp/app.py"
  echo "  Open: http://localhost:5001"

} 2>&1 | tee "$LOG_FILE"