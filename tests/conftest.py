import logging

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _silence_logging():
    """Suppress all log output during tests."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Isolated temp database; clears all relevant env vars."""
    monkeypatch.setenv("QUORUMCALL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("QUORUMCALL_ADMIN_KEY", raising=False)
    monkeypatch.delenv("QUORUMCALL_BASE_URL", raising=False)
    monkeypatch.delenv("QUORUMCALL_HOST", raising=False)
    monkeypatch.delenv("QUORUMCALL_PORT", raising=False)
    monkeypatch.delenv("QUORUMCALL_SETTINGS_FILE", raising=False)
    import db
    db.init_db()
    return tmp_path


@pytest.fixture
def client(data_dir):
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def questions():
    return [
        {"id": "q1", "type": "short_answer", "title": "Name?", "required": True},
        {"id": "q2", "type": "radio", "title": "Color?", "options": ["Red", "Blue"]},
    ]


@pytest.fixture
def poll_id(data_dir, questions):
    import db
    return db.create_poll("Test Poll", questions)
