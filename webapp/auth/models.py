import json

from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, username, role, modules="[]", full_name="",
                 email="", last_login=None, is_blocked=False, failed_attempts=0):
        self.id              = str(id)
        self.username        = username
        self.role            = role
        self.full_name       = full_name
        self.email           = email
        self.last_login      = last_login
        self.is_blocked      = is_blocked
        self.failed_attempts = failed_attempts

        if isinstance(modules, str):
            try:
                self.modules = json.loads(modules)
            except (ValueError, TypeError):
                self.modules = []
        else:
            self.modules = modules or []

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def display_name(self):
        return self.full_name or self.username

    def can_see_module(self, module_code):
        if self.is_admin or not self.modules:
            return True
        return module_code in self.modules

    # Flask-Login — blocked users cannot be active
    @property
    def is_active(self):
        return not self.is_blocked

    def get_id(self):
        return self.id