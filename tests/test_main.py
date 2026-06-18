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


# ─── builder page ───────────────────────────────────────────────────────────────

def test_builder_page_serves_html(client):
    r = client.get("/new")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<!DOCTYPE html>" in r.text
    assert "Create a poll" in r.text
    assert 'id="qlist"' in r.text


def test_create_poll_from_builder_shape(client):
    # Mirrors what the builder posts: a JSON blob with branching (string + dict `next`).
    questions = [
        {"id": "q1", "type": "radio", "title": "Happy?", "options": ["Yes", "No"],
         "next": {"Yes": "q3", "No": "q2"}},
        {"id": "q2", "type": "long_answer", "title": "Why not?", "next": "q3"},
        {"id": "q3", "type": "rating", "title": "Rate us", "rating_max": 5, "required": True},
    ]
    r = upload_poll(client, title="Builder poll", questions=questions)
    assert r.status_code == 200
    poll_id = r.json()["id"]
    got = client.get(f"/api/polls/{poll_id}").json()
    assert got["questions"] == questions


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
    import db
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}])
    db.expire_poll(pid)
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is True


def test_expired_by_naive_past_datetime(client, data_dir):
    import db
    past = datetime(2000, 1, 1)   # naive, past
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}], past)
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is True


def test_expired_by_aware_past_datetime(client, data_dir):
    import db
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)  # aware, past
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}], past)
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is True


def test_not_expired_future_datetime(client, data_dir):
    import db
    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    pid = db.create_poll("P", [{"id": "q1", "type": "short_answer", "title": "Q"}], future)
    assert client.get(f"/api/polls/{pid}").json()["is_expired"] is False


def test_not_expired_no_expires_at(client, data_dir):
    import db
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
    import db
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
    import db
    questions = [{"id": f"q_{t}", "type": t, "title": t} for t in types]
    return db.create_poll("Typed", questions), questions


def test_aggregate_text_types(client, data_dir):
    import db
    text_types = ("short_answer", "long_answer", "email", "phone", "url", "date", "time", "datetime")
    pid, _ = _make_typed_poll(data_dir, *text_types)
    answers = [{"question_id": f"q_{t}", "value": "val"} for t in text_types]
    db.add_response(pid, answers)

    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    for t in text_types:
        assert res[f"q_{t}"]["type"] == "text"
        assert res[f"q_{t}"]["values"] == ["val"]


