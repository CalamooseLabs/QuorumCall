# QuorumCall

Internal polling server. Create polls from a JSON or TOML file, share a link, collect responses, and retrieve results as JSON. The server also renders a browser UI for respondents.

- **No logins** — polls are public, identified by UUID
- **Conditional branching** — questions can route respondents based on their answers
- **Browser UI** served at `/p/{uuid}` — no frontend build step
- **SQLite storage** — a single file, zero infrastructure
- **NixOS service module** included

## Quick Start

```bash
nix develop          # enter the dev shell
runserver            # serves http://127.0.0.1:8000, data in ./data
```

Create your first poll and share the link:

```bash
quorumcall add-poll --title "Team survey" --file example_poll.json
# ✓ Created: a1b2c3d4-...
#   URL:     http://127.0.0.1:8000/p/a1b2c3d4-...
```

Results come back as JSON:

```bash
curl http://127.0.0.1:8000/api/polls/{id}/results
```

## Documentation

| Doc | Contents |
|-----|----------|
| [Installation & Setup](docs/install.md) | Dev environment, the CLI, running locally, pip, building |
| [Question Types & Format](docs/questions.md) | JSON/TOML format, all 17 question types, conditional branching |
| [API Reference](docs/api.md) | All routes, request/response shapes, results aggregation |
| [Configuration](docs/configuration.md) | Environment variables, branding & theming |
| [NixOS Module](docs/nixos.md) | Deploying as a NixOS service, every module option, privileged ports |
| [Architecture](docs/development/architecture.md) | Module layout, data layer, poll expiry, conditional branching |
| [Testing](docs/development/testing.md) | Running tests, coverage, the signed-commit workflow |
