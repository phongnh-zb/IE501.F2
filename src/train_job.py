import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from configs import config
from src.models.evaluate import run_evaluation
from src.models.registry import save_model
from src.models.train import FEATURE_COLS, get_classifiers, prepare_features
from src.storage.model_results_writer import write_model_results
from src.utils import get_spark_session


def main():
    spark = get_spark_session("OULAD_Training", config.MASTER)
    spark.sparkContext.setLogLevel("ERROR")

    print(f">>> [TRAIN] Reading processed data from: {config.HDFS_OUTPUT_PATH}")
    try:
        df = spark.read.parquet(config.HDFS_OUTPUT_PATH)
    except Exception as e:
        print(">>> ERROR: Processed data not found. Ensure ETL step ran successfully.")
        raise e

    train_data, test_data = prepare_features(df, feature_cols=FEATURE_COLS)
    classifiers = get_classifiers()
    results = run_evaluation(classifiers, train_data, test_data)

    save_model(results["best_model"], results["best_name"])

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    write_model_results(results["all_results"], results["best_name"], FEATURE_COLS, run_id)
    print(f">>> [TRAIN] Run ID: {run_id}")

    spark.stop()


if __name__ == "__main__":
    main()