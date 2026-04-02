from pyspark.ml.classification import (GBTClassificationModel,
                                       RandomForestClassificationModel)

TREE_MODEL_TYPES = (RandomForestClassificationModel, GBTClassificationModel)


def extract_feature_importance(model, feature_cols):
    if not isinstance(model, TREE_MODEL_TYPES):
        print(f">>> [EXPLAIN] Skipping — {type(model).__name__} does not expose featureImportances.")
        return None

    importances = model.featureImportances.toArray()

    ranked = sorted(
        zip(feature_cols, importances),
        key=lambda x: x[1],
        reverse=True,
    )

    print(">>> [EXPLAIN] Feature Importance:")
    for feat, score in ranked:
        bar = "█" * int(score * 40)
        print(f"    {feat:<20s} {score:.4f}  {bar}")

    return ranked


def get_model_summary(model):
    # Logistic Regression exposes a summary with extra stats
    if hasattr(model, "summary"):
        summary = model.summary
        return {
            "areaUnderROC": summary.areaUnderROC,
            "accuracy": summary.accuracy,
        }
    return None