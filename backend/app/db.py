"""SQLite storage (standard library only)."""
import sqlite3
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    pw_salt BLOB NOT NULL,
    pw_hash BLOB NOT NULL,
    age_group TEXT,
    gender TEXT,
    residence TEXT,
    consent_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    day TEXT NOT NULL,                 -- yyyy-MM-dd (client local date)
    social_media REAL NOT NULL,
    entertainment REAL NOT NULL,
    gaming REAL NOT NULL,
    productivity REAL NOT NULL,
    education REAL NOT NULL,
    other REAL NOT NULL,
    mood_text TEXT NOT NULL,
    vader_compound REAL NOT NULL,
    transformer_risk REAL,             -- NULL when no transformer configured
    text_risk REAL NOT NULL,
    text_risk_source TEXT NOT NULL,    -- 'vader_proxy' | 'transformer'
    violation_ratio REAL NOT NULL,     -- share of the 6 categories over their threshold
    behavior_score REAL NOT NULL,      -- value actually used in fusion
    behavior_source TEXT NOT NULL,     -- 'threshold_rules' | 'random_forest'
    fused_score REAL NOT NULL,
    tier TEXT NOT NULL,
    crisis_flag INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, day)
);
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    instrument TEXT NOT NULL,          -- phq9 | gad7 | pss10
    answers_json TEXT NOT NULL,
    total INTEGER NOT NULL,
    band TEXT NOT NULL,
    item9_positive INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)
