import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from configs import config
from src.etl.extract import extract_raw_data
from src.etl.load import load_to_hdfs
from src.etl.transform import transform_data
from src.utils import get_spark_session


def main():
    spark = get_spark_session(config.APP_NAME, config.MASTER)
    spark.sparkContext.setLogLevel("ERROR")

    # Extract
    raw_frames = extract_raw_data(spark, config)

    # Transform
    df_final = transform_data(
        df_info=raw_frames["student_info"],
        df_vle=raw_frames["student_vle"],
        df_assess=raw_frames["student_assessment"],
    )

    # Load
    load_to_hdfs(df_final, config.HDFS_OUTPUT_PATH)

    spark.stop()


if __name__ == "__main__":
    main()