import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


def _setup(data_dir: str | None) -> None:
    import db

    d = Path(data_dir or os.environ.get("QUORUMCALL_DATA_DIR", "."))
    d.mkdir(parents=True, exist_ok=True)
    os.environ["QUORUMCALL_DATA_DIR"] = str(d)
    db.init_db()


def cmd_serve(args):
    import uvicorn
    from rich.panel import Panel

    from _version import __version__
    from console import err_console
    from log import setup_logging
    from main import app

    host = args.host or os.environ.get("QUORUMCALL_HOST", "127.0.0.1")
    port = args.port or int(os.environ.get("QUORUMCALL_PORT", "8000"))
    _setup(args.data_dir)

    if "QUORUMCALL_BASE_URL" not in os.environ:
        os.environ["QUORUMCALL_BASE_URL"] = f"http://{host}:{port}"

    setup_logging()

    err_console.print(
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
    from console import console
    from questions import parse_questions
    from settings import base_url

    _setup(args.data_dir)
    import db

    path = Path(args.file)
    try:
        questions = parse_questions(path.read_bytes(), path.name)
    except (OSError, ValueError) as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)

    exp_dt = None
    if args.expires:
        try:
            exp_dt = datetime.fromisoformat(args.expires)
        except ValueError:
            console.print("[red]✗[/red] Invalid --expires — use ISO 8601 (e.g. 2026-12-31T23:59:59)")
            sys.exit(1)

    poll_id = db.create_poll(args.title, questions, exp_dt)
    url = f"{base_url()}/p/{poll_id}"

    console.print(f"[green]✓[/green] Created: [bold]{poll_id}[/bold]")
    console.print(f"  URL: {url}")


def cmd_list_polls(args):
    from rich.table import Table

    from console import console

    _setup(args.data_dir)
    import db

    rows = db.list_polls()

    if not rows:
        console.print("No polls.")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Title")
    table.add_column("Status", width=8)
    table.add_column("Expires")

    for r in rows:
        expired = db.is_expired(r)
        status = "EXPIRED" if expired else "active"
        style = "red" if expired else "green"
        exp_str = r["expires_at"] or "never"
        table.add_row(r["id"], r["title"], f"[{style}]{status}[/{style}]", exp_str)

    console.print(table)


def cmd_expire_poll(args):
    from console import console

    _setup(args.data_dir)
    import db

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

    p = sub.add_parser("add-poll", help="Create a poll from a JSON or TOML file")
    p.add_argument("--title", required=True)
    p.add_argument("--file", required=True, metavar="FILE", help="Path to a JSON or TOML questions file")
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
