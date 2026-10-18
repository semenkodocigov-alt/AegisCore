# -*- coding: utf-8 -*-
"""Thread-safe SQLite database layer for Aegis-Core user management.

Uses threading.local() for per-thread connection isolation and PBKDF2
password hashing.  The database file is created in the project root as
``aegis_users.db``.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Database lives in the project root (parent of this package)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(_PROJECT_ROOT / "aegis_users.db")

# Allowed user roles
VALID_ROLES = frozenset({"admin", "user", "analyst"})

# ---------------------------------------------------------------------------
# Thread-local connection pool
# ---------------------------------------------------------------------------

_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    """Return a per-thread SQLite connection (created lazily).

    Connections use WAL journal mode for better concurrent read performance
    and return ``sqlite3.Row`` objects so columns are accessible by name.
    """
    conn: Optional[sqlite3.Connection] = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        # WAL mode allows concurrent reads while writing
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

def create_tables() -> None:
    """Create application storage tables if they do not exist.

    Safe to call multiple times (``IF NOT EXISTS``).
    """
    conn = _get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id             TEXT PRIMARY KEY,
            email          TEXT UNIQUE NOT NULL,
            nickname       TEXT NOT NULL DEFAULT '',
            password_hash  TEXT NOT NULL,
            role           TEXT NOT NULL DEFAULT 'user'
                           CHECK (role IN ('admin', 'user', 'analyst')),
            created_at     REAL NOT NULL,
            last_login_at  REAL,
            remember_token TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        )
        """
    )
    conn.commit()


def get_setting(key: str) -> str | None:
    """Read an application setting from the local database."""
    row = _get_connection().execute(
        "SELECT setting_value FROM app_settings WHERE setting_key = ?",
        (key,),
    ).fetchone()
    return str(row["setting_value"]) if row else None


def set_setting(key: str, value: str) -> None:
    """Persist an application setting in the local database."""
    conn = _get_connection()
    conn.execute(
        """
        INSERT INTO app_settings (setting_key, setting_value)
        VALUES (?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
        """,
        (key, value),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def add_user(
    email: str,
    password_hash: str,
    nickname: str = "",
    role: str = "user",
) -> Optional[dict]:
    """Insert a new user and return its dict representation.

    Returns ``None`` if the email already exists or the role is invalid.
    """
    if role not in VALID_ROLES:
        return None

    user_id = str(uuid.uuid4())
    now = time.time()

    try:
        conn = _get_connection()
        conn.execute(
            """
            INSERT INTO users (id, email, nickname, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, email.lower().strip(), nickname, password_hash, role, now),
        )
        conn.commit()
        return {
            "id": user_id,
            "email": email.lower().strip(),
            "nickname": nickname,
            "role": role,
            "created_at": now,
            "last_login_at": None,
        }
    except sqlite3.IntegrityError:
        # Duplicate email
        return None
    except sqlite3.Error:
        return None


def get_user_by_email(email: str) -> Optional[dict]:
    """Look up a user by e-mail address (case-insensitive).

    Returns a plain ``dict`` or ``None``.
    """
    try:
        conn = _get_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Look up a user by UUID.

    Returns a plain ``dict`` or ``None``.
    """
    try:
        conn = _get_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        return None


def update_last_login(user_id: str, remember_token: str | None = None) -> bool:
    """Set ``last_login_at`` to *now* and optionally store a remember token.

    Returns ``True`` on success.
    """
    try:
        conn = _get_connection()
        conn.execute(
            """
            UPDATE users
               SET last_login_at  = ?,
                   remember_token = ?
             WHERE id = ?
            """,
            (time.time(), remember_token, user_id),
        )
        conn.commit()
        return conn.total_changes > 0
    except sqlite3.Error:
        return False


def update_user_profile(
    user_id: str,
    email: str,
    nickname: str,
    password_hash: str | None = None,
) -> Optional[dict]:
    """Update a user's profile and return the updated public database row."""
    try:
        conn = _get_connection()
        if password_hash is None:
            cursor = conn.execute(
                """
                UPDATE users
                   SET email = ?, nickname = ?
                 WHERE id = ?
                """,
                (email.lower().strip(), nickname.strip(), user_id),
            )
        else:
            cursor = conn.execute(
                """
                UPDATE users
                   SET email = ?, nickname = ?, password_hash = ?
                 WHERE id = ?
                """,
                (email.lower().strip(), nickname.strip(), password_hash, user_id),
            )
        conn.commit()
        if cursor.rowcount != 1:
            return None
        return get_user_by_id(user_id)
    except sqlite3.Error:
        return None


def delete_user(user_id: str) -> bool:
    """Permanently delete a user by UUID.

    Returns ``True`` when exactly one row was removed.
    """
    try:
        conn = _get_connection()
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount == 1
    except sqlite3.Error:
        return False


# ---------------------------------------------------------------------------
# Auto-create tables on first import
# ---------------------------------------------------------------------------
create_tables()
