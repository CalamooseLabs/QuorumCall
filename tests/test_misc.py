"""Tests for schemas, html rendering, settings, and package version."""


def test_version():
    import quorumcall
    assert quorumcall.__version__ == "0.1.0"


def test_render_html_default():
    from quorumcall.html import render_html
    from quorumcall.settings import DEFAULTS
    html = render_html(DEFAULTS)
    assert "<!DOCTYPE html>" in html
    assert DEFAULTS["primary_color"] in html


def test_render_html_custom_primary_color():
    from quorumcall.html import render_html
    html = render_html({"primary_color": "#ff5500"})
    assert "#ff5500" in html


def test_render_html_brand_injected():
    from quorumcall.html import render_html
    html = render_html({"brand_name": "Acme Corp", "brand_icon": "https://example.com/logo.png"})
    assert "Acme Corp" in html
    assert "https://example.com/logo.png" in html


def test_load_settings_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("QUORUMCALL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("QUORUMCALL_SETTINGS_FILE", raising=False)
    from quorumcall.settings import load_settings, DEFAULTS
    assert load_settings() == DEFAULTS


def test_load_settings_from_file(tmp_path, monkeypatch):
    f = tmp_path / "settings.json"
    f.write_text('{"primary_color": "#ff0000"}')
    monkeypatch.setenv("QUORUMCALL_SETTINGS_FILE", str(f))
    from quorumcall.settings import load_settings, DEFAULTS
    s = load_settings()
    assert s["primary_color"] == "#ff0000"
    assert s["brand_name"] == DEFAULTS["brand_name"]


def test_load_settings_missing_file_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("QUORUMCALL_SETTINGS_FILE", str(tmp_path / "nope.json"))
    from quorumcall.settings import load_settings, DEFAULTS
    assert load_settings() == DEFAULTS


def test_answer_value_accepts_any_type():
    from quorumcall.schemas import AnswerValue
    assert AnswerValue(question_id="q1", value="text").value == "text"
    assert AnswerValue(question_id="q1", value=42).value == 42
    assert AnswerValue(question_id="q1", value=["a", "b"]).value == ["a", "b"]
    assert AnswerValue(question_id="q1", value=None).value is None


def test_submit_request_wraps_answers():
    from quorumcall.schemas import AnswerValue, SubmitRequest
    sr = SubmitRequest(answers=[
        AnswerValue(question_id="q1", value="yes"),
        AnswerValue(question_id="q2", value=3),
    ])
    assert len(sr.answers) == 2
    assert sr.answers[0].question_id == "q1"