def test_aggregate_text_filters_null(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "short_answer")
    db.add_response(pid, [{"question_id": "q_short_answer", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_short_answer"]["values"] == []


def test_aggregate_radio_normal(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "radio")
    db.add_response(pid, [{"question_id": "q_radio", "value": "A"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_radio"]["type"] == "single_choice"
    assert res["q_radio"]["counts"]["A"] == 1
    assert res["q_radio"]["other_values"] == []


def test_aggregate_radio_other(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "radio")
    db.add_response(pid, [{"question_id": "q_radio", "value": "Other: custom"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_radio"]["other_values"] == ["custom"]
    assert res["q_radio"]["counts"] == {}


def test_aggregate_radio_null_skipped(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "radio")
    db.add_response(pid, [{"question_id": "q_radio", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_radio"]["counts"] == {}


def test_aggregate_dropdown_and_true_false(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "dropdown", "true_false")
    db.add_response(pid, [
        {"question_id": "q_dropdown", "value": "Option 1"},
        {"question_id": "q_true_false", "value": "Yes"},
    ])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_dropdown"]["type"] == "single_choice"
    assert res["q_true_false"]["type"] == "single_choice"


def test_aggregate_checkbox_list_with_other(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "checkbox")
    db.add_response(pid, [{"question_id": "q_checkbox", "value": ["X", "Other: custom"]}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_checkbox"]["type"] == "multiple_choice"
    assert res["q_checkbox"]["counts"]["X"] == 1
    assert res["q_checkbox"]["other_values"] == ["custom"]


def test_aggregate_checkbox_non_list_value(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "checkbox")
    db.add_response(pid, [{"question_id": "q_checkbox", "value": "A"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_checkbox"]["counts"]["A"] == 1


def test_aggregate_checkbox_falsy_items_skipped(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "checkbox")
    db.add_response(pid, [{"question_id": "q_checkbox", "value": [None, "", "A"]}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_checkbox"]["counts"] == {"A": 1}


def test_aggregate_likert_normal(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "likert")
    db.add_response(pid, [{"question_id": "q_likert", "value": "Agree"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_likert"]["type"] == "likert"
    assert res["q_likert"]["counts"]["Agree"] == 1


def test_aggregate_likert_null_skipped(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "likert")
    db.add_response(pid, [{"question_id": "q_likert", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_likert"]["counts"] == {}


def test_aggregate_numeric_with_values(client, data_dir):
    import db
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
    import db
    pid, _ = _make_typed_poll(data_dir, "number")
    # submit a response that does NOT answer this question
    db.add_response(pid, [])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_number"]["count"] == 0
    assert res["q_number"]["mean"] is None
    assert res["q_number"]["min"] is None
    assert res["q_number"]["max"] is None


def test_aggregate_numeric_null_value_skipped(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "number")
    db.add_response(pid, [{"question_id": "q_number", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q_number"]["count"] == 0


def test_aggregate_unknown_type_fallback(client, data_dir):
    import db
    questions = [{"id": "q1", "type": "mystery_type", "title": "?"}]
    pid = db.create_poll("P", questions)
    db.add_response(pid, [{"question_id": "q1", "value": "something"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q1"]["type"] == "other"
    assert res["q1"]["values"] == ["something"]


def test_aggregate_unknown_type_null_excluded(client, data_dir):
    import db
    questions = [{"id": "q1", "type": "mystery_type", "title": "?"}]
    pid = db.create_poll("P", questions)
    db.add_response(pid, [{"question_id": "q1", "value": None}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]
    assert res["q1"]["values"] == []


def test_aggregate_numeric_non_numeric_ignored(client, data_dir):
    """A non-numeric value to a numeric question must be ignored, not 500 the view."""
    import db
    pid, _ = _make_typed_poll(data_dir, "number")
    db.add_response(pid, [{"question_id": "q_number", "value": "abc"}])
    db.add_response(pid, [{"question_id": "q_number", "value": ["nope"]}])
    db.add_response(pid, [{"question_id": "q_number", "value": 7}])
    r = client.get(f"/api/polls/{pid}/results")
    assert r.status_code == 200
    res = r.json()["results"]["q_number"]
    assert res["count"] == 1
    assert res["values"] == [7.0]


def test_aggregate_checkbox_scalar_other(client, data_dir):
    import db
    pid, _ = _make_typed_poll(data_dir, "checkbox")
    db.add_response(pid, [{"question_id": "q_checkbox", "value": "Other: x"}])
    res = client.get(f"/api/polls/{pid}/results").json()["results"]["q_checkbox"]
    assert res["other_values"] == ["x"]
    assert res["counts"] == {}


# ─── create-poll structural validation ───────────────────────────────────────

def test_create_poll_question_missing_id(client):
    r = upload_poll(client, questions=[{"type": "radio", "title": "Q", "options": ["a"]}])
    assert r.status_code == 400


def test_create_poll_question_missing_type(client):
    r = upload_poll(client, questions=[{"id": "q1", "title": "Q"}])
    assert r.status_code == 400


def test_create_poll_duplicate_ids(client):
    qs = [{"id": "q1", "type": "short_answer", "title": "A"},
          {"id": "q1", "type": "short_answer", "title": "B"}]
    assert upload_poll(client, questions=qs).status_code == 400


def test_create_poll_non_list_questions(client):
    r = client.post(
        "/api/polls",
        data={"title": "x"},
        files={"questions_file": ("q.json", io.BytesIO(b"[1,2,3]"), "application/json")},
    )
    assert r.status_code == 400


def test_create_poll_toml_missing_questions(client):
    r = client.post(
        "/api/polls",
        data={"title": "x"},
        files={"questions_file": ("q.toml", io.BytesIO(b'title = "x"\n'), "application/toml")},
    )
    assert r.status_code == 400


def test_create_poll_invalid_utf8(client):
    r = client.post(
        "/api/polls",
        data={"title": "x"},
        files={"questions_file": ("q.toml", io.BytesIO(b"\xff\xfe"), "application/toml")},
    )
    assert r.status_code == 400


# ─── submit validation, body cap, public-vs-admin ─────────────────────────────

def test_submit_response_invalid_payload(client):
    pid = upload_poll(client).json()["id"]
    assert client.post(f"/api/polls/{pid}/responses", json={}).status_code == 422
    assert client.post(
        f"/api/polls/{pid}/responses", json={"answers": [{"value": "x"}]}
    ).status_code == 422


def test_oversized_body_rejected(client):
    pid = upload_poll(client).json()["id"]
    big = "A" * 1_100_000  # > 1 MiB cap
    r = client.post(
        f"/api/polls/{pid}/responses",
        json={"answers": [{"question_id": "q1", "value": big}]},
    )
    assert r.status_code == 413


def test_submit_stays_open_when_admin_key_set(client, monkeypatch):
    pid = upload_poll(client).json()["id"]
    monkeypatch.setenv("QUORUMCALL_ADMIN_KEY", "secret")
    # admin routes now gated...
    assert upload_poll(client, title="gated").status_code == 403
    assert client.get(f"/api/polls/{pid}/results").status_code == 403
    # ...but the public submit endpoint is unaffected
    r = client.post(
        f"/api/polls/{pid}/responses",
        json={"answers": [{"question_id": "q1", "value": "hi"}]},
    )
    assert r.status_code == 200


def test_crafted_markup_path_does_not_500(client):
    """A path with unbalanced Rich markup must not crash the request via the log line."""
    import logging
    from log import setup_logging
    logging.disable(logging.NOTSET)
    setup_logging()
    try:
        r = client.get("/api/polls/%5B%2Fcyan%5D")  # decodes to /api/polls/[/cyan]
        assert r.status_code == 404
    finally:
        logging.disable(logging.CRITICAL)
