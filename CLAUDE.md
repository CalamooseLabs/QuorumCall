# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

QuorumCall is an internal company polling server. Key constraints from the owner:

- **No user logins** — polls are public by UUID
- **Python, minimal dependencies** — FastAPI + uvicorn + python-multipart + stdlib sqlite3
- **Nix-first** — must be packageable via `flake.nix` and runnable as a NixOS service
- **Signed commits only** — owner uses a YubiKey; never commit directly. Write commit messages to `GIT_COMMIT_MSG` and tell the user to run `gcommit` (provided by the dev shell)
- **Results as JSON** — all API responses are JSON; the server also serves a minimal browser UI for respondents

## Dev Environment

Uses Nix + direnv. Enter the shell first — it provides Python with all runtime and test deps.

```bash
nix develop                      # enter dev shell (direnv does this automatically)

# Run the server
quorumcall serve --host 127.0.0.1 --port 8000 --data-dir ./data

# Manage polls from the CLI
quorumcall add-poll --title "My Poll" --file questions.json [--expires "2026-12-31T23:59:59"]
quorumcall list-polls
quorumcall expire-poll <uuid>

# Tests
pytest --cov=quorumcall --cov-report=term-missing   # full suite with branch coverage
pytest tests/test_db.py                              # single file
pytest -k test_aggregate_radio_other                 # single test
```

## Planned Architecture

```
quorumcall/
├── cli.py       # argparse entry point; sets QUORUMCALL_DATA_DIR env var then starts uvicorn
├── db.py        # sqlite3 via contextmanager; _db_path() reads QUORUMCALL_DATA_DIR at call time
├── schemas.py   # Pydantic: AnswerValue, SubmitResponse (minimal — dicts used elsewhere)
├── main.py      # FastAPI app + all routes + _aggregate() for results
├── settings.py  # load_settings() — reads settings.json; DEFAULTS dict
└── html.py      # render_html(settings) — themed single-page poll UI (vanilla JS)
```

**Data layer**: Two SQLite tables — `polls` (id, title, created_at, expires_at, is_expired, questions_json) and `responses` (id, poll_id, submitted_at, answers_json). Questions and answers are stored as JSON blobs.

**Poll expiry**: A poll is expired if `is_expired=1` OR `expires_at < now()`. The `_is_expired(row)` helper in `main.py` centralises this check.

**Conditional branching**: Each question's `next` field is either a string (fixed next question ID), a dict (answer→question ID map), or null (sequential). The frontend JS and `getNextId()` implement the same logic.

## API Routes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/polls` | admin | Create poll (multipart: title, questions_file, expires_at?) |
| GET | `/api/polls` | admin | List all polls |
| GET | `/api/polls/{id}` | public | Poll definition (questions JSON) |
| POST | `/api/polls/{id}/responses` | public | Submit a response |
| GET | `/api/polls/{id}/results` | admin | Aggregated results JSON |
| POST | `/api/polls/{id}/expire` | admin | Manually expire a poll |
| GET | `/p/{id}` | public | Browser UI (serves `POLL_HTML`) |

Admin routes check `X-Admin-Key` header against `QUORUMCALL_ADMIN_KEY` env var; if the env var is unset, admin routes are open.

## Question Types

`short_answer`, `long_answer`, `number`, `email`, `phone`, `url`, `date`, `time`, `datetime`, `radio`, `checkbox`, `dropdown`, `true_false`, `slider`, `rating`, `likert`

Radio and checkbox support `include_other: true` to add a free-text "Other" option. Slider supports `slider_min/max/step/labels`. Rating uses `rating_max`. Likert uses `likert_options` list.

## Questions JSON Format

```json
{
  "questions": [
    {
      "id": "q1",
      "type": "radio",
      "title": "Are you satisfied?",
      "required": true,
      "options": ["Yes", "No"],
      "next": { "Yes": "q3", "No": "q2" }
    },
    { "id": "q2", "type": "long_answer", "title": "What went wrong?", "next": "q3" },
    { "id": "q3", "type": "short_answer", "title": "Final thoughts?" }
  ]
}
```

`next` is omitted → sequential. `next` is `"__end__"` or `null` → submit immediately after this question.

## Nix Package

`flake.nix` must export:
- `packages.x86_64-linux.default` — the `buildPythonApplication` derivation
- `nixosModules.default` — a NixOS module with `services.quorumcall.{enable, host, port, dataDir}` options, running as a systemd service with `DynamicUser = true`

The NixOS module references the package via `self.packages.${pkgs.stdenv.hostPlatform.system}.default`.

## Commit Workflow

Never run `git commit`. Instead:

1. Write the commit message to `GIT_COMMIT_MSG` in the repo root
2. Tell the user to run `gcommit` (a `writeShellScriptBin` in `shell.nix` — available in the dev shell)

`gcommit` prints the message, prompts `[y/N]`, then runs `git commit -S -F GIT_COMMIT_MSG`.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `QUORUMCALL_DATA_DIR` | `.` | Directory for `quorumcall.db` |
| `QUORUMCALL_BASE_URL` | `http://localhost:8000` | Prefix for poll share links |
| `QUORUMCALL_HOST` | `127.0.0.1` | Bind host |
| `QUORUMCALL_PORT` | `8000` | Bind port |
| `QUORUMCALL_ADMIN_KEY` | `` (open) | If set, required as `X-Admin-Key` header for admin routes |
