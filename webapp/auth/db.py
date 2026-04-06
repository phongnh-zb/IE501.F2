import json
import os
import sqlite3
from datetime import datetime

from configs import config
from webapp.auth.models import User

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL,
    modules       TEXT    NOT NULL DEFAULT '[]',
    full_name     TEXT    NOT NULL,
    email         TEXT    NOT NULL,
    last_login    TEXT,
    created_at    TEXT    NOT NULL,
    created_by    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL,
    updated_by    TEXT    NOT NULL
);
"""

# Applied on every startup — silently ignored if column already exists
_MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN full_name  TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN email      TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN last_login TEXT",
    "ALTER TABLE users ADD COLUMN created_by TEXT NOT NULL DEFAULT 'cli'",
    "ALTER TABLE users ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN updated_by TEXT NOT NULL DEFAULT ''",
]

_VALID_ROLES = {"admin", "lecturer"}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _connect():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _validate(**fields):
    for name, value in fields.items():
        if not value or not str(value).strip():
            raise ValueError(f"'{name}' is required and cannot be blank.")
    if "role" in fields and fields["role"] not in _VALID_ROLES:
        raise ValueError(f"Invalid role '{fields['role']}'. Must be one of: {sorted(_VALID_ROLES)}.")


def init_db():
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)
        for sql in _MIGRATIONS:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass


def _row_to_user(row):
    return User(
        id         = row["id"],
        username   = row["username"],
        role       = row["role"],
        modules    = row["modules"],
        full_name  = row["full_name"],
        email      = row["email"],
        last_login = row["last_login"],
    )


def get_user_by_id(user_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, role, modules, full_name, email, last_login "
            "FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_username(username):
    """Return (User, password_hash) or (None, None) if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, role, modules, "
            "full_name, email, last_login FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row:
        return None, None
    return _row_to_user(row), row["password_hash"]


def create_user(username, password_hash, role, modules=None,
                full_name="", email="", created_by="cli"):
    _validate(
        username=username,
        password_hash=password_hash,
        role=role,
        full_name=full_name,
        email=email,
    )
    now          = _now()
    modules_json = json.dumps(modules or [])
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users "
            "(username, password_hash, role, modules, full_name, email, "
            " created_at, created_by, updated_at, updated_by) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (username, password_hash, role, modules_json,
             full_name, email, now, created_by, now, created_by),
        )


def update_last_login(user_id):
    now = _now()
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET last_login = ?, updated_at = ?, updated_by = ? WHERE id = ?",
            (now, now, "system", user_id),
        )