import time

from pyspark.ml.evaluation import (BinaryClassificationEvaluator,
                                   MulticlassClassificationEvaluator)
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

# CV is O(n_folds × train_time).
# For sequentially-boosted models, use a lightweight CV estimator (fewer iterations)
# rather than the full model, so CV completes in reasonable time while still
# producing a meaningful AUC signal.
CV_LITE_PARAMS = {
    "GBTClassifier":      {"maxIter": 5},
    "SparkXGBClassifier": {"n_estimators": 20},
}


def _cv_estimator(classifier):
    name = type(classifier).__name__
    if name not in CV_LITE_PARAMS:
        return classifier
    # Return a fresh instance of the same class with reduced iterations
    lite_kwargs = CV_LITE_PARAMS[name]
    params = classifier.extractParamMap()
    init_kwargs = {p.name: v for p, v in params.items() if p.name not in lite_kwargs}
    init_kwargs.update(lite_kwargs)
    try:
        return type(classifier)(**init_kwargs)
    except Exception:
        # If param extraction fails, fall back to original to avoid crashing
        return classifier


def evaluate_model(model, test_data, label_col="label"):
    predictions = model.transform(test_data)

    # AUC — guarded: LinearSVC rawPrediction format varies across Spark versions
    try:
        auc_evaluator = BinaryClassificationEvaluator(labelCol=label_col)
        auc = auc_evaluator.evaluate(predictions)
    except Exception as e:
        print(f">>> [EVAL] AUC skipped ({type(model).__name__}): {e}")
        auc = 0.0

    acc_evaluator = MulticlassClassificationEvaluator(
        labelCol=label_col, predictionCol="prediction", metricName="accuracy"
    )
    accuracy = acc_evaluator.evaluate(predictions)

    return {"auc": auc, "accuracy": accuracy, "predictions": predictions}


def cross_validate(classifier, train_data, label_col="label", num_folds=3):
    evaluator = BinaryClassificationEvaluator(labelCol=label_col)
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
        avg_auc = cv_model.avgMetrics[0]
        print(f">>> [EVAL] CV AUC: {avg_auc:.4f}")
        return avg_auc
    except Exception as e:
        print(f">>> [EVAL] CV failed ({type(classifier).__name__}): {e}")
        return 0.0


def run_evaluation(classifiers, train_data, test_data, num_cv_folds=3):
    results = {}
    best_name = ""
    best_auc  = 0.0
    best_model = None

    print("=" * 60)
    print("STARTING MODEL TRAINING & EVALUATION")
    print("=" * 60)

    for name, classifier in classifiers.items():
        print(f"\n>>> [{name}]")

        # Single train + test evaluation
        t0 = time.time()
        model = classifier.fit(train_data)
        train_time = time.time() - t0

        metrics = evaluate_model(model, test_data)

        # Cross-validation — boosted models use a lighter estimator for CV
        # to avoid O(num_folds × maxIter) sequential tree builds hanging the job.
        cv_estimator = _cv_estimator(classifier)
        if cv_estimator is not classifier:
            lite = CV_LITE_PARAMS[type(classifier).__name__]
            print(f">>> [EVAL] CV for {name} uses lite params {lite} (full model trained separately)")
        cv_auc = cross_validate(cv_estimator, train_data, num_folds=num_cv_folds)

        metrics["cv_auc"]       = cv_auc
        metrics["training_time"] = round(train_time, 2)

        print(f"    AUC:      {metrics['auc']:.4f}")
        print(f"    CV AUC:   {metrics['cv_auc']:.4f}")
        print(f"    Accuracy: {metrics['accuracy']:.4f}")
        print(f"    Train:    {train_time:.2f}s")

        results[name] = {"model": model, "metrics": metrics}

        if metrics["auc"] > best_auc:
            best_auc   = metrics["auc"]
            best_name  = name
            best_model = model

    print("\n" + "=" * 60)
    print(f"BEST MODEL: {best_name}  (AUC: {best_auc:.4f})")
    print("=" * 60)

    return {
        "all_results": results,
        "best_name":   best_name,
        "best_model":  best_model,
        "best_auc":    best_auc,
    }