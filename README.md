# QuorumCall

Internal polling server. Create polls from a JSON file, share a link, collect responses, retrieve results as JSON.

- No logins — polls are identified by UUID
- Conditional branching — questions can route respondents based on their answers
- Browser UI served at `/p/{uuid}` — no frontend build step
- SQLite storage — single file, zero infrastructure
- NixOS service module included

---

## Quick start

```bash
nix develop          # enter the dev shell
runserver            # starts at http://127.0.0.1:8000 with data in ./data
```

Create your first poll:

```bash
quorumcall add-poll --title "Team survey" --file example_poll.json
# Created: a1b2c3d4-...
# URL:     http://127.0.0.1:8000/p/a1b2c3d4-...
```

Share the URL. Results:

```
GET /api/polls/{id}/results
```

---

## Installation

### Nix flake (recommended)

```nix
# flake.nix
inputs.quorumcall.url = "github:your-org/QuorumCall";

# run directly
nix run github:your-org/QuorumCall -- serve
```

### NixOS service

```nix
{ inputs, ... }: {
  imports = [ inputs.quorumcall.nixosModules.default ];

  services.quorumcall = {
    enable    = true;
    host      = "127.0.0.1";
    port      = 8000;
    baseUrl   = "https://polls.example.com";
    adminKeyFile = "/run/secrets/quorumcall-admin-key";  # optional
  };
}
```

`adminKeyFile` must be an EnvironmentFile with `QUORUMCALL_ADMIN_KEY=<secret>`.

### Pip

```bash
pip install ".[test]"   # with test deps
pip install .           # runtime only
```

---

## CLI

```
quorumcall serve       [--host HOST] [--port PORT] [--data-dir DIR]
quorumcall add-poll    --title TITLE --file questions.json [--expires ISO_DATETIME] [--data-dir DIR]
quorumcall list-polls  [--data-dir DIR]
quorumcall expire-poll POLL_ID [--data-dir DIR]
```

Dev-shell shortcuts:

```
runserver    # quorumcall serve with env-var defaults
runtests     # pytest --cov=quorumcall --cov-report=term-missing
```

---

## Creating a poll

POST `multipart/form-data` to `/api/polls`:

| Field            | Type   | Required |
|------------------|--------|----------|
| `title`          | string | yes      |
| `questions_file` | file   | yes      |
| `expires_at`     | string | no       |

`questions_file` accepts either JSON (`.json`) or TOML (`.toml`) — format is detected by file extension.

```bash
curl -X POST http://localhost:8000/api/polls \
  -F title="Exit survey" \
  -F questions_file=@questions.json \
  -F expires_at="2026-12-31T23:59:59"
```

Response:

```json
{
  "id": "a1b2c3d4-...",
  "title": "Exit survey",
  "poll_url": "http://localhost:8000/p/a1b2c3d4-..."
}
```

---

## Questions format

Both JSON and TOML are accepted. Format is detected by file extension.

**JSON:**

```json
{
  "questions": [
    {
      "id": "q1",
      "type": "radio",
      "title": "Are you satisfied with your experience?",
      "required": true,
      "options": ["Yes", "No", "Somewhat"],
      "next": { "Yes": "q3", "No": "q2", "Somewhat": "q2" }
    },
    {
      "id": "q2",
      "type": "long_answer",
      "title": "What could be improved?",
      "next": "q3"
    },
    {
      "id": "q3",
      "type": "rating",
      "title": "Rate your overall experience",
      "required": true,
      "rating_max": 5
    }
  ]
}
```

**TOML:**

```toml
[[questions]]
id = "q1"
type = "radio"
title = "Are you satisfied with your experience?"
required = true
options = ["Yes", "No", "Somewhat"]

[questions.next]
Yes = "q3"
No = "q2"
Somewhat = "q2"

[[questions]]
id = "q2"
type = "long_answer"
title = "What could be improved?"
next = "q3"

[[questions]]
id = "q3"
type = "rating"
title = "Rate your overall experience"
required = true
rating_max = 5
```

### `next` field (conditional branching)

| Value | Behaviour |
|-------|-----------|
| omitted / `null` | Next question in order; submit if last |
| `"q5"` | Always jump to `q5` |
| `{"Yes": "q3", "No": "q2"}` | Route by selected answer; falls back to sequential if answer not mapped |

### Supported question types

