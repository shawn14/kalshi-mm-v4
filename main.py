"""Kalshi MM v4 — entry point.

Starts three concurrent tasks:
  1. WebSocket feed (KalshiWS.run)
  2. MM engine loop (MMEngine.run)
  3. FastAPI dashboard (uvicorn)

Usage:
  python main.py                     # paper mode (dry_run=True)
  python main.py --live              # real orders (set after startup, or use dashboard)
  python main.py --series KXMLBKS    # override series (comma-separated)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

DEFAULT_SERIES = ["KXMLBKS", "KXNBAPTS"]


async def run_all(args: argparse.Namespace) -> None:
    from core.kalshi import KalshiClient
    from core.kalshi_ws import KalshiWS
    from mm.engine import MMEngine
    from risk.limits import RiskLimits
    from dashboard.app import app, set_engine

    api_key = os.environ["KALSHI_API_KEY"]
    key_path = os.environ["KALSHI_PRIVATE_KEY_PATH"]

    client = KalshiClient(api_key, key_path)
    ws = KalshiWS(api_key, key_path)

    # Verify exchange is open
    status = await client.exchange_status()
    if not status.get("trading_active"):
        log.warning("Exchange trading_active=False — running in paper mode regardless")

    series = args.series.split(",") if args.series else DEFAULT_SERIES

    limits = RiskLimits(
        max_active_tickers=25,
        max_exposure_usd=args.capital * 0.50,  # max 50% of capital at risk
        max_daily_loss_usd=args.capital * 0.10,  # 10% daily stop
    )

    engine = MMEngine(
        client=client,
        ws=ws,
        series=series,
        limits=limits,
        base_hs=3.0,
        min_spread_c=7.0,
        game_tail_min=150.0,
        dry_run=not args.live,
    )
    set_engine(engine)

    log.info("Starting Kalshi MM v4 — series=%s dry_run=%s capital=$%.0f",
             series, engine.dry_run, args.capital)

    config = uvicorn.Config(
        app, host="0.0.0.0", port=8080,
        log_level="warning", access_log=False,
    )
    server = uvicorn.Server(config)

    await asyncio.gather(
        ws.run(),
        engine.run(),
        server.serve(),
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true",
                   help="Place real orders (default: paper)")
    p.add_argument("--series", default="",
                   help="Comma-separated series tickers (default: KXMLBKS,KXNBAPTS)")
    p.add_argument("--capital", type=float, default=1000.0,
                   help="Capital in USD (default: 1000)")
    args = p.parse_args()
    asyncio.run(run_all(args))


if __name__ == "__main__":
    main()
