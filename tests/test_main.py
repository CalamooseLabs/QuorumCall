"""Tests for FastAPI routes and _aggregate logic."""
import io
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


# ─── helpers ──────────────────────────────────────────────────────────────────

def upload_poll(client, title="Poll", questions=None, expires_at=None):
    if questions is None:
        questions = [{"id": "q1", "type": "short_answer", "title": "Q?"}]
    payload = json.dumps({"questions": questions}).encode()
    data = {"title": title}
    if expires_at:
        data["expires_at"] = expires_at
    return client.post(
        "/api/polls",
        data=data,
        files={"questions_file": ("q.json", io.BytesIO(payload), "application/json")},
    )


# ─── root ─────────────────────────────────────────────────────────────────────

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "QuorumCall"
    assert r.json()["version"] == "0.1.0"


# ─── poll page ────────────────────────────────────────────────────────────────

def test_poll_page_serves_html(client):
    r = client.get("/p/any-uuid-here")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<!DOCTYPE html>" in r.text


# ─── create poll ──────────────────────────────────────────────────────────────

def test_create_poll_success(client):
    r = upload_poll(client)
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert "poll_url" in body
    assert body["title"] == "Poll"
    assert "/p/" in body["poll_url"]


def test_create_poll_with_valid_expiry(client):
    r = upload_poll(client, expires_at="2030-01-01T00:00:00")
    assert r.status_code == 200


def test_create_poll_invalid_json(client):
    r = client.post(
        "/api/polls",
        data={"title": "Bad"},
        files={"questions_file": ("q.json", io.BytesIO(b"not json"), "application/json")},
    )
    assert r.status_code == 400


def test_create_poll_missing_questions_key(client):
    bad = json.dumps({"wrong_key": []}).encode()
    r = client.post(
        "/api/polls",
        data={"title": "Bad"},
        files={"questions_file": ("q.json", io.BytesIO(bad), "application/json")},
    )
    assert r.status_code == 400


def test_create_poll_invalid_expiry_format(client):
    r = upload_poll(client, expires_at="not-a-date")
    assert r.status_code == 400


def test_create_poll_toml_success(client):
    toml = b'[[questions]]\nid = "q1"\ntype = "short_answer"\ntitle = "Name?"\n'
    r = client.post(
        "/api/polls",
        data={"title": "TOML Poll"},
        files={"questions_file": ("q.toml", io.BytesIO(toml), "application/toml")},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "TOML Poll"


def test_create_poll_toml_invalid(client):
    r = client.post(
        "/api/polls",
        data={"title": "Bad"},
        files={"questions_file": ("q.toml", io.BytesIO(b"not = [valid toml"), "application/toml")},
    )
    assert r.status_code == 400


# ─── admin auth ───────────────────────────────────────────────────────────────

def test_admin_key_not_set_allows_all(client):
    r = client.get("/api/polls")
    assert r.status_code == 200


def test_admin_key_missing_header_rejected(client, monkeypatch):
    monkeypatch.setenv("QUORUMCALL_ADMIN_KEY", "secret")
    r = client.get("/api/polls")
    assert r.status_code == 403


def test_admin_key_wrong_header_rejected(client, monkeypatch):
    monkeypatch.setenv("QUORUMCALL_ADMIN_KEY", "secret")
    r = client.get("/api/polls", headers={"X-Admin-Key": "wrong"})
    assert r.status_code == 403


def test_admin_key_correct_header_passes(client, monkeypatch):
    monkeypatch.setenv("QUORUMCALL_ADMIN_KEY", "secret")
    r = client.get("/api/polls", headers={"X-Admin-Key": "secret"})
    assert r.status_code == 200


# ─── list polls ───────────────────────────────────────────────────────────────

def test_list_polls_empty(client):
    r = client.get("/api/polls")
    assert r.status_code == 200
    assert r.json() == []


def test_list_polls_returns_all(client):
    upload_poll(client, title="Alpha")
    upload_poll(client, title="Beta")
    r = client.get("/api/polls")
    assert r.status_code == 200
    titles = {p["title"] for p in r.json()}
    assert titles == {"Alpha", "Beta"}


# ─── get poll ─────────────────────────────────────────────────────────────────

def test_get_poll_success(client):
    pid = upload_poll(client).json()["id"]
    r = client.get(f"/api/polls/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid
    assert "questions" in r.json()


def test_get_poll_not_found(client):
    r = client.get("/api/polls/does-not-exist")
    assert r.status_code == 404


# ─── _is_expired branch coverage (exercised through get_poll) ─────────────────

def test_expired_by_flag(client, data_dir):
    from quorumcall import db
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}])
    db.expire_poll(pid)
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is True


