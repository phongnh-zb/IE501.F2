import json
import os
import sqlite3
from datetime import datetime

from configs import config
from webapp.auth.models import User

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT    UNIQUE NOT NULL,
    password_hash TEXT   NOT NULL,
    role         TEXT    NOT NULL DEFAULT 'lecturer',
    modules      TEXT    NOT NULL DEFAULT '[]',
    created_at   TEXT    NOT NULL
);
"""


def _connect():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)
        conn.commit()


def get_user_by_id(user_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, role, modules FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return User(row["id"], row["username"], row["role"], row["modules"])


def get_user_by_username(username):
    """Return (User, password_hash) or (None, None) if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, role, modules FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row:
        return None, None
    user = User(row["id"], row["username"], row["role"], row["modules"])
    return user, row["password_hash"]


def create_user(username, password_hash, role="lecturer", modules=None):
    modules_json = json.dumps(modules or [])
    created_at   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, modules, created_at) VALUES (?,?,?,?,?)",
            (username, password_hash, role, modules_json, created_at),
        )
        conn.commit()