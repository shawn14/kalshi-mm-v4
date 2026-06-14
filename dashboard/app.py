"""FastAPI dashboard — mobile-optimized, live MM state + research pipeline."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Kalshi MM v4", docs_url=None, redoc_url=None)
log = logging.getLogger(__name__)

_ENGINE = None
_PAPER_MODE = True

_REPO = Path(__file__).parent.parent
_FRONTEND = _REPO / "frontend" / "out"   # Next.js static export


def set_engine(engine: Any) -> None:
    global _ENGINE
    _ENGINE = engine


# ── Frontend static files — mounted AFTER all /api routes are defined ────────
def mount_frontend(application: FastAPI) -> None:
    """Call this after all API routes are registered."""
    if _FRONTEND.exists():
        # Serve Next.js static export; each page is its own directory index.html
        application.mount("/", StaticFiles(directory=str(_FRONTEND), html=True),
                          name="frontend")
        log.info("Frontend mounted from %s", _FRONTEND)
    else:
        log.warning("Frontend build not found at %s — run: cd frontend && npm run build", _FRONTEND)

        @application.get("/", response_class=HTMLResponse)
        async def no_frontend():
            return "<h1>Frontend not built</h1><p>cd frontend && npm run build</p>"


# ── MM State ──────────────────────────────────────────────────────────────────
@app.get("/api/mm/state")
async def mm_state():
    if _ENGINE is None:
        return {"status": "not_started"}
    return _ENGINE.state_snapshot()


@app.get("/api/mm/quotes")
async def mm_quotes():
    if _ENGINE is None:
        return {"orders": []}
    return {"orders": list(_ENGINE._active_orders.values())}


@app.get("/api/mm/inventory")
async def mm_inventory():
    if _ENGINE is None:
        return {"inventory": []}
    inv = []
    for ticker, i in _ENGINE._inventory.items():
        inv.append({
            "ticker": ticker,
            "net_yes": i.net_yes,
            "fills_yes": i.fills_yes,
            "fills_no": i.fills_no,
            "pnl_c": i.realized_pnl_c,
        })
    return {"inventory": sorted(inv, key=lambda x: abs(x["net_yes"]), reverse=True)}


# ── Kill switch ───────────────────────────────────────────────────────────────
@app.post("/api/mm/kill")
async def kill():
    if _ENGINE:
        await _ENGINE.arm_kill()
    return {"status": "killed"}


@app.post("/api/mm/resume")
async def resume():
    if _ENGINE:
        await _ENGINE.disarm_kill()
    return {"status": "resumed"}


# ── Go Live ───────────────────────────────────────────────────────────────────
@app.post("/api/mm/go-live")
async def go_live(body: dict = {}):
    global _PAPER_MODE
    if _ENGINE is None:
        raise HTTPException(500, "Engine not started")
    capital = float(body.get("capital_usd", 1000.0))
    _PAPER_MODE = False
    _ENGINE.dry_run = False
    _ENGINE._capital_usd = capital
    log.critical("GO LIVE: capital=$%.0f dry_run=False", capital)
    return {"status": "live", "capital_usd": capital}


@app.post("/api/mm/go-paper")
async def go_paper():
    global _PAPER_MODE
    _PAPER_MODE = True
    if _ENGINE:
        _ENGINE.dry_run = True
    return {"status": "paper"}


# ── Research ──────────────────────────────────────────────────────────────────
@app.get("/api/research/backtest")
async def backtest_results():
    out = Path("trading_log/backtest_results")
    if not out.exists():
        return {"results": []}
    results = []
    for f in sorted(out.glob("*.json"), reverse=True)[:100]:
        results.append(json.loads(f.read_text()))
    return {"results": results}


@app.post("/api/research/run-backtest")
async def run_backtest_endpoint():
    """Kick off a full backtest sweep in background."""
    async def _run():
        from research.backtest import sweep_all_series, save_results
        results = sweep_all_series()
        save_results(results)
        log.info("Backtest sweep complete: %d series", len(results))
    asyncio.create_task(_run())
    return {"status": "running"}


@app.get("/api/research/paper")
async def paper_summary():
    from research.paper_trade import paper_performance_summary
    return paper_performance_summary()


@app.get("/api/research/series-scores")
async def series_scores():
    try:
        from research.db import connect
        con = connect()
        rows = con.execute("""
            SELECT series, avg_spread_c, pct_in_zone, ev_estimate, rank, notes
            FROM series_scores
            ORDER BY rank ASC
            LIMIT 50
        """).fetchall()
        con.close()
        return {"scores": [{"series": r[0], "avg_spread_c": r[1],
                             "pct_in_zone": r[2], "ev_estimate": r[3],
                             "rank": r[4], "notes": r[5]} for r in rows]}
    except Exception:
        return {"scores": []}


# ── System ────────────────────────────────────────────────────────────────────
@app.get("/api/system/status")
async def system_status():
    from core.kalshi import KalshiClient
    return {
        "paper_mode": _PAPER_MODE,
        "engine_running": _ENGINE is not None and _ENGINE._running,
        "kill_switch": _ENGINE._kill if _ENGINE else False,
        "circuit_breaker": _ENGINE.breaker.tripped if _ENGINE else False,
        "ts": dt.datetime.utcnow().isoformat(),
    }


# Mount frontend last so /api/* routes take priority
mount_frontend(app)
