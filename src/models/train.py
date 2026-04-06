from pyspark.ml.classification import (GBTClassifier, LinearSVC,
                                       LogisticRegression,
                                       RandomForestClassifier)
from pyspark.ml.feature import VectorAssembler
from pyspark.sql.functions import col, count

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


def add_class_weights(df, label_col="label"):
    """
    Add a 'weight' column using balanced class weighting:
        w_class = total / (n_classes * count_class)
    Minority class gets w > 1, majority gets w < 1.
    LinearSVC does not support weightCol — those rows still carry the column
    but it is simply ignored when passed to that classifier.
    """
    total = df.count()
    n_classes = 2

    class_counts = (
        df.groupBy(label_col)
        .agg(count("*").alias("cnt"))
        .collect()
    )
    weight_map = {
        row[label_col]: total / (n_classes * row["cnt"])
        for row in class_counts
    }

    print(">>> [TRAIN] Class weights:")
    for label, w in sorted(weight_map.items()):
        print(f"    label={label}  count={dict((r[label_col], r['cnt']) for r in class_counts)[label]:,}  weight={w:.4f}")

    from pyspark.sql.functions import when
    items = list(weight_map.items())
    expr = when(col(label_col) == items[0][0], items[0][1])
    for label_val, w in items[1:]:
        expr = expr.when(col(label_col) == label_val, w)
    expr = expr.otherwise(1.0)

    return df.withColumn("weight", expr)


def get_classifiers():
    classifiers = {
        "Logistic Regression": LogisticRegression(
            labelCol="label", featuresCol="features",
            weightCol="weight", maxIter=100,
        ),
        "Random Forest": RandomForestClassifier(
            labelCol="label", featuresCol="features",
            weightCol="weight", numTrees=20, seed=42,
        ),
        "Gradient Boosted Trees": GBTClassifier(
            labelCol="label", featuresCol="features",
            weightCol="weight", maxIter=20, maxDepth=5, seed=42,
        ),
        # LinearSVC does not support weightCol — trained unweighted
        "Linear SVC": LinearSVC(
            labelCol="label", featuresCol="features", maxIter=100,
        ),
    }

    if XGBOOST_AVAILABLE:
        classifiers["XGBoost"] = SparkXGBClassifier(
            label_col="label",
            features_col="features",
            weight_col="weight",
            n_estimators=100,
            max_depth=6,
            use_gpu=False,
        )

    return classifiers


def prepare_features(df, feature_cols=None, label_col="label", test_ratio=0.2, seed=42):
    cols = feature_cols or FEATURE_COLS

    df_weighted = add_class_weights(df, label_col=label_col)

    assembler = VectorAssembler(inputCols=cols, outputCol="features")
    data_vectorized = assembler.transform(df_weighted)

    train_data, test_data = data_vectorized.randomSplit(
        [1.0 - test_ratio, test_ratio], seed=seed
    )

    print(f">>> [TRAIN] Features ({len(cols)}): {cols}")
    print(f">>> [TRAIN] Train: {train_data.count()} rows, Test: {test_data.count()} rows")

    return train_data, test_data


def train_model(name, classifier, train_data):
    print(f"\n>>> Training {name}...")
    return classifier.fit(train_data)