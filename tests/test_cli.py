"""Tests for CLI subcommands."""
import json
import os
from unittest.mock import patch

import pytest


def run_cli(*argv):
    with patch("sys.argv", ["quorumcall", *argv]):
        from cli import main
        main()


# ─── add-poll ─────────────────────────────────────────────────────────────────

def test_add_poll_basic(data_dir, tmp_path, questions, capsys):
    q_file = tmp_path / "q.json"
    q_file.write_text(json.dumps({"questions": questions}))
    run_cli("add-poll", "--title", "My Poll", "--file", str(q_file))
    out = capsys.readouterr().out
    assert "Created:" in out
    assert "URL:" in out


def test_add_poll_with_expiry(data_dir, tmp_path, questions):
    q_file = tmp_path / "q.json"
    q_file.write_text(json.dumps({"questions": questions}))
    run_cli("add-poll", "--title", "Expiring", "--file", str(q_file), "--expires", "2030-01-01T00:00:00")
    import db
    rows = db.list_polls()
    assert len(rows) == 1
    assert "2030" in rows[0]["expires_at"]


def test_add_poll_without_expiry(data_dir, tmp_path, questions):
    q_file = tmp_path / "q.json"
    q_file.write_text(json.dumps({"questions": questions}))
    run_cli("add-poll", "--title", "Forever", "--file", str(q_file))
    import db
    assert db.list_polls()[0]["expires_at"] is None


def test_add_poll_custom_data_dir(tmp_path, monkeypatch, questions):
    """--data-dir creates the directory and writes the db there."""
    monkeypatch.delenv("QUORUMCALL_DATA_DIR", raising=False)
    sub = tmp_path / "custom"
    q_file = tmp_path / "q.json"
    q_file.write_text(json.dumps({"questions": questions}))
    run_cli("add-poll", "--title", "Dir Test", "--file", str(q_file), "--data-dir", str(sub))
    assert (sub / "quorumcall.db").exists()


def test_add_poll_toml(data_dir, tmp_path, capsys):
    toml = b'[[questions]]\nid = "q1"\ntype = "short_answer"\ntitle = "Name?"\n'
    q_file = tmp_path / "q.toml"
    q_file.write_bytes(toml)
    run_cli("add-poll", "--title", "TOML Poll", "--file", str(q_file))
    out = capsys.readouterr().out
    assert "Created:" in out


def test_add_poll_uses_base_url_from_env(data_dir, tmp_path, questions, monkeypatch, capsys):
    monkeypatch.setenv("QUORUMCALL_BASE_URL", "https://polls.example.com")
    q_file = tmp_path / "q.json"
    q_file.write_text(json.dumps({"questions": questions}))
    run_cli("add-poll", "--title", "T", "--file", str(q_file))
    assert "polls.example.com" in capsys.readouterr().out


# ─── list-polls ───────────────────────────────────────────────────────────────

def test_list_polls_empty(data_dir, capsys):
    run_cli("list-polls")
    assert "No polls." in capsys.readouterr().out


def test_list_polls_active(data_dir, questions, capsys):
    import db
    db.create_poll("Active Poll", questions)
    run_cli("list-polls")
    out = capsys.readouterr().out
    assert "Active Poll" in out
    assert "active" in out


def test_list_polls_expired_by_flag(data_dir, questions, capsys):
    import db
    pid = db.create_poll("Old", questions)
    db.expire_poll(pid)
    run_cli("list-polls")
    assert "EXPIRED" in capsys.readouterr().out


def test_list_polls_no_expires_at(data_dir, questions, capsys):
    """Poll with no expires_at shows 'never'."""
    import db
    db.create_poll("Forever", questions)
    run_cli("list-polls")
    assert "never" in capsys.readouterr().out


def test_list_polls_expired_by_naive_past_datetime(data_dir, questions, capsys):
    import db
    from datetime import datetime
    db.create_poll("Past", questions, datetime(2000, 1, 1))  # naive, past
    run_cli("list-polls")
    assert "EXPIRED" in capsys.readouterr().out


def test_list_polls_not_expired_by_aware_future_datetime(data_dir, questions, capsys):
    import db
    from datetime import datetime, timezone
    db.create_poll("Future", questions, datetime(2099, 1, 1, tzinfo=timezone.utc))
    run_cli("list-polls")
    assert "active" in capsys.readouterr().out


# ─── expire-poll ──────────────────────────────────────────────────────────────

def test_expire_poll_success(data_dir, poll_id, capsys):
    run_cli("expire-poll", poll_id)
    assert "Expired:" in capsys.readouterr().out
    import db
    assert db.get_poll(poll_id)["is_expired"] == 1


def test_expire_poll_not_found(data_dir, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli("expire-poll", "no-such-uuid")
    assert exc.value.code == 1
    assert "Not found:" in capsys.readouterr().out


# ─── serve ────────────────────────────────────────────────────────────────────

def test_serve_uses_cli_args(data_dir, monkeypatch):
    monkeypatch.delenv("QUORUMCALL_HOST", raising=False)
    monkeypatch.delenv("QUORUMCALL_PORT", raising=False)
    with patch("uvicorn.run") as mock_run:
        run_cli("serve", "--host", "10.0.0.1", "--port", "7777")
    assert mock_run.call_args.kwargs["host"] == "10.0.0.1"
    assert mock_run.call_args.kwargs["port"] == 7777


def test_serve_uses_env_vars(data_dir, monkeypatch):
    monkeypatch.setenv("QUORUMCALL_HOST", "0.0.0.0")
    monkeypatch.setenv("QUORUMCALL_PORT", "9999")
    with patch("uvicorn.run") as mock_run:
        run_cli("serve")
    assert mock_run.call_args.kwargs["host"] == "0.0.0.0"
    assert mock_run.call_args.kwargs["port"] == 9999


def test_serve_sets_base_url_when_absent(data_dir, monkeypatch):
    monkeypatch.delenv("QUORUMCALL_BASE_URL", raising=False)
    with patch("uvicorn.run"):
        run_cli("serve", "--host", "127.0.0.1", "--port", "8080")
    assert os.environ.get("QUORUMCALL_BASE_URL") == "http://127.0.0.1:8080"


def test_serve_does_not_override_existing_base_url(data_dir, monkeypatch):
    monkeypatch.setenv("QUORUMCALL_BASE_URL", "https://polls.example.com")
    with patch("uvicorn.run"):
        run_cli("serve")
    assert os.environ["QUORUMCALL_BASE_URL"] == "https://polls.example.com"
