"""Aggregation of poll responses into per-question result summaries.

``aggregate()`` turns the raw stored answers into the ``results`` block of
``GET /api/polls/{id}/results``. The summary shape depends on the question
type — see docs/api.md for the full per-type field reference.
"""

import json

# How the poll UI encodes a free-text "Other" choice (see ui.py). Kept here as a
# named constant so the prefix and its length stay in one place on the Python side.
OTHER_PREFIX = "Other: "


def _to_float(v):
    """Coerce a stored answer to float, or None if it is not numeric.

    Submissions are stored verbatim (the server accepts any value), so a
    non-numeric answer to a number/slider/rating question must not crash the
    results view — it is simply ignored.
    """
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def aggregate(questions: list, responses: list) -> dict:
    """Summarise ``responses`` against the poll's ``questions``.

    Returns a dict keyed by question id; each value carries a ``type`` field
    (``text`` / ``single_choice`` / ``multiple_choice`` / ``likert`` /
    ``numeric`` / ``other``) describing how to read the rest of its fields.
    """
    # Parse each response once, into {question_id: value} (first answer wins,
    # matching the previous first-match-then-break behaviour). This avoids
    # re-parsing every response's JSON once per question.
    parsed = []
    for resp in responses:
        by_qid: dict = {}
        for a in json.loads(resp["answers_json"]):
            by_qid.setdefault(a["question_id"], a["value"])
        parsed.append(by_qid)

    out = {}
    for q in questions:
        qid = q.get("id")
        if not qid:
            continue
        qtype = q.get("type")
        vals = [p[qid] for p in parsed if qid in p]

        if qtype in ("short_answer", "long_answer", "email", "phone", "url", "date", "time", "datetime"):
            out[qid] = {"type": "text", "values": [v for v in vals if v]}

        elif qtype in ("radio", "dropdown", "true_false"):
            counts: dict = {}
            other: list = []
            for v in vals:
                if v is None:
                    continue
                if isinstance(v, str) and v.startswith(OTHER_PREFIX):
                    other.append(v[len(OTHER_PREFIX):])
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
                    if isinstance(item, str) and item.startswith(OTHER_PREFIX):
                        other.append(item[len(OTHER_PREFIX):])
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
            nums = [n for v in vals if (n := _to_float(v)) is not None]
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
