from pyspark.ml.classification import (GBTClassifier, LogisticRegression,
                                       RandomForestClassifier)
from pyspark.ml.feature import VectorAssembler

FEATURE_COLS = [
    # VLE engagement (6)
    "total_clicks",
    "active_days",
    "clicks_per_day",
    "forum_clicks",
    "quiz_clicks",
    "resource_clicks",
    # Academic performance (4)
    "avg_score",
    "weighted_avg_score",
    "submission_rate",
    "avg_days_early",
    # Registration behavior (2)
    "withdrew_early",
    "days_before_start",
    # Demographics (3)
    "num_prev_attempts",
    "imd_band_encoded",
    "disability_encoded",
]


def get_classifiers():
    return {
        "Logistic Regression": LogisticRegression(
            labelCol="label", featuresCol="features"
        ),
        "Random Forest": RandomForestClassifier(
            labelCol="label", featuresCol="features", numTrees=20
        ),
        "Gradient Boosted Trees": GBTClassifier(
            labelCol="label", featuresCol="features", maxIter=20, maxDepth=5
        ),
    }


def prepare_features(df, feature_cols=None, label_col="label", test_ratio=0.2, seed=42):
    cols = feature_cols or FEATURE_COLS

    assembler = VectorAssembler(inputCols=cols, outputCol="features")
    data_vectorized = assembler.transform(df)

    train_data, test_data = data_vectorized.randomSplit(
        [1.0 - test_ratio, test_ratio], seed=seed
    )

    print(f">>> [TRAIN] Features ({len(cols)}): {cols}")
    print(f">>> [TRAIN] Train: {train_data.count()} rows, Test: {test_data.count()} rows")

    return train_data, test_data


def train_model(name, classifier, train_data):
    print(f"\n>>> Training {name}...")
    return classifier.fit(train_data)