import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from configs import config
from etl.extract import extract_raw_data
from etl.load import load_to_hdfs
from etl.transform import transform_data
from utils import get_spark_session


def main():
    spark = get_spark_session(config.APP_NAME, config.MASTER)
    spark.sparkContext.setLogLevel("ERROR")

    raw = extract_raw_data(spark, config)

    df_final = transform_data(
        df_info=raw["student_info"],
        df_vle=raw["student_vle"],
        df_student_assess=raw["student_assessment"],
        df_assessments=raw["assessments"],
        df_reg=raw["student_registration"],
        df_vle_info=raw["vle"],
    )

    load_to_hdfs(df_final, config.HDFS_OUTPUT_PATH)

    spark.stop()


if __name__ == "__main__":
    main()