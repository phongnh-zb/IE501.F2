import json

from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, username, role, modules):
        self.id       = str(id)
        self.username = username
        self.role     = role  # 'admin' or 'lecturer'
        # modules: JSON-encoded list of code_module strings.
        # Empty list means the user can see all modules (admin equivalent).
        self.modules  = json.loads(modules) if isinstance(modules, str) else modules

    @property
    def is_admin(self):
        return self.role == "admin"

    def can_see_module(self, code_module):
        """Return True if this user has access to the given module code."""
        if self.is_admin:
            return True
        # Lecturer with empty modules list sees everything (e.g. a head of department)
        if not self.modules:
            return True
        return code_module in self.modules

    def filter_students(self, students):
        """Return only the student records visible to this user."""
        if self.is_admin or not self.modules:
            return students
        return [s for s in students if self.can_see_module(s.get("code_module", ""))]