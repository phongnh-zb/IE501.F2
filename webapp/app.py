import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask

from configs.config import FLASK_PORT, SECRET_KEY
from webapp.auth.db import init_db
from webapp.auth.manager import login_manager
from webapp.auth.routes import auth_bp
from webapp.routes.api import api_bp
from webapp.routes.dashboard import dashboard_bp
from webapp.routes.models import models_bp
from webapp.routes.pipeline import pipeline_bp
from webapp.routes.profile import profile_bp
from webapp.routes.students import students_bp
from webapp.services.cache import start_background_scheduler

logging.basicConfig(level=logging.INFO)


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    login_manager.init_app(app)
    init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(api_bp)

    @app.route("/favicon.ico")
    def favicon():
        from flask import send_from_directory
        return send_from_directory(
            app.static_folder, "favicon.svg", mimetype="image/svg+xml"
        )

    @app.errorhandler(403)
    def forbidden(_):
        from flask import render_template
        return render_template("403.html"), 403

    @app.template_filter("format_number")
    def format_number(value):
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return value

    return app


app = create_app()

if __name__ == "__main__":
    start_background_scheduler()
    app.run(host="0.0.0.0", debug=True, port=FLASK_PORT, use_reloader=False)