def test_expired_by_naive_past_datetime(client, data_dir):
    from quorumcall import db
    past = datetime(2000, 1, 1)   # naive, past
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}], past)
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is True


def test_expired_by_aware_past_datetime(client, data_dir):
    from quorumcall import db
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)  # aware, past
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}], past)
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is True


def test_not_expired_future_datetime(client, data_dir):
    from quorumcall import db
    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}], future)
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is False


def test_not_expired_no_expires_at(client, data_dir):
    from quorumcall import db
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}])
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is False


# ─── submit response ──────────────────────────────────────────────────────────

def test_submit_response_success(client):
    pid = upload_poll(client).json()["id"]
    r = client.post(
        f"/api/polls/{pid}/responses",
        json={"answers": [{"question_id": "q1", "value": "hello"}]},
    )
    assert r.status_code == 200
    assert "response_id" in r.json()


def test_submit_response_poll_not_found(client):
    r = client.post("/api/polls/missing/responses", json={"answers": []})
    assert r.status_code == 404


def test_submit_response_poll_expired(client, data_dir):
    from quorumcall import db
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}])
    db.expire_poll(pid)
    r = client.post(f"/api/polls/{pid}/responses", json={"answers": []})
    assert r.status_code == 410


# ─── expire poll ──────────────────────────────────────────────────────────────

def test_expire_poll_route_success(client):
    pid = upload_poll(client).json()["id"]
    r = client.post(f"/api/polls/{pid}/expire")
    assert r.status_code == 200
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is True


def test_expire_poll_route_not_found(client):
    r = client.post("/api/polls/ghost/expire")
    assert r.status_code == 404


# ─── results – no responses ───────────────────────────────────────────────────

def test_results_no_responses(client):
    pid = upload_poll(client).json()["id"]
    r = client.get(f"/api/polls/{pid}/results")
    assert r.status_code == 200
    body = r.json()
    assert body["total_responses"] == 0
    assert body["results"]["q1"]["type"] == "text"
    assert body["results"]["q1"]["values"] == []
    assert body["responses"] == []


def test_results_individual_responses(client):
    pid = upload_poll(client).json()["id"]
    client.post(
        f"/api/polls/{pid}/responses",
        json={"answers": [{"question_id": "q1", "value": "hello"}]},
    )
    body = client.get(f"/api/polls/{pid}/results").json()
    assert body["total_responses"] == 1
    assert len(body["responses"]) == 1
    entry = body["responses"][0]
    assert "id" in entry
    assert "submitted_at" in entry
    assert entry["answers"] == [{"question_id": "q1", "value": "hello"}]


def test_results_not_found(client):
    assert client.get("/api/polls/missing/results").status_code == 404


# ─── _aggregate – full type coverage ─────────────────────────────────────────

def _make_typed_poll(data_dir, *types):
    from quorumcall import db
    questions = [{"id": f"q_{t}", "type": t, "title": t} for t in types]
    return db.create_poll("Typed", questions), questions


def test_aggregate_text_types(client, data_dir):
    from quorumcall import db
    text_types = ("short_answer", "long_answer", "email", "phone", "url", "date", "time", "datetime")
    pid, _ = _make_typed_poll(data_dir, *text_types)
    answers = [{"question_id": f"q_{t}", "value": "val"} for t in text_types]
    db.add_response(pid, answers)

    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    for t in text_types:
        assert res[f"q_{t}"]["type"] == "text"
        assert res[f"q_{t}"]["values"] == ["val"]


