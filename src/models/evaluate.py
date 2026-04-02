import time

from pyspark.ml.evaluation import (BinaryClassificationEvaluator,
                                   MulticlassClassificationEvaluator)
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder


def evaluate_model(model, test_data, label_col="label"):
    predictions = model.transform(test_data)

    # AUC
    auc_evaluator = BinaryClassificationEvaluator(labelCol=label_col)
    auc = auc_evaluator.evaluate(predictions)

    # Accuracy
    acc_evaluator = MulticlassClassificationEvaluator(
        labelCol=label_col, predictionCol="prediction", metricName="accuracy"
    )
    accuracy = acc_evaluator.evaluate(predictions)

    return {"auc": auc, "accuracy": accuracy, "predictions": predictions}


def cross_validate(classifier, train_data, label_col="label", num_folds=5):
    evaluator = BinaryClassificationEvaluator(labelCol=label_col)

    # Empty param grid → evaluates the classifier as-is with k-fold
    param_grid = ParamGridBuilder().build()

    cv = CrossValidator(
        estimator=classifier,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        numFolds=num_folds,
        seed=42,
    )

    print(f">>> [EVAL] Running {num_folds}-fold cross-validation...")
    cv_model = cv.fit(train_data)
    avg_auc = cv_model.avgMetrics[0]

    print(f">>> [EVAL] CV Average AUC: {avg_auc:.4f}")
    return {"cv_model": cv_model, "avg_auc": avg_auc}


def run_evaluation(classifiers, train_data, test_data):
    results = {}
    best_model_name = ""
    best_auc = 0.0
    best_model = None

    print("=" * 60)
    print("STARTING MODEL TRAINING & EVALUATION")
    print("=" * 60)

    for name, classifier in classifiers.items():
        start_time = time.time()

        # Train
        model = classifier.fit(train_data)

        # Evaluate
        metrics = evaluate_model(model, test_data)
        duration = time.time() - start_time

        print(f"\n>>> {name}")
        print(f"    AUC:      {metrics['auc']:.4f}")
        print(f"    Accuracy: {metrics['accuracy']:.4f}")
        print(f"    Time:     {duration:.2f}s")

        results[name] = {
            "model": model,
            "metrics": metrics,
            "duration": duration,
        }

        if metrics["auc"] > best_auc:
            best_auc = metrics["auc"]
            best_model_name = name
            best_model = model

    print("\n" + "=" * 60)
    print(f"BEST MODEL: {best_model_name} (AUC: {best_auc:.4f})")
    print("=" * 60)

    return {
        "all_results": results,
        "best_name": best_model_name,
        "best_model": best_model,
        "best_auc": best_auc,
    }