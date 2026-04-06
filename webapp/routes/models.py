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
    return render_template("models.html", models=model_results, history=history)