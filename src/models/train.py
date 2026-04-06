from pyspark.ml.classification import (GBTClassifier, LinearSVC,
                                       LogisticRegression,
                                       RandomForestClassifier)
from pyspark.ml.feature import VectorAssembler

try:
    from xgboost.spark import SparkXGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print(">>> [TRAIN] xgboost not installed — XGBoost will be skipped. Run: pip install xgboost>=2.0.0")

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
    classifiers = {
        "Logistic Regression": LogisticRegression(
            labelCol="label", featuresCol="features", maxIter=100,
        ),
        "Random Forest": RandomForestClassifier(
            labelCol="label", featuresCol="features", numTrees=20, seed=42,
        ),
        "Gradient Boosted Trees": GBTClassifier(
            labelCol="label", featuresCol="features", maxIter=20, maxDepth=5, seed=42,
        ),
        "Linear SVC": LinearSVC(
            labelCol="label", featuresCol="features", maxIter=100,
        ),
    }

    if XGBOOST_AVAILABLE:
        classifiers["XGBoost"] = SparkXGBClassifier(
            label_col="label",
            features_col="features",
            n_estimators=100,
            max_depth=6,
            use_gpu=False,
        )

    return classifiers


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