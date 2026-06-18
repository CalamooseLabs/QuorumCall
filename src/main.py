"""FastAPI application assembly.

Creates the app, installs request-logging middleware, and mounts the routes
defined in routes.py. Route handlers live in routes.py; response aggregation in
results.py.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from rich.markup import escape

import db
from _version import __version__
from log import get_logger
from routes import router

log = get_logger()

# Reject obviously oversized request bodies before they are read into memory.
MAX_BODY_BYTES = 1_048_576  # 1 MiB


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent (CREATE TABLE IF NOT EXISTS), so it is safe on every startup and
    # makes `main:app` self-sufficient regardless of how it is launched.
    db.init_db()
    yield


app = FastAPI(title="QuorumCall", version=__version__, lifespan=lifespan)


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    """Cap body size, then log each request's method, path, status, and latency."""
    t0 = time.perf_counter()
    cl = request.headers.get("content-length")
    if cl is not None and cl.isdigit() and int(cl) > MAX_BODY_BYTES:
        response = JSONResponse({"detail": "Request body too large"}, status_code=413)
    else:
        response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    sc = response.status_code
    color = "green" if sc < 400 else "yellow" if sc < 500 else "red"
    # escape() the path: it is attacker-controlled and the log handler renders
    # Rich markup, so an unescaped "[...]" could raise MarkupError (→ 500) or
    # spoof log output.
    log.info(
        f"[cyan]{request.method:<6}[/cyan]  {escape(request.url.path):<45} [{color}]{sc}[/{color}]  {ms:>5.0f}ms"
    )
    return response


app.include_router(router)
