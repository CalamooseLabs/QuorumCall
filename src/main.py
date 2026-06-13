"""FastAPI application assembly.

Creates the app, installs request-logging middleware, and mounts the routes
defined in routes.py. Route handlers live in routes.py; response aggregation in
results.py.
"""

import time

from fastapi import FastAPI, Request

from log import get_logger
from routes import router

app = FastAPI(title="QuorumCall", version="0.1.0")
log = get_logger()


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    """Log each request's method, path, status, and latency."""
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    sc = response.status_code
    color = "green" if sc < 400 else "yellow" if sc < 500 else "red"
    log.info(
        f"[cyan]{request.method:<6}[/cyan]  {request.url.path:<45} [{color}]{sc}[/{color}]  {ms:>5.0f}ms"
    )
    return response


app.include_router(router)
