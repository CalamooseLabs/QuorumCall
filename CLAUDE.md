# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

QuorumCall is an internal company polling server. Key constraints from the owner:

- **No user logins** — polls are public by UUID
- **Python, minimal dependencies** — FastAPI + uvicorn + python-multipart + rich + stdlib sqlite3
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
pytest --cov=src --cov-report=term-missing          # full suite with branch coverage
pytest tests/test_db.py                              # single file
pytest -k test_aggregate_radio_other                 # single test
```

## Architecture

Flat module layout under `src/` — there is **no** `quorumcall` package directory. Modules sit
directly in `src/` and import each other absolutely (`import db`, `from ui import render_html`).
The distribution is still named `quorumcall` and still installs a `quorumcall` console script
(entry point `cli:main`); `src` is put on `PYTHONPATH` for dev (shell hook) and tests (pytest
`pythonpath`).

```
src/
├── cli.py       # argparse entry point; sets QUORUMCALL_DATA_DIR env var then starts uvicorn
├── main.py      # FastAPI app assembly + request-logging middleware; includes routes.router
├── routes.py    # all route handlers + request helpers (_require_admin, _is_expired, _poll_or_404, _parse_questions_file)
├── results.py   # aggregate() — builds the /results summary from responses
├── db.py        # sqlite3 via contextmanager; _db_path() reads QUORUMCALL_DATA_DIR at call time
├── schemas.py   # Pydantic: AnswerValue, SubmitRequest (minimal — dicts used elsewhere)
├── settings.py  # load_settings() — reads settings.json; DEFAULTS dict
├── ui.py        # render_html(settings) — themed single-page poll UI (vanilla JS)
├── console.py   # shared Rich consoles (stdout / stderr)
├── log.py       # setup_logging() / get_logger() — Rich-based logging
└── _version.py  # __version__
```

User-facing documentation lives in `docs/` (a lean `README.md` plus
`docs/{install,questions,api,configuration,nixos}.md` and
`docs/development/{architecture,testing}.md`). Keep it in sync when behaviour changes.

> `ui.py` holds the poll-UI renderer. It is **not** named `html.py`: as a top-level module that
> would shadow the stdlib `html` module (breaking `html.escape`, which Starlette uses, in dev, and
> breaking our own `from ui import render_html` once installed).

**Data layer**: Two SQLite tables — `polls` (id, title, created_at, expires_at, is_expired, questions_json) and `responses` (id, poll_id, submitted_at, answers_json). Questions and answers are stored as JSON blobs.

**Poll expiry**: A poll is expired if `is_expired=1` OR `expires_at < now()`. The `_is_expired(row)` helper in `routes.py` centralises this check.

**Conditional branching**: Each question's `next` field is either a string (fixed next question ID), a dict (answer→question ID map), or null/omitted (next question in order). Branching is **frontend-only** — the JS function `nextId()` in `ui.py` evaluates it; the server just stores whatever answers it receives.

## API Routes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/polls` | admin | Create poll (multipart: title, questions_file, expires_at?) |
| GET | `/api/polls` | admin | List all polls |
| GET | `/api/polls/{id}` | public | Poll definition (questions JSON) |
| POST | `/api/polls/{id}/responses` | public | Submit a response |
| GET | `/api/polls/{id}/results` | admin | Aggregated results JSON |
| POST | `/api/polls/{id}/expire` | admin | Manually expire a poll |
| GET | `/p/{id}` | public | Browser UI (renders the poll page via `ui.render_html`) |

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

`next` omitted or `null` → go to the next question in order, submitting after the last one. A string jumps to that question ID; a dict routes by the selected answer (falling back to the next question in order when unmapped).

## Nix Package

The Nix build is split across files (mirrors CalamooseLabs/OpenReturn):
- `flake.nix` — thin orchestration. `packages.x86_64-linux.default` / `apps.default`
  via `pkgs.callPackage ./build.nix {}`; `devShells.default` via `import ./shell.nix`;
  `nixosModules.default = import ./module.nix`.
- `build.nix` — `{ pkgs ? import <nixpkgs> {} }: buildPythonApplication {...}`;
  buildable standalone (`nix-build build.nix`).
- `module.nix` — the NixOS module (`{ config, lib, pkgs, ... }`). Its `package`
  option defaults to `pkgs.callPackage ./build.nix {}`, so the module has **no**
  dependency on flake `self` and can be imported standalone.

`services.quorumcall` options: `enable, package, host, port, user, group, runAsRoot,
openFirewall, dataDir, baseUrl, adminKey, adminKeyFile, primaryColor, brandName,
brandIcon`.

The service runs as a dedicated **static system user** (`user`/`group`, default
`quorumcall`) with a hardened unit (`ProtectSystem=strict`, `ReadWritePaths=[dataDir]`,
`ProtectHome`, `PrivateTmp`); `StateDirectory` manages `dataDir`, and the CLI is put on
the host PATH (`environment.systemPackages`) for poll management. Behaviours to keep
working when editing the module:

- **Privileged ports.** `port` is `lib.types.port`. When `port` is 1-1023 and
  `runAsRoot` is false, the unit gets `AmbientCapabilities`/`CapabilityBoundingSet =
  "CAP_NET_BIND_SERVICE"` so the service user can bind it (e.g. port 80). Otherwise
  (port 0 or ≥ 1024, non-root) it sets `NoNewPrivileges = true`. Root binds any port
  natively, so neither applies under `runAsRoot`.
- **`runAsRoot`.** When true, runs as `root` (no service user is created); the
  hardening and `StateDirectory` still apply.
- **Secrets.** `adminKey` (literal — world-readable in the store, emits a build
  warning) and `adminKeyFile` (EnvironmentFile, preferred) are mutually exclusive
  (assertion).

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
