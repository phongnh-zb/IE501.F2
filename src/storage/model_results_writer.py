import json
from datetime import datetime

from common.hbase_client import ensure_table, hbase_connection
from configs import config
from src.models.explain import extract_feature_importance, importance_to_json


def write_model_results(all_results, best_name, feature_cols, run_id, tuning_results=None):
    print(">>> [MODEL RESULTS] Connecting to HBase...")
    tuning_results = tuning_results or {}

    with hbase_connection() as conn:
        ensure_table(conn, config.MODEL_RESULTS_TABLE, ["metrics", "info", "importance", "tuning"])
        table = conn.table(config.MODEL_RESULTS_TABLE)

        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        batch = table.batch()

        for name, result in all_results.items():
            model_key = name.replace(" ", "_")
            row_key   = f"{model_key}|{run_id}".encode()

            metrics  = result["metrics"]
            ranked   = extract_feature_importance(result["model"], feature_cols)
            imp_json = importance_to_json(ranked)

            # Tuning data — empty JSON for models not tuned
            tuning = tuning_results.get(name, {})
            tuning_json = json.dumps(tuning) if tuning else "{}"

            batch.put(row_key, {
                b"metrics:auc":            str(round(metrics.get("auc", 0.0), 4)).encode(),
                b"metrics:accuracy":       str(round(metrics.get("accuracy", 0.0), 4)).encode(),
                b"metrics:precision":      str(round(metrics.get("precision", 0.0), 4)).encode(),
                b"metrics:recall":         str(round(metrics.get("recall", 0.0), 4)).encode(),
                b"metrics:f1":             str(round(metrics.get("f1", 0.0), 4)).encode(),
                b"metrics:cv_auc":         str(round(metrics.get("cv_auc", 0.0), 4)).encode(),
                b"metrics:composite_score":str(round(metrics.get("composite_score", 0.0), 4)).encode(),
                b"metrics:training_time":  str(metrics.get("training_time", 0.0)).encode(),
                b"info:run_id":           run_id.encode(),
                b"info:timestamp":        ts.encode(),
                b"info:is_best":          ("true" if name == best_name else "false").encode(),
                b"importance:json":       imp_json.encode(),
                b"tuning:json":           tuning_json.encode(),
            })

        batch.send()
        print(f">>> [MODEL RESULTS] Wrote {len(all_results)} records for run {run_id}.")