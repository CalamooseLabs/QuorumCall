"""Parsing and structural validation of an uploaded questions definition.

Shared by routes.create_poll (POST /api/polls) and cli.cmd_add_poll so both the
HTTP and CLI paths accept exactly the same files and reject the same malformed
ones. ``parse_questions`` raises a plain ``ValueError`` on any problem; each
caller maps that to its own error surface (HTTP 400 / a clean CLI message).
"""

import json
import tomllib
from pathlib import Path


def parse_questions(content: bytes, filename: str) -> list:
    """Parse + validate a questions file, returning the ``questions`` list.

    The format is chosen by extension (``.toml`` → TOML, else JSON). Raises
    ``ValueError`` if the file does not parse, lacks a ``questions`` list, or
    contains a question that is not an object with non-empty ``id`` and ``type``,
    or has duplicate ids.
    """
    ext = Path(filename or "").suffix.lower()
    try:
        data = tomllib.loads(content.decode()) if ext == ".toml" else json.loads(content)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"could not parse file: {e}")

    questions = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(questions, list):
        raise ValueError("file must contain a 'questions' list")

    seen: set = set()
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            raise ValueError(f"question {i + 1} must be an object")
        qid, qtype = q.get("id"), q.get("type")
        if not (isinstance(qid, str) and qid):
            raise ValueError(f"question {i + 1} is missing a non-empty 'id'")
        if not (isinstance(qtype, str) and qtype):
            raise ValueError(f"question {qid!r} is missing a non-empty 'type'")
        if qid in seen:
            raise ValueError(f"duplicate question id {qid!r}")
        seen.add(qid)

    return questions
