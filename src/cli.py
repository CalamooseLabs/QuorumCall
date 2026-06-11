import argparse
import json
import os
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path


def _setup(data_dir: str | None) -> None:
    import db

    d = Path(data_dir or os.environ.get("QUORUMCALL_DATA_DIR", "."))
    d.mkdir(parents=True, exist_ok=True)
    os.environ["QUORUMCALL_DATA_DIR"] = str(d)
    db.init_db()


def cmd_serve(args):
    import uvicorn
    from rich.console import Console
    from rich.panel import Panel

    from _version import __version__
    from log import setup_logging
    from main import app

    host = args.host or os.environ.get("QUORUMCALL_HOST", "127.0.0.1")
    port = args.port or int(os.environ.get("QUORUMCALL_PORT", "8000"))
    _setup(args.data_dir)

    if "QUORUMCALL_BASE_URL" not in os.environ:
        os.environ["QUORUMCALL_BASE_URL"] = f"http://{host}:{port}"

    setup_logging()

    Console(stderr=True).print(
        Panel.fit(
            f"[bold blue]QuorumCall[/bold blue]  [dim]v{__version__}[/dim]\n"
            f"[dim]url [/dim]  http://{host}:{port}\n"
            f"[dim]data[/dim]  {os.environ['QUORUMCALL_DATA_DIR']}",
            border_style="blue",
            padding=(0, 2),
        )
    )

    uvicorn.run(app, host=host, port=port, log_config=None, access_log=False)


def cmd_add_poll(args):
    from rich.console import Console

    _setup(args.data_dir)
    import db

    path = Path(args.file)
    if path.suffix.lower() == ".toml":
        with open(path, "rb") as f:
            definition = tomllib.load(f)
    else:
        with open(path) as f:
            definition = json.load(f)

    questions = definition["questions"]
    exp_dt = None
    if args.expires:
        exp_dt = datetime.fromisoformat(args.expires)

    poll_id = db.create_poll(args.title, questions, exp_dt)
    base_url = os.environ.get("QUORUMCALL_BASE_URL", "http://localhost:8000")
    url = f"{base_url}/p/{poll_id}"

    console = Console(file=sys.stdout)
    console.print(f"[green]✓[/green] Created: [bold]{poll_id}[/bold]")
    console.print(f"  URL: {url}")


def cmd_list_polls(args):
    from rich.console import Console
    from rich.table import Table

    _setup(args.data_dir)
    import db

    rows = db.list_polls()
    console = Console(file=sys.stdout)

    if not rows:
        console.print("No polls.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Title")
    table.add_column("Status", width=8)
    table.add_column("Expires")

    for r in rows:
        expired = bool(r["is_expired"])
        if not expired and r["expires_at"]:
            exp = datetime.fromisoformat(r["expires_at"])
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            expired = datetime.now(timezone.utc) > exp
        status = "EXPIRED" if expired else "active"
        style = "red" if expired else "green"
        exp_str = r["expires_at"] or "never"
        table.add_row(r["id"], r["title"], f"[{style}]{status}[/{style}]", exp_str)

    console.print(table)


def cmd_expire_poll(args):
    from rich.console import Console

    _setup(args.data_dir)
    import db

    console = Console(file=sys.stdout)
    if db.expire_poll(args.poll_id):
        console.print(f"[green]✓[/green] Expired: {args.poll_id}")
    else:
        console.print(f"[red]✗[/red] Not found: {args.poll_id}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(prog="quorumcall", description="QuorumCall polling server")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("serve", help="Start the HTTP server")
    p.add_argument("--host", help="Bind host (default: 127.0.0.1)")
    p.add_argument("--port", type=int, help="Bind port (default: 8000)")
    p.add_argument("--data-dir", metavar="DIR", help="Data directory for quorumcall.db")

    p = sub.add_parser("add-poll", help="Create a poll from a JSON file")
    p.add_argument("--title", required=True)
    p.add_argument("--file", required=True, metavar="questions.json")
    p.add_argument("--expires", metavar="ISO_DATETIME", help="e.g. 2026-12-31T23:59:59")
    p.add_argument("--data-dir", metavar="DIR")

    p = sub.add_parser("list-polls", help="List all polls")
    p.add_argument("--data-dir", metavar="DIR")

    p = sub.add_parser("expire-poll", help="Manually expire a poll")
    p.add_argument("poll_id", help="UUID of the poll to expire")
    p.add_argument("--data-dir", metavar="DIR")

    args = parser.parse_args()
    {
        "serve": cmd_serve,
        "add-poll": cmd_add_poll,
        "list-polls": cmd_list_polls,
        "expire-poll": cmd_expire_poll,
    }[args.command](args)


if __name__ == "__main__":
    main()
