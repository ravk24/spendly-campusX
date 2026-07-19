"""SQLite data layer for Spendly (Step 1 — Database Setup).

All timestamps stored by this schema are UTC (SQLite's datetime('now')).
"""

import sqlite3
from datetime import date
from pathlib import Path

from flask import g
from werkzeug.security import generate_password_hash

# spendly.db lives in the project root, regardless of the current working directory.
DB_PATH = Path(__file__).resolve().parent.parent / "spendly.db"


def get_db():
    """Return the SQLite connection for the current app context, opening it if needed."""
    if "db" not in g:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        # Per-connection in SQLite; never assume it persists.
        db.execute("PRAGMA foreign_keys = ON")
        g.db = db
    return g.db


def close_db(e=None):
    """Close the app-context connection. Registered via app.teardown_appcontext."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and indexes. Idempotent — safe to run on every startup."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount      REAL    NOT NULL CHECK (amount > 0),
            category    TEXT    NOT NULL CHECK (category IN
                ('Food','Transport','Bills','Health','Entertainment','Shopping','Other')),
            date        TEXT    NOT NULL CHECK (date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
            description TEXT,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date)"
    )
    db.commit()


# (amount, category, day-of-month, description) — days all ≤ 28 so February works.
_SEED_EXPENSES = [
    (450.00, "Food", "02", "Groceries"),
    (120.00, "Transport", "04", "Metro card top-up"),
    (1500.00, "Bills", "05", "Electricity bill"),
    (600.00, "Health", "08", "Pharmacy"),
    (350.00, "Entertainment", "11", "Movie night"),
    (999.00, "Shopping", "15", "Headphones"),
    (200.00, "Other", "18", None),
    (275.00, "Food", "21", "Dinner out"),
]


def seed_db():
    """Insert the demo user and expenses exactly once (keyed on the demo email)."""
    db = get_db()
    email = "demo@spendly.com".strip().lower()

    exists = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
    if exists is not None:
        return

    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", email, generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    month_prefix = f"{date.today():%Y-%m}-"
    for amount, category, day, description in _SEED_EXPENSES:
        db.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, round(amount, 2), category, month_prefix + day, description),
        )

    db.commit()
