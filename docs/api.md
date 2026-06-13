# API Reference

All responses are JSON. Admin routes require the header `X-Admin-Key: <secret>`
when `QUORUMCALL_ADMIN_KEY` is set; if it is unset, admin routes are open. See
[Configuration](configuration.md) and the [NixOS module](nixos.md#admin-authentication)
for how to set the key.

## Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | — | Service info |
| `GET` | `/p/{id}` | — | Browser poll UI |
| `POST` | `/api/polls` | admin | Create a poll |
| `GET` | `/api/polls` | admin | List all polls |
| `GET` | `/api/polls/{id}` | — | Poll definition + questions |
| `POST` | `/api/polls/{id}/responses` | — | Submit a response |
| `GET` | `/api/polls/{id}/results` | admin | Aggregated results |
| `POST` | `/api/polls/{id}/expire` | admin | Manually close a poll |

## Creating a Poll

`POST /api/polls` as `multipart/form-data`:

| Field | Type | Required |
|-------|------|----------|
| `title` | string | yes |
| `questions_file` | file | yes |
| `expires_at` | string (ISO 8601) | no |

`questions_file` accepts JSON (`.json`) or TOML (`.toml`) — format is detected by
extension. See [Question Types & Format](questions.md).

```bash
curl -X POST http://localhost:8000/api/polls \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -F title="Exit survey" \
  -F questions_file=@questions.json \
  -F expires_at="2026-12-31T23:59:59"
```

```json
{
  "id": "a1b2c3d4-...",
  "title": "Exit survey",
  "poll_url": "http://localhost:8000/p/a1b2c3d4-..."
}
```

## Submitting a Response

`POST /api/polls/{id}/responses` with a JSON body of answers. Returns `410` if
the poll has expired.

```bash
curl -X POST http://localhost:8000/api/polls/{id}/responses \
  -H "Content-Type: application/json" \
  -d '{"answers": [{"question_id": "q1", "value": "Yes"}, {"question_id": "q3", "value": 4}]}'
```

```json
{ "response_id": "b2c3d4e5-..." }
```

## Results Shape

`GET /api/polls/{id}/results` returns aggregated results keyed by question id.
Each entry's `type` field tells you how to read the rest of its data.

```json
{
  "poll_id": "...",
  "title": "Exit survey",
  "is_expired": false,
  "total_responses": 42,
  "questions": [ ... ],
  "results": {
    "q1": { "type": "single_choice", "counts": {"Yes": 30, "No": 12}, "other_values": [] },
    "q2": { "type": "text", "values": ["Great product", "..."] },
    "q3": { "type": "numeric", "count": 42, "mean": 4.2, "min": 1, "max": 5, "values": [...] }
  },
  "responses": [
    {
      "id": "b2c3d4e5-...",
      "submitted_at": "2026-01-15T10:30:00",
      "answers": [
        { "question_id": "q1", "value": "Yes" },
        { "question_id": "q3", "value": 4 }
      ]
    }
  ]
}
```

The `results` summary depends on the question type:

| Result `type` | Question types | Fields |
|---------------|----------------|--------|
| `text` | text/email/phone/url/date/time/datetime | `values: string[]` |
| `single_choice` | `radio`, `dropdown`, `true_false` | `counts: {option: n}`, `other_values: string[]` |
| `multiple_choice` | `checkbox` | `counts: {option: n}`, `other_values: string[]` |
| `numeric` | `slider`, `number`, `rating` | `count`, `mean`, `min`, `max`, `values: number[]` |
| `likert` | `likert` | `counts: {option: n}` |
| `other` | anything unrecognized | `values` |

`responses` lists every individual submission — useful for per-person data such
as shirt sizes or free-text answers.
