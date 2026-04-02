#!/bin/bash
# Usage:
#   ./scripts/reset_hdfs.sh          # remove processed output and saved models only
#   ./scripts/reset_hdfs.sh --full   # also remove raw CSVs (requires re-running setup_hdfs.sh)

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PROJECT_ROOT/configs/config.sh"

GREEN='\033[0;32m'; RED='\033[0;31m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}✔  Removed: $1${RESET}"; }
skip() { echo -e "   Already absent: $1"; }

FULL_RESET=false
[ "${1}" == "--full" ] && FULL_RESET=true

echo ">>> HDFS Reset"
echo ""

if $FULL_RESET; then
    echo -e "${RED}WARNING: --full will also delete raw CSVs.${RESET}"
    echo    "         You will need to re-run ./scripts/setup_hdfs.sh before the next pipeline run."
    echo ""
fi

echo "Paths to be removed:"
echo "  $HDFS_OUTPUT_PATH"
echo "  $HDFS_MODEL_PATH"
$FULL_RESET && echo "  $HDFS_BASE_PATH"
echo ""

read -rp "Confirm? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted — no changes made."
    exit 0
fi

echo ""

remove_path() {
    local path="$1"
    if hdfs dfs -test -e "$path" 2>/dev/null; then
        hdfs dfs -rm -r "$path"
        ok "$path"
    else
        skip "$path"
    fi
}

remove_path "$HDFS_OUTPUT_PATH"
remove_path "$HDFS_MODEL_PATH"
$FULL_RESET && remove_path "$HDFS_BASE_PATH"

echo ""
echo -e "${GREEN}>>> Reset complete.${RESET}"
if $FULL_RESET; then
    echo "Next step: ./scripts/setup_hdfs.sh"
fi