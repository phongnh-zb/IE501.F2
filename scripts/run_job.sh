#!/bin/bash
# Manual step-by-step execution for debugging. For the full automated pipeline use: python3 main.py
# Usage:
#   ./scripts/run_job.sh           # run all three steps
#   ./scripts/run_job.sh etl       # ETL only
#   ./scripts/run_job.sh train     # model training only
#   ./scripts/run_job.sh hbase     # HBase write only

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$PROJECT_ROOT/configs/config.sh"

STEP="${1:-all}"
SPARK_MASTER="$MASTER"

GREEN='\033[0;32m'; RED='\033[0;31m'; BLUE='\033[0;34m'; RESET='\033[0m'

step_header() { echo -e "\n${BLUE}>>> [$1]${RESET}"; }
step_ok()     { echo -e "${GREEN}✔ $1${RESET}"; }
step_fail()   { echo -e "${RED}✘ $1 — aborting.${RESET}"; exit 1; }

run_etl() {
    step_header "ETL — spark-submit src/etl_job.py"
    spark-submit \
        --master "$SPARK_MASTER" \
        "$PROJECT_ROOT/src/etl_job.py"
    [ $? -eq 0 ] && step_ok "ETL complete" || step_fail "ETL failed"
}

run_train() {
    step_header "TRAINING — spark-submit src/train_model.py"
    spark-submit \
        --master "$SPARK_MASTER" \
        "$PROJECT_ROOT/src/train_model.py"
    [ $? -eq 0 ] && step_ok "Training complete" || step_fail "Training failed"
}

run_hbase() {
    # save_to_hbase.py uses happybase only — no Spark needed, plain python3 is correct
    step_header "HBASE WRITE — python3 src/save_to_hbase.py"
    python3 "$PROJECT_ROOT/src/save_to_hbase.py"
    [ $? -eq 0 ] && step_ok "HBase write complete" || step_fail "HBase write failed"
}

case "$STEP" in
    etl)   run_etl ;;
    train) run_train ;;
    hbase) run_hbase ;;
    all)
        run_etl
        run_train
        run_hbase
        ;;
    *)
        echo "Usage: $0 [etl|train|hbase|all]"
        exit 1
        ;;
esac