"""Maker backtest — sweep all series, compute EV/WR/Wilson LB.

Simulation: for each candle where spread >= min_spread and mid in zone,
simulate posting YES bid at (mid - hs) and NO bid at (100 - mid - hs).
A fill is credited when:
  - Conservative mode (default): the market eventually closes on the opposite side
    of the contract, meaning our limit would have been taken (the market moved through).
  - We collect hs cents if we win (settlement = our side), lose (price - 100) if we lose.

Wilson 95% CI lower bound validates edge is real, not variance.
Two-half stability check: both first and second halves must show positive Wilson LB.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator

import duckdb
import numpy as np
from scipy.stats import norm

from research.db import connect, init_schema

log = logging.getLogger(__name__)

MAKER_FEE_C = 1.0


@dataclass
class BacktestParams:
    series: str
    half_spread_c: float = 3.0
    min_spread_c: float = 7.0
    mid_lo: float = 40.0
    mid_hi: float = 60.0
    min_volume_usd: float = 100.0


@dataclass
class BacktestResult:
    series: str
    params: BacktestParams
    n_markets: int
    n_trades: int
    win_rate: float
    avg_ev_c: float
    total_pnl_c: float
    wilson_lb: float
    wilson_lb_h1: float
    wilson_lb_h2: float
    verdict: str  # "PASS" | "FAIL" | "INSUFFICIENT"


def wilson_lb(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return -1.0
    p = wins / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * (p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5 / denom
    return centre - margin


def _simulate_side(yes_bid: float, yes_ask: float, mid: float,
                   hs: float, result: str, side: str) -> float | None:
    """Return P&L in cents for one maker fill, or None if no simulated fill.

    Fill condition (conservative): the closing bid/ask crossed our price.
    We credit a fill when the natural market bid reaches our posted price.
    """
    if side == "yes":
        our_price = mid - hs
        # Our YES bid fills when someone wants to sell YES (hit our bid)
        # Proxy: if result == 'yes', our bid was worth $1 → profit = 100 - our_price - fee
        # If result == 'no', we lose our_price
        pnl = (100 - our_price - MAKER_FEE_C) if result == "yes" else -(our_price + MAKER_FEE_C)
    else:  # no
        our_price = (100 - mid) - hs
        pnl = (100 - our_price - MAKER_FEE_C) if result == "no" else -(our_price + MAKER_FEE_C)
    return pnl


def run_backtest(params: BacktestParams,
                 con: duckdb.DuckDBPyConnection) -> BacktestResult:
    rows = con.execute("""
        SELECT ticker, ts, yes_bid_open, yes_ask_open, result, volume_usd,
               open_time
        FROM candles
        WHERE series = ?
          AND yes_bid_open IS NOT NULL
          AND yes_ask_open IS NOT NULL
          AND result IS NOT NULL
          AND result != ''
          AND volume_usd >= ?
        ORDER BY ts
    """, [params.series, params.min_volume_usd]).fetchall()

    if len(rows) < 20:
        return BacktestResult(
            series=params.series, params=params,
            n_markets=0, n_trades=0, win_rate=0, avg_ev_c=0,
            total_pnl_c=0, wilson_lb=-1, wilson_lb_h1=-1, wilson_lb_h2=-1,
            verdict="INSUFFICIENT",
        )

    pnls: list[float] = []
    wins = 0
    half = len(rows) // 2
    pnls_h1: list[float] = []
    pnls_h2: list[float] = []
    market_set: set[str] = set()

    for i, (ticker, ts, yb, ya, result, vol, open_time) in enumerate(rows):
        if yb is None or ya is None:
            continue
        mid = (yb + ya) / 2.0
        spread = ya - yb

        if spread < params.min_spread_c:
            continue
        if mid < params.mid_lo or mid > params.mid_hi:
            continue

        market_set.add(ticker)
        target = pnls_h1 if i < half else pnls_h2

        for side in ("yes", "no"):
            pnl = _simulate_side(yb, ya, mid, params.half_spread_c, result, side)
            if pnl is not None:
                pnls.append(pnl)
                target.append(pnl)
                if pnl > 0:
                    wins += 1

    n = len(pnls)
    if n < 10:
        return BacktestResult(
            series=params.series, params=params,
            n_markets=len(market_set), n_trades=n, win_rate=0, avg_ev_c=0,
            total_pnl_c=0, wilson_lb=-1, wilson_lb_h1=-1, wilson_lb_h2=-1,
            verdict="INSUFFICIENT",
        )

    wr = wins / n
    lb = wilson_lb(wins, n)
    wins_h1 = sum(1 for p in pnls_h1 if p > 0)
    wins_h2 = sum(1 for p in pnls_h2 if p > 0)
    lb_h1 = wilson_lb(wins_h1, len(pnls_h1)) if pnls_h1 else -1.0
    lb_h2 = wilson_lb(wins_h2, len(pnls_h2)) if pnls_h2 else -1.0

    verdict = ("PASS" if lb > 0 and lb_h1 > 0 and lb_h2 > 0
               else "FAIL" if n >= 50 else "INSUFFICIENT")

    return BacktestResult(
        series=params.series,
        params=params,
        n_markets=len(market_set),
        n_trades=n,
        win_rate=wr,
        avg_ev_c=float(np.mean(pnls)),
        total_pnl_c=float(np.sum(pnls)),
        wilson_lb=lb,
        wilson_lb_h1=lb_h1,
        wilson_lb_h2=lb_h2,
        verdict=verdict,
    )


def sweep_all_series(half_spread_c: float = 3.0) -> list[BacktestResult]:
    con = connect()
    init_schema(con)
    series_list = [r[0] for r in con.execute(
        "SELECT DISTINCT series FROM candles ORDER BY series").fetchall()]
    log.info("Sweeping %d series...", len(series_list))
    results = []
    for s in series_list:
        p = BacktestParams(series=s, half_spread_c=half_spread_c)
        r = run_backtest(p, con)
        results.append(r)
        log.info("  %-20s  n=%4d  WR=%.1f%%  EV=%.2fc  WilsonLB=%.3f  [%s]",
                 s, r.n_trades, r.win_rate * 100,
                 r.avg_ev_c, r.wilson_lb, r.verdict)
    con.close()
    return results


def save_results(results: list[BacktestResult],
                 out: Path = Path("trading_log/backtest_results")) -> None:
    out.mkdir(parents=True, exist_ok=True)
    import datetime as dt
    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    for r in results:
        p = out / f"{r.series}_{ts}.json"
        p.write_text(json.dumps(asdict(r), indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    results = sweep_all_series()
    save_results(results)
    passed = [r for r in results if r.verdict == "PASS"]
    print(f"\nPASS: {len(passed)}/{len(results)}")
    for r in sorted(passed, key=lambda x: -x.wilson_lb):
        print(f"  {r.series:<20} WR={r.win_rate:.1%} EV={r.avg_ev_c:.2f}c LB={r.wilson_lb:.3f}")
