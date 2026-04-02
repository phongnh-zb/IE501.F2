import os
import sys
import time

import happybase

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from configs import config
from src.utils import get_spark_session


def _apply_business_rules(score: float, clicks: float, risk_label: int) -> int:
    if score >= 90.0:
        return 0
    if score < 40.0 or clicks < 10:
        return 1
    return risk_label


def write_predictions(rows, connection):
    table = connection.table(config.TABLE_NAME)

    print(f">>> [HBASE] Writing {len(rows)} rows...")
    start_time = time.time()

    batch = table.batch(batch_size=1000)
    for row in rows:
        clicks     = float(row["total_clicks"])
        score      = float(row["avg_score"])
        risk_label = _apply_business_rules(score, clicks, int(row["label"]))

        batch.put(
            str(row["id_student"]).encode(),
            {
                b"info:clicks":              str(clicks).encode(),
                b"info:avg_score":           str(score).encode(),
                b"prediction:risk_label":    str(risk_label).encode(),
            },
        )
    batch.send()

    duration = time.time() - start_time
    print(f">>> [HBASE] ✅ Done in {duration:.2f}s.")


def _ensure_table(connection):
    if b"student_predictions" not in connection.tables():
        print(">>> [HBASE] Table not found — creating 'student_predictions'...")
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
        total_count = df.count()
        print(f">>> [INFO] {total_count} rows found.")
        all_rows = df.select("id_student", "total_clicks", "avg_score", "label").collect()
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