def test_aggregate_text_filters_null(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "short_answer")
    db.add_response(pid, [{"question_id": "q_short_answer", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_short_answer"]["values"] == []


def test_aggregate_radio_normal(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "radio")
    db.add_response(pid, [{"question_id": "q_radio", "value": "A"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_radio"]["type"] == "single_choice"
    assert res["q_radio"]["counts"]["A"] == 1
    assert res["q_radio"]["other_values"] == []


def test_aggregate_radio_other(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "radio")
    db.add_response(pid, [{"question_id": "q_radio", "value": "Other: custom"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_radio"]["other_values"] == ["custom"]
    assert res["q_radio"]["counts"] == {}


def test_aggregate_radio_null_skipped(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "radio")
    db.add_response(pid, [{"question_id": "q_radio", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_radio"]["counts"] == {}


def test_aggregate_dropdown_and_true_false(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "dropdown", "true_false")
    db.add_response(pid, [
        {"question_id": "q_dropdown", "value": "Option 1"},
        {"question_id": "q_true_false", "value": "Yes"},
    ])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_dropdown"]["type"] == "single_choice"
    assert res["q_true_false"]["type"] == "single_choice"


def test_aggregate_checkbox_list_with_other(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "checkbox")
    db.add_response(pid, [{"question_id": "q_checkbox", "value": ["X", "Other: custom"]}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_checkbox"]["type"] == "multiple_choice"
    assert res["q_checkbox"]["counts"]["X"] == 1
    assert res["q_checkbox"]["other_values"] == ["custom"]


def test_aggregate_checkbox_non_list_value(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "checkbox")
    db.add_response(pid, [{"question_id": "q_checkbox", "value": "A"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_checkbox"]["counts"]["A"] == 1


def test_aggregate_checkbox_falsy_items_skipped(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "checkbox")
    db.add_response(pid, [{"question_id": "q_checkbox", "value": [None, "", "A"]}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_checkbox"]["counts"] == {"A": 1}


def test_aggregate_likert_normal(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "likert")
    db.add_response(pid, [{"question_id": "q_likert", "value": "Agree"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_likert"]["type"] == "likert"
    assert res["q_likert"]["counts"]["Agree"] == 1


def test_aggregate_likert_null_skipped(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "likert")
    db.add_response(pid, [{"question_id": "q_likert", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_likert"]["counts"] == {}


def test_aggregate_numeric_with_values(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "slider", "number", "rating")
    db.add_response(pid, [
        {"question_id": "q_slider", "value": 50},
        {"question_id": "q_number", "value": 7},
        {"question_id": "q_rating", "value": 4},
    ])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    for qid in ("q_slider", "q_number", "q_rating"):
        assert res[qid]["type"] == "numeric"
        assert res[qid]["count"] == 1
        assert res[qid]["mean"] is not None
        assert res[qid]["min"] is not None
        assert res[qid]["max"] is not None


def test_aggregate_numeric_no_values(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "number")
    # submit a response that does NOT answer this question
    db.add_response(pid, [])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_number"]["count"] == 0
    assert res["q_number"]["mean"] is None
    assert res["q_number"]["min"] is None
    assert res["q_number"]["max"] is None


def test_aggregate_numeric_null_value_skipped(client, data_dir):
    from quorumcall import db
    pid, _ = _make_typed_poll(data_dir, "number")
    db.add_response(pid, [{"question_id": "q_number", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_number"]["count"] == 0


def test_aggregate_unknown_type_fallback(client, data_dir):
    from quorumcall import db
    questions = [{"id": "q1", "type": "mystery_type", "title": "?"}]
    pid = db.create_poll("P", questions)
    db.add_response(pid, [{"question_id": "q1", "value": "something"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q1"]["type"] == "other"
    assert res["q1"]["values"] == ["something"]


def test_aggregate_unknown_type_null_excluded(client, data_dir):
    from quorumcall import db
    questions = [{"id": "q1", "type": "mystery_type", "title": "?"}]
    pid = db.create_poll("P", questions)
    db.add_response(pid, [{"question_id": "q1", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q1"]["values"] == []
