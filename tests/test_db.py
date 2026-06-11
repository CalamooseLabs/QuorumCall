import json
import pytest
from datetime import datetime, timezone


def test_init_db_idempotent(data_dir):
    import db
    db.init_db()
    db.init_db()  # second call must not raise


def test_create_poll_returns_uuid(data_dir, questions):
    import db
    pid = db.create_poll("My Poll", questions)
    assert len(pid) == 36
    assert pid.count("-") == 4


def test_create_poll_without_expiry(data_dir, questions):
    import db
    pid = db.create_poll("No Expiry", questions)
    row = db.get_poll(pid)
    assert row["title"] == "No Expiry"
    assert row["is_expired"] == 0
    assert row["expires_at"] is None
    assert json.loads(row["questions_json"]) == questions


def test_create_poll_with_expiry(data_dir, questions):
    import db
    exp = datetime(2030, 6, 1, tzinfo=timezone.utc)
    pid = db.create_poll("Expiring", questions, exp)
    row = db.get_poll(pid)
    assert "2030" in row["expires_at"]


def test_get_poll_missing(data_dir):
    import db
    assert db.get_poll("no-such-uuid") is None


def test_list_polls_empty(data_dir):
    import db
    assert db.list_polls() == []


def test_list_polls_most_recent_first(data_dir, questions):
    import db
    id1 = db.create_poll("First", questions)
    id2 = db.create_poll("Second", questions)
    rows = db.list_polls()
    assert len(rows) == 2
    assert rows[0]["id"] == id2
    assert rows[1]["id"] == id1


def test_expire_poll_found(data_dir, questions):
    import db
    pid = db.create_poll("Poll", questions)
    assert db.expire_poll(pid) is True
    assert db.get_poll(pid)["is_expired"] == 1


def test_expire_poll_missing(data_dir):
    import db
    assert db.expire_poll("ghost-id") is False


def test_add_and_get_responses(data_dir, questions):
    import db
    pid = db.create_poll("Poll", questions)
    answers = [{"question_id": "q1", "value": "Alice"}]
    rid = db.add_response(pid, answers)
    assert len(rid) == 36

    responses = db.get_responses(pid)
    assert len(responses) == 1
    assert json.loads(responses[0]["answers_json"]) == answers


def test_get_responses_empty(data_dir, questions):
    import db
    pid = db.create_poll("Poll", questions)
    assert db.get_responses(pid) == []


def test_conn_rolls_back_on_exception(data_dir):
    from db import _conn
    with pytest.raises(RuntimeError):
        with _conn() as conn:
            conn.execute("CREATE TABLE tmp_test (x TEXT)")
            raise RuntimeError("deliberate")

    # table must not exist after rollback
    with _conn() as conn:
        hit = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tmp_test'"
        ).fetchall()
        assert hit == []
