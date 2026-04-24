import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from configs import config
from src.models.evaluate import run_evaluation
from src.models.registry import save_model
from src.models.train import (FEATURE_COLS, get_classifiers, prepare_features,
                              tune_classifiers)
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

    # 1 — Feature engineering and train/test split
    train_data, test_data = prepare_features(df, feature_cols=FEATURE_COLS)

    # 2 — Baseline classifiers
    classifiers = get_classifiers()

    # 3 — Hyperparameter tuning for tree-based models via grid search
    print("\n>>> [TRAIN] Running hyperparameter tuning...")
    classifiers, tuning_results = tune_classifiers(classifiers, train_data, num_folds=2)

    # 4 — Full training + evaluation on all classifiers
    results = run_evaluation(classifiers, train_data, test_data)

    # 5 — Persist best model to HDFS
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_model(results["best_model"], results["best_name"], run_id=run_id)

    # 6 — Write all metrics to HBase
    write_model_results(results["all_results"], results["best_name"], FEATURE_COLS, run_id,
                        tuning_results=tuning_results)
    print(f">>> [TRAIN] Run ID: {run_id}")

    spark.stop()


if __name__ == "__main__":
    main()