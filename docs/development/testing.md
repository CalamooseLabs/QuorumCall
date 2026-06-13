# Testing

## Running Tests

Tests run with pytest. The dev shell puts `src` on `PYTHONPATH` (also set via
`pyproject.toml`'s `pythonpath`), so no install is needed.

```bash
runtests                              # full suite with branch coverage (pytest --cov=src)
runtests tests/test_db.py             # a single file
runtests -k test_aggregate_radio      # a single test by name
```

`runtests` is a dev-shell shortcut for
`pytest --cov=src --cov-report=term-missing`.

### Integration tests

Tests marked `integration` (the full HTTP stack via a subprocess — slower) are
**deselected by default** (`addopts = "-m 'not integration'"`). Run them
explicitly:

```bash
pytest -m integration
```

## Coverage

The suite reports branch coverage over `src/` and runs close to 100%. New code
should come with tests that keep coverage from regressing.

```bash
runtests                              # prints a term-missing coverage report
```

## Test File Structure

Tests are flat under `tests/`, with shared fixtures in `conftest.py` (an
isolated temp database per test, env-var cleanup, a `TestClient`, and sample
questions).

| Test file | Covers |
|-----------|--------|
| `tests/test_db.py` | `src/db.py` |
| `tests/test_main.py` | `src/routes.py` + `src/results.py` (routes and aggregation, via the API) |
| `tests/test_cli.py` | `src/cli.py` |
| `tests/test_integration.py` | full HTTP stack via subprocess (marked `integration`) |
| `tests/test_misc.py` | settings, UI rendering, schemas, version |

## Commit Workflow

Commits are signed with a YubiKey. **Never run `git commit` directly.** Instead:

1. Write the commit message to `GIT_COMMIT_MSG` in the repo root.
2. Run `gcommit` (provided by the dev shell). It prints the message, prompts
   `[y/N]`, then runs `git commit -S -F GIT_COMMIT_MSG`.

```bash
gcommit
```
