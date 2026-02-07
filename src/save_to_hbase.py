import os
import sys
import time

import happybase

# Setup import path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from configs import config
from src.utils import get_spark_session


def main():
    # Initialize Spark
    spark = get_spark_session("Save_To_HBase_Full", config.MASTER)
    spark.sparkContext.setLogLevel("ERROR")

    print(f">>> [HBASE] Reading processed data from HDFS: {config.HDFS_OUTPUT_PATH}")
    
    try:
        # Read Parquet data from HDFS
        df = spark.read.parquet(config.HDFS_OUTPUT_PATH)
        
        # --- IMPORTANT: Count total rows for tracking ---
        total_count = df.count()
        print(f">>> [INFO] Found total {total_count} rows of data.")
        
        # Collect all data to Driver 
        all_rows = df.select("id_student", "total_clicks", "avg_score", "label").collect()
    except Exception as e:
        print(f">>> ERROR: Data not found or HDFS read error: {e}")
        sys.exit(1)

    print(">>> [HBASE] Connecting to HBase via Thrift...")
    connection = None
    
    try:
        connection = happybase.Connection('localhost', port=9090, timeout=10000)
        table = connection.table('student_predictions')
        
        print(f">>> [HBASE] Starting to write {total_count} rows to table 'student_predictions'...")
        
        batch = table.batch(batch_size=1000)
        start_time = time.time()
        
        for i, row in enumerate(all_rows):
            row_key = str(row['id_student']).encode()
            
            # Get original values from Spark
            clicks = float(row['total_clicks'])
            score = float(row['avg_score'])
            risk_label = int(row['label']) # Model prediction
            
            # --- BUSINESS RULES (OVERRIDES) ---
            
            # Rule 1: High Achievers are always Safe
            if score >= 90.0:
                risk_label = 0 
                
            # Rule 2: Low Activity/Score is always High Risk (Fix for 0/0 case)
            elif score < 40.0 or clicks < 10:
                risk_label = 1
                
            # ----------------------------------

            batch.put(row_key, {
                b'info:clicks': str(clicks).encode(),
                b'info:avg_score': str(score).encode(),
                b'prediction:risk_label': str(risk_label).encode()
            })

        batch.send()
        
        duration = time.time() - start_time
        print(f">>> [HBASE] ✅ COMPLETED! Wrote {total_count} rows in {duration:.2f} seconds.")
    except Exception as e:
        print(f">>> [HBASE] CONNECTION/WRITE ERROR: {e}")
    finally:
        if connection:
            connection.close()

    spark.stop()

if __name__ == "__main__":
    main()