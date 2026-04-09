from flask import Blueprint, render_template
from flask_login import login_required

from webapp.services.cache import (get_model_history_from_hbase,
                                   get_model_results_from_hbase)

models_bp = Blueprint("models", __name__)


@models_bp.route("/models")
@login_required
def models():
    model_results = get_model_results_from_hbase()
    history       = get_model_history_from_hbase()
    best          = next((m for m in model_results if m["is_best"]), model_results[0] if model_results else None)
    return render_template(
        "models/index.html",
        models=model_results,
        history=history,
        best=best,
    )