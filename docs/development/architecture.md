# Architecture

QuorumCall is a small FastAPI + stdlib-sqlite3 server with a deliberately
minimal dependency footprint (FastAPI, uvicorn, python-multipart, rich).

## Module Layout

`src/` uses a **flat module layout** — there is no `quorumcall/` package
directory. Modules sit directly in `src/` and import each other absolutely
(`import db`, `from routes import router`). The distribution is still named
`quorumcall` and installs a `quorumcall` console script (entry point
`cli:main`); `src` is placed on `PYTHONPATH` for dev (shell hook) and tests
(pytest `pythonpath`).

```
src/
├── cli.py        # argparse entry point; sets QUORUMCALL_DATA_DIR, then starts uvicorn
├── main.py       # FastAPI app assembly + request-logging middleware; includes the router
├── routes.py     # all route handlers + request helpers (auth, expiry, file parsing)
├── results.py    # aggregate() — turns responses into the results summary
├── questions.py  # parse_questions() — parse + validate an uploaded JSON/TOML questions file
├── db.py         # sqlite3 via a contextmanager; _db_path() reads QUORUMCALL_DATA_DIR at call time; is_expired(row)
├── schemas.py    # Pydantic models (AnswerValue, SubmitRequest)
├── settings.py   # load_settings(); base_url(); inject_theme(template, settings); DEFAULTS dict
├── ui.py         # render_html(settings) — themed single-page poll-taking UI (vanilla JS)
├── builder.py    # render_builder_html(settings) — browser poll builder, served at GET /new
├── console.py    # shared Rich consoles (stdout / stderr)
├── log.py        # setup_logging() / get_logger() — Rich-based logging to stderr
└── _version.py   # __version__
```

> `ui.py` holds the poll-UI renderer. It is **not** named `html.py`: as a
> top-level module that would shadow the stdlib `html` module (breaking
> `html.escape`, which Starlette uses).

**App vs. routes.** `main.py` only assembles the app — it creates the
`FastAPI()` instance, installs the request-logging middleware, and mounts the
`APIRouter` defined in `routes.py`. Keeping handlers in `routes.py` (with the
small request helpers they share) and aggregation in `results.py` keeps each
file focused and lets the helpers be tested without spinning up the app.

## Data Layer

Two SQLite tables, with questions and answers stored as JSON blobs:

- `polls` — `id`, `title`, `created_at`, `expires_at`, `is_expired`, `questions_json`
- `responses` — `id`, `poll_id`, `submitted_at`, `answers_json`

`db.py` opens connections through a contextmanager and resolves the database
path (`QUORUMCALL_DATA_DIR/quorumcall.db`) at call time, so changing the env var
between calls (as the CLI and tests do) takes effect immediately.

## Poll Expiry

A poll is expired if `is_expired = 1` **or** `expires_at < now()`. The check
lives in `db.is_expired(row)` (naive timestamps are treated as UTC; a malformed
stored value is treated as not-expired so the poll stays readable); both
`routes._is_expired` and the CLI delegate to it. Submitting to an expired poll
returns `410`.

## Conditional Branching

Each question's `next` field is either a string (fixed next question id), a dict
(answer → question id map), or null (sequential). The branching is evaluated by
the browser UI's JavaScript (`ui.py`) as the respondent progresses; the server
stores whatever answers are submitted. See
[Question Types & Format](../questions.md#conditional-branching).

## Nix Layout

The Nix files mirror a thin-orchestration split (see also the
[NixOS Module](../nixos.md)):

| File | Role |
|------|------|
| `flake.nix` | Thin orchestration: inputs, then delegates to the files below |
| `build.nix` | The `buildPythonApplication` derivation; wired in via `pkgs.callPackage ./build.nix {}` and buildable standalone (`nix-build build.nix`) |
| `module.nix` | The NixOS module (`{ config, lib, pkgs, ... }`); `package` defaults to `pkgs.callPackage ./build.nix {}`, so it has no dependency on flake `self` |
| `shell.nix` | The dev shell + helper scripts (`quorumcall`, `runserver`, `runtests`, `gcommit`) |
