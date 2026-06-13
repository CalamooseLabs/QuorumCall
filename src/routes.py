"""FastAPI route handlers for QuorumCall, grouped on a single ``APIRouter``.

main.py builds the application and includes this router. Keeping the handlers
here — together with the small request helpers they share — separates request
logic from app assembly. Response aggregation lives in results.py.
"""

import json
import os
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

import db
from log import get_logger
from results import aggregate
from schemas import SubmitRequest
from settings import load_settings
from ui import render_html

router = APIRouter()
log = get_logger()


def _base_url() -> str:
    """Public base URL used to build shareable poll links."""
    return os.environ.get("QUORUMCALL_BASE_URL", "http://localhost:8000")


def _is_expired(row) -> bool:
    """Return True if a poll row is closed, either explicitly or past ``expires_at``."""
    if row["is_expired"]:
        return True
    if row["expires_at"]:
        exp = datetime.fromisoformat(row["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp
    return False


def _require_admin(x_admin_key: Optional[str] = Header(default=None)):
    """Dependency: reject the request unless the admin key matches (when one is set)."""
    key = os.environ.get("QUORUMCALL_ADMIN_KEY", "")
    if key and x_admin_key != key:
        raise HTTPException(status_code=403, detail="Forbidden")


def _parse_questions_file(content: bytes, filename: str) -> list:
    """Parse an uploaded questions file as JSON or TOML, chosen by extension."""
    ext = Path(filename or "").suffix.lower()
    try:
        if ext == ".toml":
            return tomllib.loads(content.decode())["questions"]
        return json.loads(content)["questions"]
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, UnicodeDecodeError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid file: {e}")


def _poll_or_404(poll_id: str):
    """Fetch a poll row or raise 404."""
    row = db.get_poll(poll_id)
    if not row:
        raise HTTPException(status_code=404, detail="Poll not found")
    return row


@router.get("/", response_class=JSONResponse)
def root():
    return {"service": "QuorumCall", "version": "0.1.0"}


@router.get("/p/{poll_id}", response_class=HTMLResponse)
def poll_page(poll_id: str):
    return HTMLResponse(content=render_html(load_settings()))


@router.post("/api/polls", dependencies=[Depends(_require_admin)])
async def create_poll(
    title: str = Form(...),
    questions_file: UploadFile = File(...),
    expires_at: Optional[str] = Form(default=None),
):
    content = await questions_file.read()
    questions = _parse_questions_file(content, questions_file.filename or "")

    exp_dt = None
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expires_at — use ISO 8601")

    poll_id = db.create_poll(title, questions, exp_dt)
    url = f"{_base_url()}/p/{poll_id}"
    log.info(f"poll created [bold]{poll_id}[/bold] — {title!r}")
    return {"id": poll_id, "title": title, "poll_url": url}


@router.get("/api/polls", dependencies=[Depends(_require_admin)])
def list_polls():
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "created_at": r["created_at"],
            "expires_at": r["expires_at"],
            "is_expired": _is_expired(r),
            "poll_url": f"{_base_url()}/p/{r['id']}",
        }
        for r in db.list_polls()
    ]


@router.get("/api/polls/{poll_id}")
def get_poll(poll_id: str):
    row = _poll_or_404(poll_id)
    return {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "is_expired": _is_expired(row),
        "questions": json.loads(row["questions_json"]),
    }


@router.post("/api/polls/{poll_id}/responses")
def submit_response(poll_id: str, payload: SubmitRequest):
    row = _poll_or_404(poll_id)
    if _is_expired(row):
        raise HTTPException(status_code=410, detail="Poll has expired")
    response_id = db.add_response(poll_id, [a.model_dump() for a in payload.answers])
    log.info(f"response [bold]{response_id}[/bold] → poll [bold]{poll_id}[/bold]")
    return {"response_id": response_id}


@router.get("/api/polls/{poll_id}/results", dependencies=[Depends(_require_admin)])
def get_results(poll_id: str):
    row = _poll_or_404(poll_id)
    questions = json.loads(row["questions_json"])
    responses = db.get_responses(poll_id)
    return {
        "poll_id": poll_id,
        "title": row["title"],
        "is_expired": _is_expired(row),
        "total_responses": len(responses),
        "questions": questions,
        "results": aggregate(questions, responses),
        "responses": [
            {
                "id": r["id"],
                "submitted_at": r["submitted_at"],
                "answers": json.loads(r["answers_json"]),
            }
            for r in responses
        ],
    }


@router.post("/api/polls/{poll_id}/expire", dependencies=[Depends(_require_admin)])
def expire_poll(poll_id: str):
    if not db.expire_poll(poll_id):
        raise HTTPException(status_code=404, detail="Poll not found")
    log.info(f"poll expired [bold]{poll_id}[/bold]")
    return {"message": "Poll expired"}
