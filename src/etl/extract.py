def extract_raw_data(spark, config):
    base = config.HDFS_BASE_PATH

    print(f">>> [ETL:EXTRACT] Reading raw CSVs from: {base}")

    df_info = spark.read.csv(
        f"{base}{config.FILE_STUDENT_INFO}",
        header=True,
        inferSchema=True,
    )
    df_vle = spark.read.csv(
        f"{base}{config.FILE_STUDENT_VLE}",
        header=True,
        inferSchema=True,
    )
    df_assess = spark.read.csv(
        f"{base}{config.FILE_STUDENT_ASSESSMENT}",
        header=True,
        inferSchema=True,
    )

    print(
        f">>> [ETL:EXTRACT] Loaded — "
        f"studentInfo: {df_info.count()} rows, "
        f"studentVle: {df_vle.count()} rows, "
        f"studentAssessment: {df_assess.count()} rows"
    )

    return {
        "student_info": df_info,
        "student_vle": df_vle,
        "student_assessment": df_assess,
    }