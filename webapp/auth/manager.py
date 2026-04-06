from flask_login import LoginManager

from webapp.auth.db import get_user_by_id

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access this page."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)