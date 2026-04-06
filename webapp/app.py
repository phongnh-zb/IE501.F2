import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask

from configs.config import FLASK_PORT
from webapp.routes.api import api_bp
from webapp.routes.dashboard import dashboard_bp
from webapp.routes.models import models_bp
from webapp.routes.students import students_bp
from webapp.services.cache import start_background_scheduler

logging.basicConfig(level=logging.INFO)


def create_app():
    app = Flask(__name__)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(api_bp)

    return app


app = create_app()

if __name__ == "__main__":
    start_background_scheduler()
    app.run(debug=True, port=FLASK_PORT, use_reloader=False)