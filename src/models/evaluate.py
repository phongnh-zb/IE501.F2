import time

from pyspark.ml.evaluation import (BinaryClassificationEvaluator,
                                   MulticlassClassificationEvaluator)
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

from src.models.train import train_model

# CV is O(n_folds × train_time). For sequentially-boosted models use a
# lightweight CV estimator (fewer iterations) to complete in reasonable time.
# XGBoostClassifierWrapper uses native sklearn CV internally — excluded here.
CV_LITE_PARAMS = {
    "GBTClassifier": {"maxIter": 5},
}


def _cv_estimator(classifier):
    name = type(classifier).__name__
    # Non-Spark-ML wrappers (e.g. XGBoostClassifierWrapper) don't implement
    # fitMultiple — CrossValidator will fail. Return None to signal skip.
    if not hasattr(classifier, 'uid'):
        return None
    if name not in CV_LITE_PARAMS:
        return classifier
    lite_kwargs = CV_LITE_PARAMS[name]
    params      = classifier.extractParamMap()
    init_kwargs = {p.name: v for p, v in params.items() if p.name not in lite_kwargs}
    init_kwargs.update(lite_kwargs)
    try:
        return type(classifier)(**init_kwargs)
    except Exception:
        return classifier


def evaluate_model(model, test_data, label_col="label"):
    predictions = model.transform(test_data)

    # LinearSVC rawPrediction is a decision score, not a probability — AUC is
    # approximate. Guard with try/except for version differences.
    try:
        auc = BinaryClassificationEvaluator(labelCol=label_col).evaluate(predictions)
    except Exception as e:
        print(f">>> [EVAL] AUC skipped ({type(model).__name__}): {e}")
        auc = 0.0

    def _mc(metric):
        return MulticlassClassificationEvaluator(
            labelCol=label_col, predictionCol="prediction", metricName=metric,
        ).evaluate(predictions)

    return {
        "auc":         auc,
        "accuracy":    _mc("accuracy"),
        "precision":   _mc("weightedPrecision"),
        "recall":      _mc("weightedRecall"),
        "f1":          _mc("weightedFMeasure"),
        "predictions": predictions,
    }


def cross_validate(classifier, train_data, label_col="label", num_folds=3):
    evaluator  = BinaryClassificationEvaluator(labelCol=label_col)
    param_grid = ParamGridBuilder().build()
    cv = CrossValidator(
        estimator=classifier,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        numFolds=num_folds,
        seed=42,
        parallelism=2,
    )
    print(f">>> [EVAL] Running {num_folds}-fold CV...")
    try:
        cv_model = cv.fit(train_data)
        avg_auc  = cv_model.avgMetrics[0]
        print(f">>> [EVAL] CV AUC: {avg_auc:.4f}")
        return avg_auc
    except Exception as e:
        print(f">>> [EVAL] CV failed ({type(classifier).__name__}): {e}")
        return 0.0


def _composite_score(metrics, weights):
    return sum(metrics.get(k, 0.0) * w for k, w in weights.items())


def run_evaluation(classifiers, train_data, test_data, num_cv_folds=3):
    from configs.config import MODEL_SELECTION_WEIGHTS

    results       = {}
    best_name     = ""
    best_score    = -1.0
    best_model    = None

    print("=" * 60)
    print("STARTING MODEL TRAINING & EVALUATION")
    print(f"Selection criterion: weighted composite {MODEL_SELECTION_WEIGHTS}")
    print("=" * 60)

    for name, classifier in classifiers.items():
        print(f"\n>>> [{name}]")

        # Training — uses train_model() from train.py (separation of concerns)
        t0         = time.time()
        model      = train_model(name, classifier, train_data)
        train_time = time.time() - t0

        # Evaluation on held-out test set
        metrics = evaluate_model(model, test_data)

        # Cross-validation AUC — boosted models use lite estimator;
        # non-Spark-ML wrappers return None and skip CV entirely.
        cv_est = _cv_estimator(classifier)
        if cv_est is None:
            cv_auc = 0.0
            print(f">>> [EVAL] CV skipped for {name} (non-Spark-ML estimator)")
        else:
            if cv_est is not classifier:
                lite = CV_LITE_PARAMS[type(classifier).__name__]
                print(f">>> [EVAL] CV for {name} uses lite params {lite}")
            cv_auc = cross_validate(cv_est, train_data, num_folds=num_cv_folds)

        metrics["cv_auc"]        = cv_auc
        metrics["training_time"] = round(train_time, 2)

        score = _composite_score(metrics, MODEL_SELECTION_WEIGHTS)
        metrics["composite_score"] = round(score, 4)

        print(f"    AUC:             {metrics['auc']:.4f}")
        print(f"    CV AUC:          {metrics['cv_auc']:.4f}")
        print(f"    Accuracy:        {metrics['accuracy']:.4f}")
        print(f"    Precision:       {metrics['precision']:.4f}")
        print(f"    Recall:          {metrics['recall']:.4f}")
        print(f"    F1:              {metrics['f1']:.4f}")
        print(f"    Train:           {train_time:.2f}s")
        print(f"    Composite score: {score:.4f}")

        results[name] = {"model": model, "metrics": metrics}

        if score > best_score:
            best_score = score
            best_name  = name
            best_model = model

    print("\n" + "=" * 60)
    print(f"BEST MODEL: {best_name}  (composite: {best_score:.4f})")
    print(f"WEIGHTS: {MODEL_SELECTION_WEIGHTS}")
    print("=" * 60)

    return {
        "all_results": results,
        "best_name":   best_name,
        "best_model":  best_model,
        "best_auc":    results[best_name]["metrics"]["auc"],
    }