"""Rich-based logging. Log records render to stderr via the shared err_console."""

import logging

from rich.logging import RichHandler

from console import err_console


def setup_logging() -> None:
    """Install a Rich log handler on the root logger (stderr, markup enabled)."""
    handler = RichHandler(
        console=err_console,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        log_time_format="[%H:%M:%S]",
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[handler],
        force=True,
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str = "quorumcall") -> logging.Logger:
    """Return the named application logger (defaults to ``quorumcall``)."""
    return logging.getLogger(name)
