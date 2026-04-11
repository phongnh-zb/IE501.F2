import json

from pyspark.ml.classification import (GBTClassificationModel, LinearSVCModel,
                                       LogisticRegressionModel,
                                       RandomForestClassificationModel)

TREE_TYPES = (RandomForestClassificationModel, GBTClassificationModel)
COEF_TYPES = (LogisticRegressionModel, LinearSVCModel)


def _normalize(values):
    total = sum(abs(v) for v in values)
    if total == 0:
        return [0.0] * len(values)
    return [abs(v) / total for v in values]


def extract_feature_importance(model, feature_cols):
    raw = None
    model_type = type(model).__name__

    if isinstance(model, TREE_TYPES):
        raw = list(model.featureImportances.toArray())

    elif isinstance(model, COEF_TYPES):
        raw = list(model.coefficients.toArray())

    elif hasattr(model, "featureImportances"):
        # XGBoostModelWrapper and any future adapter exposing featureImportances
        raw = list(model.featureImportances.toArray())

    else:
        print(f">>> [EXPLAIN] Cannot extract importance for {model_type}: unsupported type.")
        return None

    normalized = _normalize(raw)
    ranked = sorted(zip(feature_cols, normalized), key=lambda x: x[1], reverse=True)

    print(f">>> [EXPLAIN] Feature Importance — {model_type}:")
    for feat, score in ranked:
        bar = "█" * int(score * 40)
        print(f"    {feat:<25s} {score:.4f}  {bar}")

    return ranked


def importance_to_json(ranked):
    if not ranked:
        return "[]"
    # Cast to Python float — numpy float32/float64 are not JSON serializable
    return json.dumps([{"feature": f, "score": round(float(s), 4)} for f, s in ranked])


def get_model_summary(model):
    if hasattr(model, "summary"):
        summary = model.summary
        return {
            "areaUnderROC": getattr(summary, "areaUnderROC", None),
            "accuracy":     getattr(summary, "accuracy", None),
        }
    return None