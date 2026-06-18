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
    path = str(_db_path())
    # WAL lets readers run concurrently with a writer (helps the read-heavy
    # /results and /p routes). It must be set outside a transaction, so use a
    # throwaway connection; the mode then persists in the DB file.
    wal = sqlite3.connect(path)
    try:
        wal.execute("PRAGMA journal_mode=WAL")
    finally:
        wal.close()

    # Two single-statement execute() calls (not executescript, which would force
    # an implicit COMMIT and break the manual transaction managed by _conn()).
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                id             TEXT PRIMARY KEY,
                title          TEXT NOT NULL,
                created_at     TEXT NOT NULL,
                expires_at     TEXT,
                is_expired     INTEGER NOT NULL DEFAULT 0,
                questions_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id           TEXT PRIMARY KEY,
                poll_id      TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                FOREIGN KEY (poll_id) REFERENCES polls(id)
            )
        """)
        # /results filters responses by poll_id; without this index every call
        # full-scans the whole responses table.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_responses_poll_id ON responses(poll_id)"
        )


@contextmanager
def _conn():
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    # Manual transaction control: sqlite3's legacy isolation only opens an
    # implicit transaction before DML, so DDL would auto-commit and escape a
    # rollback. An explicit BEGIN wraps every statement (DML and DDL alike).
    conn.isolation_level = None
    # SQLite ignores declared foreign keys unless this is enabled per connection.
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("BEGIN")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def is_expired(row) -> bool:
    """True if a poll row is closed — explicitly flagged or past ``expires_at``.

    Tolerates a malformed stored ``expires_at`` (treats it as not-expired so the
    poll stays readable rather than 500-ing). Shared by the API and the CLI.
    """
    if row["is_expired"]:
        return True
    raw = row["expires_at"]
    if not raw:
        return False
    try:
        exp = datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > exp


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
