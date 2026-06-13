# Installation & Setup

## Prerequisites

- [Nix](https://nixos.org/download/) with flakes enabled (recommended), or Python ≥ 3.11
- `x86_64-linux` — the flake is hardcoded to this platform; other architectures require editing `flake.nix`

## Development Environment

QuorumCall uses Nix + direnv. Enter the dev shell — it provides Python with all runtime and test dependencies, plus the helper scripts below.

```bash
nix develop          # enter the dev shell (direnv does this automatically)
```

All commands below assume the dev shell is active. The shell exports
`PYTHONPATH=$PWD/src` so the flat modules import without an install.

### Dev-shell shortcuts

| Command | Runs |
|---------|------|
| `quorumcall` | The CLI (`python -m cli`) |
| `runserver` | `quorumcall serve` with env-var defaults, data in `./data` |
| `runtests` | `pytest --cov=src --cov-report=term-missing` |
| `gcommit` | Review and sign-commit `GIT_COMMIT_MSG` (see [Testing](development/testing.md#commit-workflow)) |

## CLI

```
quorumcall serve       [--host HOST] [--port PORT] [--data-dir DIR]
quorumcall add-poll    --title TITLE --file questions.json [--expires ISO_DATETIME] [--data-dir DIR]
quorumcall list-polls  [--data-dir DIR]
quorumcall expire-poll POLL_ID [--data-dir DIR]
```

- `serve` starts the HTTP server. Flags override the `QUORUMCALL_HOST` / `QUORUMCALL_PORT` / `QUORUMCALL_DATA_DIR` environment variables (see [Configuration](configuration.md)).
- `add-poll` creates a poll from a `.json` or `.toml` file (format is detected by extension — see [Question Types & Format](questions.md)) and prints the share URL.
- `list-polls` prints a table of every poll with its status and expiry.
- `expire-poll` closes a poll immediately.

```bash
quorumcall add-poll --title "Exit survey" --file questions.toml --expires "2026-12-31T23:59:59"
quorumcall list-polls
quorumcall expire-poll a1b2c3d4-...
```

## Running the Server

```bash
# Default: 127.0.0.1:8000, database in ./data/quorumcall.db
runserver

# Or call the CLI directly
quorumcall serve --host 0.0.0.0 --port 9000 --data-dir /srv/polls
```

The database (`quorumcall.db`) is created automatically in the data directory on
first use. To deploy as a managed system service, see the [NixOS Module](nixos.md).

## Installing with Nix

```nix
# flake.nix
inputs.quorumcall.url = "github:your-org/QuorumCall";
```

```bash
# run without installing
nix run github:your-org/QuorumCall -- serve

# build the package (produces result/bin/quorumcall)
nix build
```

## Installing with pip

```bash
pip install ".[test]"   # with test dependencies
pip install .           # runtime only
```
