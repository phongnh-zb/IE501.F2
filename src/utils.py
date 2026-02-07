from pyspark.sql import SparkSession


def get_spark_session(app_name, master="local[*]"):
    spark = SparkSession.builder \
        .appName(app_name) \
        .master(master) \
        .getOrCreate()
    
    # Reduce log verbosity (Suppress INFO logs)
    spark.sparkContext.setLogLevel("ERROR")
    return spark