"""SQLite connection + idempotent schema migration."""
from __future__ import annotations
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
  match_id TEXT PRIMARY KEY, league TEXT, home TEXT, away TEXT,
  kickoff_utc TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS odds_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT, match_id TEXT, market TEXT,
  selection TEXT, line REAL, book TEXT, decimal_odds REAL,
  captured_at TEXT, snapshot_type TEXT,
  FOREIGN KEY (match_id) REFERENCES matches(match_id)
);
CREATE TABLE IF NOT EXISTS bets (
  bet_id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, match_id TEXT,
  league TEXT, market TEXT, selection TEXT, line REAL, model_prob REAL,
  fair_prob REAL, edge REAL, ev REAL, taken_odds REAL, book TEXT,
  stake REAL, status TEXT, explanation TEXT,
  FOREIGN KEY (match_id) REFERENCES matches(match_id)
);
CREATE TABLE IF NOT EXISTS clv (
  bet_id INTEGER PRIMARY KEY, closing_odds REAL, closing_fair_prob REAL,
  clv_price REAL, clv_prob REAL, settled_at TEXT,
  FOREIGN KEY (bet_id) REFERENCES bets(bet_id)
);
CREATE TABLE IF NOT EXISTS settlements (
  bet_id INTEGER PRIMARY KEY, grade TEXT, profit REAL, settled_at TEXT,
  FOREIGN KEY (bet_id) REFERENCES bets(bet_id)
);
"""

def connect(db_path: str) -> sqlite3.Connection:
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # Additive migration for DBs created before the explanation column existed.
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(bets)")}
    if "explanation" not in cols:
        conn.execute("ALTER TABLE bets ADD COLUMN explanation TEXT")
    conn.commit()
