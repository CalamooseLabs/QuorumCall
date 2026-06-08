import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def _db_path() -> Path:
    return Path(os.environ.get("QUORUMCALL_DATA_DIR", ".")) / "quorumcall.db"


def init_db() -> None:
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS polls (
                id             TEXT PRIMARY KEY,
                title          TEXT NOT NULL,
                created_at     TEXT NOT NULL,
                expires_at     TEXT,
                is_expired     INTEGER NOT NULL DEFAULT 0,
                questions_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS responses (
                id           TEXT PRIMARY KEY,
                poll_id      TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                FOREIGN KEY (poll_id) REFERENCES polls(id)
            );
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_poll(title: str, questions: list, expires_at: datetime | None = None) -> str:
    poll_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    exp = expires_at.isoformat() if expires_at else None
    with _conn() as conn:
        conn.execute(
            "INSERT INTO polls VALUES (?, ?, ?, ?, 0, ?)",
            (poll_id, title, now, exp, json.dumps(questions)),
        )
    return poll_id


def get_poll(poll_id: str):
    with _conn() as conn:
        return conn.execute("SELECT * FROM polls WHERE id = ?", (poll_id,)).fetchone()


def list_polls() -> list:
    with _conn() as conn:
        return conn.execute("SELECT * FROM polls ORDER BY created_at DESC").fetchall()


def expire_poll(poll_id: str) -> bool:
    with _conn() as conn:
        r = conn.execute("UPDATE polls SET is_expired = 1 WHERE id = ?", (poll_id,))
        return r.rowcount > 0


def add_response(poll_id: str, answers: list) -> str:
    response_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO responses VALUES (?, ?, ?, ?)",
            (response_id, poll_id, now, json.dumps(answers)),
        )
    return response_id


def get_responses(poll_id: str) -> list:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM responses WHERE poll_id = ?", (poll_id,)
        ).fetchall()
