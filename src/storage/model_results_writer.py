import time
from datetime import datetime

import happybase

from configs import config
from src.models.explain import extract_feature_importance, importance_to_json


def _ensure_table(connection):
    if config.MODEL_RESULTS_TABLE.encode() not in connection.tables():
        print(f">>> [MODEL RESULTS] Creating table '{config.MODEL_RESULTS_TABLE}'...")
        connection.create_table(
            config.MODEL_RESULTS_TABLE,
            {"metrics": dict(), "info": dict(), "importance": dict()},
        )
        print(">>> [MODEL RESULTS] Table created.")


def write_model_results(all_results, best_name, feature_cols):
    print(">>> [MODEL RESULTS] Connecting to HBase...")
    connection = None
    try:
        connection = happybase.Connection(
            host=config.HBASE_HOST,
            port=config.HBASE_PORT,
            timeout=10000,
        )
        _ensure_table(connection)
        table = connection.table(config.MODEL_RESULTS_TABLE)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        batch = table.batch()

        for name, result in all_results.items():
            row_key = name.replace(" ", "_").encode()
            metrics  = result["metrics"]

            ranked = extract_feature_importance(result["model"], feature_cols)
            imp_json = importance_to_json(ranked)

            batch.put(row_key, {
                b"metrics:auc":           str(round(metrics.get("auc", 0.0), 4)).encode(),
                b"metrics:accuracy":      str(round(metrics.get("accuracy", 0.0), 4)).encode(),
                b"metrics:cv_auc":        str(round(metrics.get("cv_auc", 0.0), 4)).encode(),
                b"metrics:training_time": str(metrics.get("training_time", 0.0)).encode(),
                b"info:timestamp":        ts.encode(),
                b"info:is_best":          ("true" if name == best_name else "false").encode(),
                b"importance:json":       imp_json.encode(),
            })

        batch.send()
        print(f">>> [MODEL RESULTS] Wrote {len(all_results)} model records.")

    except Exception as e:
        print(f">>> [MODEL RESULTS] Write error: {e}")
        raise e
    finally:
        if connection:
            connection.close()