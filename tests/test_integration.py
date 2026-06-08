"""Integration tests — spin up a real uvicorn process and hit it with httpx.

Run with:  pytest -m integration
Excluded from the default runtests run.
"""
import io
import json
import socket
import subprocess
import sys
import time

import httpx
import pytest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(base_url: str, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            httpx.get(f"{base_url}/", timeout=1).raise_for_status()
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"Server at {base_url} did not become ready within {timeout}s")


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """Start quorumcall serve on a random port; yield (base_url, httpx.Client)."""
    data_dir = tmp_path_factory.mktemp("integration_data")
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "quorumcall.cli",
            "serve",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--data-dir", str(data_dir),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_ready(base_url)
        with httpx.Client(base_url=base_url, timeout=5.0) as client:
            yield base_url, client
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.integration
def test_root_endpoint(server):
    _, client = server
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "QuorumCall"
    assert "version" in body


@pytest.mark.integration
def test_poll_page_serves_html(server):
    _, client = server
    r = client.get("/p/some-uuid")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<!DOCTYPE html>" in r.text


@pytest.mark.integration
def test_full_poll_lifecycle(server):
    _, client = server
    questions = [
        {"id": "q1", "type": "short_answer", "title": "Name?", "required": True},
        {"id": "q2", "type": "radio", "title": "Size?", "options": ["S", "M", "L"]},
    ]
    payload = json.dumps({"questions": questions}).encode()

    # create
    r = client.post(
        "/api/polls",
        data={"title": "Shirt Sizes"},
        files={"questions_file": ("q.json", io.BytesIO(payload), "application/json")},
    )
    assert r.status_code == 200
    poll_id = r.json()["id"]
    assert "/p/" in r.json()["poll_url"]

    # get definition
    r = client.get(f"/api/polls/{poll_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Shirt Sizes"

    # submit two responses
    for name, size in [("Alice", "M"), ("Bob", "L")]:
        r = client.post(
            f"/api/polls/{poll_id}/responses",
            json={"answers": [
                {"question_id": "q1", "value": name},
                {"question_id": "q2", "value": size},
            ]},
        )
        assert r.status_code == 200
        assert "response_id" in r.json()

    # results — aggregated + individual
    r = client.get(f"/api/polls/{poll_id}/results")
    assert r.status_code == 200
    body = r.json()
    assert body["total_responses"] == 2

    # aggregated
    assert body["results"]["q1"]["type"] == "text"
    assert set(body["results"]["q1"]["values"]) == {"Alice", "Bob"}
    assert body["results"]["q2"]["counts"] == {"M": 1, "L": 1}

    # individual
    assert len(body["responses"]) == 2
    for entry in body["responses"]:
        assert "id" in entry
        assert "submitted_at" in entry
        assert len(entry["answers"]) == 2


@pytest.mark.integration
def test_expire_poll(server):
    _, client = server
    questions = [{"id": "q1", "type": "short_answer", "title": "Q?"}]
    payload = json.dumps({"questions": questions}).encode()

    r = client.post(
        "/api/polls",
        data={"title": "To Expire"},
        files={"questions_file": ("q.json", io.BytesIO(payload), "application/json")},
    )
    poll_id = r.json()["id"]

    r = client.post(f"/api/polls/{poll_id}/expire")
    assert r.status_code == 200

    r = client.post(
        f"/api/polls/{poll_id}/responses",
        json={"answers": [{"question_id": "q1", "value": "hi"}]},
    )
    assert r.status_code == 410


@pytest.mark.integration
def test_admin_key_enforced(tmp_path_factory):
    """Server started with QUORUMCALL_ADMIN_KEY set must reject missing/wrong keys."""
    data_dir = tmp_path_factory.mktemp("integration_auth")
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "quorumcall.cli",
            "serve",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--data-dir", str(data_dir),
        ],
        env={**__import__("os").environ, "QUORUMCALL_ADMIN_KEY": "s3cr3t"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_ready(base_url)
        with httpx.Client(base_url=base_url, timeout=5.0) as client:
            assert client.get("/api/polls").status_code == 403
            assert client.get("/api/polls", headers={"X-Admin-Key": "wrong"}).status_code == 403
            assert client.get("/api/polls", headers={"X-Admin-Key": "s3cr3t"}).status_code == 200
    finally:
        proc.terminate()
        proc.wait(timeout=5)
