import json
import os
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

import db
from ui import render_html
from settings import load_settings
from log import get_logger
from schemas import SubmitRequest

app = FastAPI(title="QuorumCall", version="0.1.0")
log = get_logger()


def _base_url() -> str:
    return os.environ.get("QUORUMCALL_BASE_URL", "http://localhost:8000")


def _is_expired(row) -> bool:
    if row["is_expired"]:
        return True
    if row["expires_at"]:
        exp = datetime.fromisoformat(row["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp
    return False


def _require_admin(x_admin_key: Optional[str] = Header(default=None)):
    key = os.environ.get("QUORUMCALL_ADMIN_KEY", "")
    if key and x_admin_key != key:
        raise HTTPException(status_code=403, detail="Forbidden")


def _parse_questions_file(content: bytes, filename: str) -> list:
    ext = Path(filename or "").suffix.lower()
    try:
        if ext == ".toml":
            return tomllib.loads(content.decode())["questions"]
        return json.loads(content)["questions"]
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, UnicodeDecodeError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid file: {e}")


def _poll_or_404(poll_id: str):
    row = db.get_poll(poll_id)
    if not row:
        raise HTTPException(status_code=404, detail="Poll not found")
    return row


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    sc = response.status_code
    color = "green" if sc < 400 else "yellow" if sc < 500 else "red"
    log.info(
        f"[cyan]{request.method:<6}[/cyan]  {request.url.path:<45} [{color}]{sc}[/{color}]  {ms:>5.0f}ms"
    )
    return response


@app.get("/", response_class=JSONResponse)
def root():
    return {"service": "QuorumCall", "version": "0.1.0"}


@app.get("/p/{poll_id}", response_class=HTMLResponse)
def poll_page(poll_id: str):
    return HTMLResponse(content=render_html(load_settings()))


@app.post("/api/polls", dependencies=[Depends(_require_admin)])
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


@app.get("/api/polls", dependencies=[Depends(_require_admin)])
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


@app.get("/api/polls/{poll_id}")
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


@app.post("/api/polls/{poll_id}/responses")
def submit_response(poll_id: str, payload: SubmitRequest):
    row = _poll_or_404(poll_id)
    if _is_expired(row):
        raise HTTPException(status_code=410, detail="Poll has expired")
    response_id = db.add_response(poll_id, [a.model_dump() for a in payload.answers])
    log.info(f"response [bold]{response_id}[/bold] → poll [bold]{poll_id}[/bold]")
    return {"response_id": response_id}


@app.get("/api/polls/{poll_id}/results", dependencies=[Depends(_require_admin)])
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
        "results": _aggregate(questions, responses),
        "responses": [
            {
                "id": r["id"],
                "submitted_at": r["submitted_at"],
                "answers": json.loads(r["answers_json"]),
            }
            for r in responses
        ],
    }


@app.post("/api/polls/{poll_id}/expire", dependencies=[Depends(_require_admin)])
def expire_poll(poll_id: str):
    if not db.expire_poll(poll_id):
        raise HTTPException(status_code=404, detail="Poll not found")
    log.info(f"poll expired [bold]{poll_id}[/bold]")
    return {"message": "Poll expired"}


def _aggregate(questions: list, responses: list) -> dict:
    out = {}
    for q in questions:
        qid, qtype = q["id"], q["type"]
        vals = []
        for resp in responses:
            for a in json.loads(resp["answers_json"]):
                if a["question_id"] == qid:
                    vals.append(a["value"])
                    break

        if qtype in ("short_answer", "long_answer", "email", "phone", "url", "date", "time", "datetime"):
            out[qid] = {"type": "text", "values": [v for v in vals if v]}

        elif qtype in ("radio", "dropdown", "true_false"):
            counts: dict = {}
            other: list = []
            for v in vals:
                if v is None:
                    continue
                if isinstance(v, str) and v.startswith("Other: "):
                    other.append(v[7:])
                else:
                    counts[v] = counts.get(v, 0) + 1
            out[qid] = {"type": "single_choice", "counts": counts, "other_values": other}

        elif qtype == "checkbox":
            counts = {}
            other = []
            for v in vals:
                for item in (v if isinstance(v, list) else [v]):
                    if not item:
                        continue
                    if isinstance(item, str) and item.startswith("Other: "):
                        other.append(item[7:])
                    else:
                        counts[item] = counts.get(item, 0) + 1
            out[qid] = {"type": "multiple_choice", "counts": counts, "other_values": other}

        elif qtype == "likert":
            counts = {}
            for v in vals:
                if v:
                    counts[v] = counts.get(v, 0) + 1
            out[qid] = {"type": "likert", "counts": counts}

        elif qtype in ("slider", "number", "rating"):
            nums = [float(v) for v in vals if v is not None]
            out[qid] = {
                "type": "numeric",
                "count": len(nums),
                "mean": round(sum(nums) / len(nums), 4) if nums else None,
                "min": min(nums) if nums else None,
                "max": max(nums) if nums else None,
                "values": nums,
            }

        else:
            out[qid] = {"type": "other", "values": [v for v in vals if v is not None]}

    return out
