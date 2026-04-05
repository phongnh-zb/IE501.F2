import os
import sys
import time

import happybase

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from configs import config
from src.utils import get_spark_session


def _apply_business_rules(
    score: float,
    clicks: int,
    withdrew_early: int,
    submission_rate: float,
    risk_label: int,
) -> int:
    if withdrew_early == 1:
        return 1
    if score >= 90.0 and submission_rate >= 0.8:
        return 0
    if score < 40.0 or clicks < 10 or submission_rate < 0.3:
        return 1
    return risk_label


def write_predictions(rows, connection):
    table = connection.table(config.TABLE_NAME)

    print(f">>> [HBASE] Writing {len(rows)} rows...")
    start_time = time.time()

    batch = table.batch(batch_size=1000)
    for row in rows:
        clicks          = float(row["total_clicks"])
        active_days     = int(row["active_days"])
        forum_clicks    = float(row["forum_clicks"])
        quiz_clicks     = float(row["quiz_clicks"])
        resource_clicks = float(row["resource_clicks"])
        score           = float(row["avg_score"])
        w_score         = float(row["weighted_avg_score"])
        sub_rate        = float(row["submission_rate"])
        avg_days_early  = float(row["avg_days_early"])
        withdrew_early  = int(row["withdrew_early"])
        prev_attempts   = int(row["num_prev_attempts"])

        risk_label = _apply_business_rules(
            score, clicks, withdrew_early, sub_rate, int(row["label"])
        )

        batch.put(
            str(row["id_student"]).encode(),
            {
                b"info:total_clicks":       str(clicks).encode(),
                b"info:active_days":        str(active_days).encode(),
                b"info:forum_clicks":       str(forum_clicks).encode(),
                b"info:quiz_clicks":        str(quiz_clicks).encode(),
                b"info:resource_clicks":    str(resource_clicks).encode(),
                b"info:avg_score":          str(score).encode(),
                b"info:weighted_avg_score": str(w_score).encode(),
                b"info:submission_rate":    str(sub_rate).encode(),
                b"info:avg_days_early":     str(avg_days_early).encode(),
                b"info:withdrew_early":     str(withdrew_early).encode(),
                b"info:num_prev_attempts":  str(prev_attempts).encode(),
                b"prediction:risk_label":   str(risk_label).encode(),
            },
        )
    batch.send()

    duration = time.time() - start_time
    print(f">>> [HBASE] Done in {duration:.2f}s.")


def _ensure_table(connection):
    if config.TABLE_NAME.encode() not in connection.tables():
        print(f">>> [HBASE] Table not found — creating '{config.TABLE_NAME}'...")
        connection.create_table(
            config.TABLE_NAME,
            {"info": dict(), "prediction": dict()},
        )
        print(">>> [HBASE] Table created.")


def main():
    spark = get_spark_session("Save_To_HBase_Full", config.MASTER)
    spark.sparkContext.setLogLevel("ERROR")

    print(f">>> [HBASE] Reading processed data from: {config.HDFS_OUTPUT_PATH}")
    try:
        df = spark.read.parquet(config.HDFS_OUTPUT_PATH)
        print(f">>> [INFO] {df.count()} rows found.")
        all_rows = df.select(
            "id_student",
            "total_clicks", "active_days",
            "forum_clicks", "quiz_clicks", "resource_clicks",
            "avg_score", "weighted_avg_score", "submission_rate", "avg_days_early",
            "withdrew_early", "num_prev_attempts",
            "label",
        ).collect()
    except Exception as e:
        print(f">>> ERROR: Cannot read HDFS data — {e}")
        raise e
    finally:
        spark.stop()

    print(">>> [HBASE] Connecting via Thrift...")
    connection = None
    try:
        connection = happybase.Connection(
            host=config.HBASE_HOST,
            port=config.HBASE_PORT,
            timeout=10000,
        )
        _ensure_table(connection)
        write_predictions(all_rows, connection)
    except Exception as e:
        print(f">>> [HBASE] Connection/write error: {e}")
        raise e
    finally:
        if connection:
            connection.close()