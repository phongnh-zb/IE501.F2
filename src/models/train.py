from pyspark.ml.classification import (GBTClassifier, LinearSVC,
                                       LogisticRegression,
                                       RandomForestClassifier)
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.sql.functions import col, count, when

try:
    import numpy as np
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print(">>> [TRAIN] xgboost not installed — XGBoost will be skipped.")

if XGBOOST_AVAILABLE:
    class XGBoostModelWrapper:
        def __init__(self, booster, feature_importances):
            self._booster            = booster
            self.featureImportances  = feature_importances  # matches tree model API

        def transform(self, spark_df):
            from pyspark.ml.linalg import Vectors, VectorUDT
            from pyspark.sql.types import DoubleType, StructField, StructType

            pdf   = spark_df.toPandas()
            X     = np.array([v.toArray() for v in pdf["features"]])
            proba = self._booster.predict_proba(X)[:, 1]
            preds = (proba >= 0.5).astype(float)

            # rawPrediction must be a 2-element Vector for BinaryClassificationEvaluator.
            # Explicit schema avoids Spark misidentifying types from Pandas inference.
            rows = [
                (
                    float(pdf["label"].iloc[i]),
                    float(preds[i]),
                    Vectors.dense([1.0 - float(proba[i]), float(proba[i])]),
                )
                for i in range(len(preds))
            ]

            schema = StructType([
                StructField("label",         DoubleType(), False),
                StructField("prediction",    DoubleType(), False),
                StructField("rawPrediction", VectorUDT(), False),
            ])

            return spark_df.sparkSession.createDataFrame(rows, schema=schema)

        def extractParamMap(self):
            return {}

    class XGBoostClassifierWrapper:
        def __init__(self, n_estimators=100, max_depth=6, **kwargs):
            self._params = {"n_estimators": n_estimators, "max_depth": max_depth, **kwargs}

        def fit(self, spark_df):
            pdf  = spark_df.toPandas()
            X    = np.array([v.toArray() for v in pdf["features"]])
            y    = pdf["label"].values
            w    = pdf["weight"].values if "weight" in pdf.columns else None

            clf = XGBClassifier(
                **self._params,
                use_label_encoder=False,
                eval_metric="logloss",
                verbosity=0,
            )
            clf.fit(X, y, sample_weight=w)

            # Build a DenseVector-like object for featureImportances
            scores     = clf.feature_importances_
            importances = type("FakeVector", (), {"toArray": lambda self: scores})()

            return XGBoostModelWrapper(clf, importances)

        def extractParamMap(self):
            return {}

        def copy(self, extra=None):
            params = dict(self._params)
            if extra:
                params.update({p.name if hasattr(p, "name") else p: v for p, v in extra.items()})
            return XGBoostClassifierWrapper(**params)


FEATURE_COLS = [
    # VLE engagement (8)
    "total_clicks",
    "active_days",
    "clicks_per_day",
    "forum_clicks",
    "quiz_clicks",
    "resource_clicks",
    "active_weeks",
    "engagement_ratio",
    # Academic performance (7)
    "avg_score",
    "weighted_avg_score",
    "submission_rate",
    "avg_days_early",
    "exam_score",
    "tma_score",
    "cma_score",
    # Registration behavior (2)
    "withdrew_early",
    "days_before_start",
    # Demographics (3)
    "num_prev_attempts",
    "imd_band_encoded",
    "disability_encoded",
]


def add_class_weights(df, label_col="label"):
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
    cnt_map = {r[label_col]: r["cnt"] for r in class_counts}
    for label, w in sorted(weight_map.items()):
        print(f"    label={label}  count={cnt_map[label]:,}  weight={w:.4f}")

    items = list(weight_map.items())
    expr = when(col(label_col) == items[0][0], items[0][1])
    for label_val, w in items[1:]:
        expr = expr.when(col(label_col) == label_val, w)
    return df.withColumn("weight", expr.otherwise(1.0))


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
        # LinearSVC does not support weightCol or produce calibrated probabilities.
        # AUC is computed from raw decision scores, not probabilities — treat
        # its AUC as approximate. Trained unweighted.
        "Linear SVC": LinearSVC(
            labelCol="label", featuresCol="features", maxIter=100,
        ),
    }
    if XGBOOST_AVAILABLE:
        classifiers["XGBoost"] = XGBoostClassifierWrapper(n_estimators=100, max_depth=6)
    return classifiers


def tune_classifiers(classifiers, train_data, num_folds=3):
    evaluator = BinaryClassificationEvaluator(labelCol="label")

    grids = {
        "Random Forest": ParamGridBuilder()
            .addGrid(classifiers["Random Forest"].numTrees,  [20, 50, 100])
            .addGrid(classifiers["Random Forest"].maxDepth,  [5, 10])
            .build(),
        "Gradient Boosted Trees": ParamGridBuilder()
            .addGrid(classifiers["Gradient Boosted Trees"].maxIter,  [20, 50])
            .addGrid(classifiers["Gradient Boosted Trees"].maxDepth, [3, 5])
            .build(),
    }

    tuned          = dict(classifiers)
    tuning_results = {}   # {model_name: {combos: [...], best_params: {...}, best_auc: float}}

    for name, param_grid in grids.items():
        if name not in classifiers:
            continue
        estimator = classifiers[name]
        print(f"\n>>> [TUNE] Grid search for {name} ({num_folds}-fold, {len(param_grid)} param combos)...")
        cv = CrossValidator(
            estimator=estimator,
            estimatorParamMaps=param_grid,
            evaluator=evaluator,
            numFolds=num_folds,
            seed=42,
            parallelism=2,
        )
        try:
            cv_model    = cv.fit(train_data)
            best_idx    = cv_model.avgMetrics.index(max(cv_model.avgMetrics))
            best_params = param_grid[best_idx]
            best_auc    = cv_model.avgMetrics[best_idx]

            print(f"    Best CV AUC: {best_auc:.4f}")
            for p, v in best_params.items():
                print(f"    {p.name}: {v}")

            # Build structured result for storage
            combos = [
                {
                    "params": {p.name: v for p, v in combo.items()},
                    "cv_auc": round(auc, 4),
                    "is_best": (i == best_idx),
                }
                for i, (combo, auc) in enumerate(zip(param_grid, cv_model.avgMetrics))
            ]
            tuning_results[name] = {
                "combos":      combos,
                "best_params": {p.name: v for p, v in best_params.items()},
                "best_auc":    round(best_auc, 4),
                "num_folds":   num_folds,
            }
            tuned[name] = estimator.copy(best_params)
        except Exception as e:
            print(f"    Grid search failed ({name}): {e} — using default.")

    return tuned, tuning_results


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