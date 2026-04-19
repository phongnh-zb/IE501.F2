import json
import os
import sqlite3
from datetime import datetime

from configs import config
from webapp.auth.models import User

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    UNIQUE NOT NULL,
    password_hash   TEXT    NOT NULL,
    role            TEXT    NOT NULL,
    modules         TEXT    NOT NULL DEFAULT '[]',
    full_name       TEXT    NOT NULL,
    email           TEXT    NOT NULL,
    last_login      TEXT,
    is_blocked      INTEGER NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    blocked_at      TEXT,
    created_at      TEXT    NOT NULL,
    created_by      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    updated_by      TEXT    NOT NULL
);
"""

_MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN full_name       TEXT    NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN email           TEXT    NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN last_login      TEXT",
    "ALTER TABLE users ADD COLUMN created_by      TEXT    NOT NULL DEFAULT 'cli'",
    "ALTER TABLE users ADD COLUMN updated_at      TEXT    NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN updated_by      TEXT    NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN is_blocked      INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN blocked_at      TEXT",
]

_VALID_ROLES    = {"admin", "lecturer"}
_MAX_ATTEMPTS   = 5


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
        raise ValueError(f"Invalid role '{fields['role']}'.")


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
        id              = row["id"],
        username        = row["username"],
        role            = row["role"],
        modules         = row["modules"],
        full_name       = row["full_name"],
        email           = row["email"],
        last_login      = row["last_login"],
        is_blocked      = bool(row["is_blocked"]),
        failed_attempts = row["failed_attempts"],
    )


def get_user_by_id(user_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, role, modules, full_name, email, "
            "last_login, is_blocked, failed_attempts "
            "FROM users WHERE id = ?", (user_id,),
        ).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_username(username):
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, role, modules, "
            "full_name, email, last_login, is_blocked, failed_attempts "
            "FROM users WHERE username = ?", (username,),
        ).fetchone()
    if not row:
        return None, None
    return _row_to_user(row), row["password_hash"]


def list_users():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, username, role, modules, full_name, email, "
            "last_login, is_blocked, failed_attempts "
            "FROM users ORDER BY role ASC, full_name ASC"
        ).fetchall()
    return [_row_to_user(r) for r in rows]


def create_user(username, password_hash, role, modules=None,
                full_name="", email="", created_by="cli"):
    _validate(username=username, password_hash=password_hash,
              role=role, full_name=full_name, email=email)
    now          = _now()
    modules_json = json.dumps(modules or [])
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users "
            "(username, password_hash, role, modules, full_name, email, "
            " is_blocked, failed_attempts, "
            " created_at, created_by, updated_at, updated_by) "
            "VALUES (?,?,?,?,?,?,0,0,?,?,?,?)",
            (username, password_hash, role, modules_json,
             full_name, email, now, created_by, now, created_by),
        )


def update_last_login(user_id):
    now = _now()
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET last_login=?, failed_attempts=0, "
            "updated_at=?, updated_by='system' WHERE id=?",
            (now, now, user_id),
        )


def update_user_info(user_id, full_name, email):
    _validate(full_name=full_name, email=email)
    with _connect() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email=? AND id!=?",
            (email.strip(), user_id),
        ).fetchone()
        if existing:
            raise ValueError("Email already in use by another account.")
        conn.execute(
            "UPDATE users SET full_name=?, email=?, updated_at=?, updated_by=? WHERE id=?",
            (full_name.strip(), email.strip(), _now(), str(user_id), user_id),
        )


def update_user_role_modules(user_id, full_name, email, modules, updated_by):
    _validate(full_name=full_name, email=email)
    with _connect() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email=? AND id!=?",
            (email.strip(), user_id),
        ).fetchone()
        if existing:
            raise ValueError("Email already in use by another account.")
        conn.execute(
            "UPDATE users SET full_name=?, email=?, modules=?, "
            "updated_at=?, updated_by=? WHERE id=?",
            (full_name.strip(), email.strip(), json.dumps(modules),
             _now(), str(updated_by), user_id),
        )


def get_password_hash(user_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id=?", (user_id,)
        ).fetchone()
    return row["password_hash"] if row else None


def update_password(user_id, new_password_hash):
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash=?, updated_at=?, updated_by=? WHERE id=?",
            (new_password_hash, _now(), str(user_id), user_id),
        )


def delete_user(user_id, requesting_user_id):
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    if str(user_id) == str(requesting_user_id):
        raise ValueError("You cannot delete your own account.")
    if user.role == "admin":
        raise ValueError("Admin accounts cannot be deleted through the UI.")
    with _connect() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))


def block_user(user_id, blocked_by):
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    if user.role == "admin":
        raise ValueError("Admin accounts cannot be blocked through the UI.")
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET is_blocked=1, blocked_at=?, "
            "updated_at=?, updated_by=? WHERE id=?",
            (_now(), _now(), str(blocked_by), user_id),
        )


def unblock_user(user_id, unblocked_by):
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET is_blocked=0, failed_attempts=0, blocked_at=NULL, "
            "updated_at=?, updated_by=? WHERE id=?",
            (_now(), str(unblocked_by), user_id),
        )


def increment_failed_attempts(user_id):
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = failed_attempts + 1, "
            "updated_at=?, updated_by='system' WHERE id=?",
            (_now(), user_id),
        )
        row = conn.execute(
            "SELECT failed_attempts FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if row and row["failed_attempts"] >= _MAX_ATTEMPTS:
            conn.execute(
                "UPDATE users SET is_blocked=1, blocked_at=?, "
                "updated_at=?, updated_by='system' WHERE id=?",
                (_now(), _now(), user_id),
            )
            return True   # newly blocked
    return False