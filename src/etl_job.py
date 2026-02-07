import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pyspark.sql.functions import avg as _avg
from pyspark.sql.functions import col
from pyspark.sql.functions import sum as _sum
from pyspark.sql.functions import when

from configs import config
from src.utils import get_spark_session


def main():
    spark = get_spark_session(config.APP_NAME, config.MASTER)
    spark.sparkContext.setLogLevel("ERROR")
    
    # Read data from HDFS
    print(f">>> [ETL] Reading RAW data from: {config.HDFS_BASE_PATH}")
    
    try:
        df_info = spark.read.csv(config.HDFS_BASE_PATH + config.FILE_STUDENT_INFO, header=True, inferSchema=True)
        df_vle = spark.read.csv(config.HDFS_BASE_PATH + config.FILE_STUDENT_VLE, header=True, inferSchema=True)
        df_assess = spark.read.csv(config.HDFS_BASE_PATH + config.FILE_STUDENT_ASSESSMENT, header=True, inferSchema=True)
    except Exception as e:
        print(f">>> ERROR: Files not found on HDFS. Have you run ./scripts/setup_hdfs.sh?")
        raise e

    # Process Data (Logic remains unchanged)
    print(">>> [ETL] Processing data...")
    
    df_clicks = df_vle.groupBy("id_student").agg(_sum("sum_click").alias("total_clicks"))
    df_scores = df_assess.groupBy("id_student").agg(_avg("score").alias("avg_score"))
    
    # Labeling: Pass/Distinction = 0 (Safe), Others = 1 (Risk)
    df_labeled = df_info.withColumn("label", 
        when(col("final_result").isin("Pass", "Distinction"), 0)
        .otherwise(1)
    )

    df_final = df_labeled.join(df_clicks, "id_student", "left") \
                         .join(df_scores, "id_student", "left") \
                         .fillna(0, subset=["total_clicks", "avg_score"])

    # Save to HDFS (Overwrite)
    print(f">>> [ETL] Saving PROCESSED data to: {config.HDFS_OUTPUT_PATH}")
    df_final.write.mode("overwrite").parquet(config.HDFS_OUTPUT_PATH)
    print(">>> [ETL] Finished Successfully!")

    spark.stop()

if __name__ == "__main__":
    main()