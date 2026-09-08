"""
PJM vs MISO Energy Arbitrage Oracle — VPS entrypoint (uvicorn).
Mounts FastMCP Streamable HTTP on /mcp, health/metrics endpoints, public/ static.
"""

import os
import sys
import time
from pathlib import Path

from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_oracle_server import mcp, ORACLE_ADDRESS, START_TIME, VERSION, PUBLIC_ENDPOINT

# Build the MCP Starlette app (routes: /mcp)
app = mcp.streamable_http_app()

# ── Health check ──

async def health(request):
    return JSONResponse({
        "status": "ok",
        "service": "PJM-vs-MISO-Energy-Arbitrage-Oracle",
        "version": VERSION,
        "uptime_seconds": int(time.time() - START_TIME),
        "endpoint": PUBLIC_ENDPOINT,
        "contract": ORACLE_ADDRESS,
    })

# ── Metrics (Prometheus text format, minimal) ──

async def metrics(request):
    uptime = int(time.time() - START_TIME)
    body = "\n".join([
        '# HELP oracle_uptime_seconds Oracle process uptime.',
        '# TYPE oracle_uptime_seconds gauge',
        f'oracle_uptime_seconds {uptime}',
        '# HELP oracle_info Static info about the oracle.',
        '# TYPE oracle_info gauge',
        f'oracle_info{{address="{ORACLE_ADDRESS}",chain="arbitrum-one",version="{VERSION}"}} 1',
    ]) + "\n"
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4")

# Append routes: /health and /metrics before static fallback
app.routes.append(Route("/health", endpoint=health))
app.routes.append(Route("/metrics", endpoint=metrics))

# Serve static files (x402.json, frame.html, etc.) at root as fallback
public_dir = Path(__file__).resolve().parent / "public"
app.routes.append(Mount("/", StaticFiles(directory=str(public_dir), html=True), name="public"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
