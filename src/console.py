"""Shared Rich consoles, so CLI and server output stay visually consistent.

Import these instead of constructing ``Console()`` ad hoc: ``console`` keeps
stdout clean for piping (user-facing output like tables and poll URLs), while
``err_console`` carries the startup banner, diagnostics, and logs on stderr.

Neither is given an explicit ``file=``; Rich resolves ``sys.stdout`` /
``sys.stderr`` at write time, so output still follows stream redirection (e.g.
pytest's ``capsys``).
"""

from rich.console import Console

# User-facing CLI output (tables, created-poll URLs). Resolves stdout lazily.
console = Console()

# Startup banner, diagnostics, and logging. Resolves stderr lazily.
err_console = Console(stderr=True)
