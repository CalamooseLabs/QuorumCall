"""Aggregation of poll responses into per-question result summaries.

``aggregate()`` turns the raw stored answers into the ``results`` block of
``GET /api/polls/{id}/results``. The summary shape depends on the question
type — see docs/api.md for the full per-type field reference.
"""

import json


def aggregate(questions: list, responses: list) -> dict:
    """Summarise ``responses`` against the poll's ``questions``.

    Returns a dict keyed by question id; each value carries a ``type`` field
    (``text`` / ``single_choice`` / ``multiple_choice`` / ``likert`` /
    ``numeric`` / ``other``) describing how to read the rest of its fields.
    """
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
