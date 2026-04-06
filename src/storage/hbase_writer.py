import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from configs import config
from common.hbase_client import ensure_table, hbase_connection
from src.utils import get_spark_session

RISK_SAFE     = 0
RISK_WATCH    = 1
RISK_HIGH     = 2
RISK_CRITICAL = 3


def _apply_risk_tier(
    score: float,
    clicks: float,
    submission_rate: float,
    avg_days_early: float,
    withdrew_early: int,
    label: int,
) -> int:
    if withdrew_early == 1:
        return RISK_CRITICAL

    if label == 1:
        if score < 40.0 or submission_rate < 0.25 or clicks < 10:
            return RISK_CRITICAL
        return RISK_HIGH

    if score < 60.0 or submission_rate < 0.6 or avg_days_early < -7:
        return RISK_WATCH

    return RISK_SAFE


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

        risk_tier = _apply_risk_tier(
            score, clicks, sub_rate, avg_days_early, withdrew_early, int(row["label"])
        )

        batch.put(
            str(row["id_student"]).encode(),
            {
                b"info:code_module":        str(row["code_module"]).encode(),
                b"info:code_presentation":  str(row["code_presentation"]).encode(),
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
                b"prediction:risk_tier":    str(risk_tier).encode(),
            },
        )
    batch.send()

    duration = time.time() - start_time
    print(f">>> [HBASE] Done in {duration:.2f}s.")


def main():
    spark = get_spark_session("Save_To_HBase_Full", config.MASTER)
    spark.sparkContext.setLogLevel("ERROR")

    print(f">>> [HBASE] Reading processed data from: {config.HDFS_OUTPUT_PATH}")
    try:
        df = spark.read.parquet(config.HDFS_OUTPUT_PATH)
        print(f">>> [INFO] {df.count()} rows found.")
        all_rows = df.select(
            "id_student",
            "code_module", "code_presentation",
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
    with hbase_connection() as conn:
        ensure_table(conn, config.TABLE_NAME, ["info", "prediction"])
        write_predictions(all_rows, conn)