| Type | Description | Extra fields |
|------|-------------|--------------|
| `short_answer` | Single-line text | — |
| `long_answer` | Multi-line textarea | — |
| `number` | Numeric input | — |
| `email` | Email input | — |
| `phone` | Telephone input | — |
| `url` | URL input | — |
| `date` | Date picker | — |
| `time` | Time picker | — |
| `datetime` | Date + time picker | — |
| `radio` | Single choice | `options`, `include_other` |
| `checkbox` | Multiple choice | `options`, `include_other` |
| `dropdown` | Select menu | `options` |
| `true_false` | Yes / No (or custom labels) | `options` |
| `slider` | Range slider | `slider_min`, `slider_max`, `slider_step`, `slider_labels` |
| `rating` | 1–N star/number rating | `rating_max` |
| `likert` | Agreement scale | `likert_options` |

All types accept `description` (helper text shown below the question title) and `required` (boolean, default `false`).

`include_other: true` on `radio` or `checkbox` adds a free-text "Other…" option.

---

## API reference

Admin routes require `X-Admin-Key: <secret>` when `QUORUMCALL_ADMIN_KEY` is set.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | — | Service info |
| `GET` | `/p/{id}` | — | Browser poll UI |
| `POST` | `/api/polls` | admin | Create poll |
| `GET` | `/api/polls` | admin | List all polls |
| `GET` | `/api/polls/{id}` | — | Poll definition + questions |
| `POST` | `/api/polls/{id}/responses` | — | Submit a response |
| `GET` | `/api/polls/{id}/results` | admin | Aggregated results |
| `POST` | `/api/polls/{id}/expire` | admin | Manually close a poll |

### Results shape

Results are keyed by question ID. The `type` field tells you how to read the data:

```json
{
  "poll_id": "...",
  "total_responses": 42,
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
        { "question_id": "q1", "value": "M" },
        { "question_id": "q2", "value": 4 }
      ]
    }
  ]
}
```

| Result type | Fields |
|-------------|--------|
| `text` | `values: string[]` |
| `single_choice` | `counts: {option: n}`, `other_values: string[]` |
| `multiple_choice` | `counts: {option: n}`, `other_values: string[]` |
| `numeric` | `count`, `mean`, `min`, `max`, `values: number[]` |
| `likert` | `counts: {option: n}` |

`responses` lists every individual submission — useful for per-person data like shirt sizes or free-text answers.

---

## Branding & theming

Create a `settings.json` in the data directory to customise the poll UI:

```json
{
  "primary_color": "#0f766e",
  "brand_name": "Acme Corp",
  "brand_icon": "https://example.com/logo.png"
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `primary_color` | `#3b82f6` | Button and accent colour (any valid CSS colour) |
| `brand_name` | *(empty)* | Organisation name shown above each poll |
| `brand_icon` | *(empty)* | URL or data URI for a logo shown above each poll |

The brand bar is hidden when both `brand_name` and `brand_icon` are empty.

Point to a custom location with `QUORUMCALL_SETTINGS_FILE=/path/to/settings.json`.

### NixOS

```nix
services.quorumcall = {
  enable       = true;
  primaryColor = "#0f766e";
  brandName    = "Acme Corp";
  brandIcon    = "https://example.com/logo.png";
};
```

---

## Configuration

All settings are environment variables. CLI flags take precedence over env vars.

| Variable | Default | Description |
|----------|---------|-------------|
| `QUORUMCALL_HOST` | `127.0.0.1` | Bind address |
| `QUORUMCALL_PORT` | `8000` | Bind port |
| `QUORUMCALL_DATA_DIR` | `.` | Directory for `quorumcall.db` |
| `QUORUMCALL_BASE_URL` | `http://localhost:8000` | Prefix for share links |
| `QUORUMCALL_ADMIN_KEY` | *(unset — open)* | Required value of `X-Admin-Key` header |
| `QUORUMCALL_SETTINGS_FILE` | `{data_dir}/settings.json` | Path to branding/theme settings |

---

## Development

```bash
nix develop     # Python + all deps in PATH

runtests                          # full suite with branch coverage report
runtests tests/test_db.py         # single file
runtests -k test_aggregate_radio  # single test
```

Commits are signed with a YubiKey. Never run `git commit` directly — update `GIT_COMMIT_MSG` then:

```bash
./gcommit
```
