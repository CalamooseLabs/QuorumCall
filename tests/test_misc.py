"""Tests for schemas, html rendering, settings, and package version."""


def test_version():
    from _version import __version__
    assert __version__ == "0.1.0"


def test_render_html_default():
    from ui import render_html
    from settings import DEFAULTS
    html = render_html(DEFAULTS)
    assert "<!DOCTYPE html>" in html
    assert DEFAULTS["primary_color"] in html


def test_render_html_custom_primary_color():
    from ui import render_html
    html = render_html({"primary_color": "#ff5500"})
    assert "#ff5500" in html


def test_render_html_brand_injected():
    from ui import render_html
    html = render_html({"brand_name": "Acme Corp", "brand_icon": "https://example.com/logo.png"})
    assert "Acme Corp" in html
    assert "https://example.com/logo.png" in html


def test_render_builder_html_default():
    from builder import render_builder_html
    from settings import DEFAULTS
    html = render_builder_html(DEFAULTS)
    assert "<!DOCTYPE html>" in html
    assert DEFAULTS["primary_color"] in html
    assert "Create a poll" in html
    assert 'id="qlist"' in html
    # presets sidebar
    assert 'id="presets"' in html
    assert "Quick add" in html
    assert "Shirt size" in html


def test_render_builder_html_custom_primary_color():
    from builder import render_builder_html
    html = render_builder_html({"primary_color": "#ff5500"})
    assert "#ff5500" in html


def test_render_builder_html_brand_injected():
    from builder import render_builder_html
    html = render_builder_html({"brand_name": "Acme Corp", "brand_icon": "https://example.com/logo.png"})
    assert "Acme Corp" in html
    assert "https://example.com/logo.png" in html


def test_load_settings_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("QUORUMCALL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("QUORUMCALL_SETTINGS_FILE", raising=False)
    from settings import load_settings, DEFAULTS
    assert load_settings() == DEFAULTS


def test_load_settings_from_file(tmp_path, monkeypatch):
    f = tmp_path / "settings.json"
    f.write_text('{"primary_color": "#ff0000"}')
    monkeypatch.setenv("QUORUMCALL_SETTINGS_FILE", str(f))
    from settings import load_settings, DEFAULTS
    s = load_settings()
    assert s["primary_color"] == "#ff0000"
    assert s["brand_name"] == DEFAULTS["brand_name"]


def test_load_settings_missing_file_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("QUORUMCALL_SETTINGS_FILE", str(tmp_path / "nope.json"))
    from settings import load_settings, DEFAULTS
    assert load_settings() == DEFAULTS


def test_answer_value_accepts_any_type():
    from schemas import AnswerValue
    assert AnswerValue(question_id="q1", value="text").value == "text"
    assert AnswerValue(question_id="q1", value=42).value == 42
    assert AnswerValue(question_id="q1", value=["a", "b"]).value == ["a", "b"]
    assert AnswerValue(question_id="q1", value=None).value is None


def test_submit_request_wraps_answers():
    from schemas import AnswerValue, SubmitRequest
    sr = SubmitRequest(answers=[
        AnswerValue(question_id="q1", value="yes"),
        AnswerValue(question_id="q2", value=3),
    ])
    assert len(sr.answers) == 2
    assert sr.answers[0].question_id == "q1"


# ─── config injection hardening ───────────────────────────────────────────────

def test_render_html_escapes_script_breakout():
    from ui import render_html
    html = render_html({"brand_name": "</script><script>alert(1)</script>"})
    assert "</script><script>alert(1)" not in html
    assert "<\\/script>" in html


def test_render_html_rejects_unsafe_color():
    from ui import render_html
    from settings import DEFAULTS
    html = render_html({"primary_color": "red;}</style><script>alert(2)</script>"})
    assert "</style><script>alert(2)" not in html  # no new style-breakout introduced
    assert f"--p:{DEFAULTS['primary_color']};" in html  # fell back to the default


def test_render_html_accepts_valid_colors():
    from ui import render_html
    for c in ["#fff", "#3b82f6", "rebeccapurple", "rgb(1, 2, 3)", "hsl(10, 50%, 50%)"]:
        assert f"--p:{c};" in render_html({"primary_color": c})


# ─── settings helpers ─────────────────────────────────────────────────────────

def test_base_url_default_and_env(monkeypatch):
    from settings import base_url, DEFAULT_BASE_URL
    monkeypatch.delenv("QUORUMCALL_BASE_URL", raising=False)
    assert base_url() == DEFAULT_BASE_URL
    monkeypatch.setenv("QUORUMCALL_BASE_URL", "https://x.example")
    assert base_url() == "https://x.example"


# ─── questions parsing/validation ─────────────────────────────────────────────

def test_parse_questions_valid():
    from questions import parse_questions
    qs = parse_questions(b'{"questions":[{"id":"q1","type":"radio"}]}', "q.json")
    assert qs[0]["id"] == "q1"


def test_parse_questions_toml():
    from questions import parse_questions
    qs = parse_questions(b'[[questions]]\nid = "q1"\ntype = "short_answer"\n', "q.toml")
    assert qs[0]["type"] == "short_answer"


def test_parse_questions_rejects_bad_input():
    import pytest
    from questions import parse_questions
    bad = [
        b"[1,2,3]",                                                   # not a dict
        b'{"questions":[1,2,3]}',                                     # item not an object
        b'{"questions":[{"type":"x"}]}',                              # missing id
        b'{"questions":[{"id":"a"}]}',                                # missing type
        b'{"questions":[{"id":"a","type":"x"},{"id":"a","type":"y"}]}',  # dup id
        b"not json",                                                 # unparseable
    ]
    for body in bad:
        with pytest.raises(ValueError):
            parse_questions(body, "q.json")


# ─── expiry helper tolerates malformed data ───────────────────────────────────

def test_aggregate_skips_question_without_id():
    from results import aggregate
    out = aggregate(
        [{"type": "short_answer", "title": "no id"},
         {"id": "q1", "type": "short_answer", "title": "ok"}],
        [],
    )
    assert list(out) == ["q1"]


def test_db_is_expired_handles_malformed_expires_at():
    import db
    assert db.is_expired({"is_expired": 0, "expires_at": "not-a-date"}) is False
    assert db.is_expired({"is_expired": 1, "expires_at": None}) is True
    assert db.is_expired({"is_expired": 0, "expires_at": None}) is False
