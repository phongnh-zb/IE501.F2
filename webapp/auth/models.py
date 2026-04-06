import json

from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, username, role, modules, full_name="", email="", last_login=None):
        self.id         = str(id)
        self.username   = username
        self.role       = role          # 'admin' or 'lecturer'
        self.full_name  = full_name or ""
        self.email      = email or ""
        self.last_login = last_login    # ISO datetime string or None
        # modules: JSON-encoded list of code_module strings.
        # Empty list means the user can see all modules (admin or head of dept).
        self.modules    = json.loads(modules) if isinstance(modules, str) else (modules or [])

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def display_name(self):
        return self.full_name if self.full_name else self.username

    def can_see_module(self, code_module):
        if self.is_admin:
            return True
        if not self.modules:
            return True
        return code_module in self.modules

    def filter_students(self, students):
        if self.is_admin or not self.modules:
            return students
        return [s for s in students if self.can_see_module(s.get("code_module", ""))]