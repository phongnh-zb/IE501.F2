def extract_raw_data(spark, config):
    base = config.HDFS_BASE_PATH

    print(f">>> [ETL:EXTRACT] Reading raw CSVs from: {base}")

    def read_csv(filename):
        return spark.read.csv(f"{base}{filename}", header=True, inferSchema=True)

    df_info         = read_csv(config.FILE_STUDENT_INFO)
    df_vle          = read_csv(config.FILE_STUDENT_VLE)
    df_student_assess = read_csv(config.FILE_STUDENT_ASSESSMENT)
    df_reg          = read_csv(config.FILE_STUDENT_REGISTRATION)
    df_assessments  = read_csv(config.FILE_ASSESSMENTS)
    df_vle_info     = read_csv(config.FILE_VLE)

    print(
        f">>> [ETL:EXTRACT] Loaded — "
        f"studentInfo: {df_info.count()} rows, "
        f"studentVle: {df_vle.count()} rows, "
        f"studentAssessment: {df_student_assess.count()} rows, "
        f"studentRegistration: {df_reg.count()} rows, "
        f"assessments: {df_assessments.count()} rows, "
        f"vle: {df_vle_info.count()} rows"
    )

    return {
        "student_info":         df_info,
        "student_vle":          df_vle,
        "student_assessment":   df_student_assess,
        "student_registration": df_reg,
        "assessments":          df_assessments,
        "vle":                  df_vle_info,
    }