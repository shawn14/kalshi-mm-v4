"""Maker backtest — sweep all series, compute calibration-based EV.

Simulation model:
  For each market (game), take the FIRST qualifying candle where:
    - mid ∈ [mid_lo, mid_hi] (quoting zone)
    - spread >= min_spread_c
    - volume >= min_volume_usd (at least some activity)

  Simulate buying YES at the natural market bid (yes_bid_open).
  P&L = (100 - bid - MAKER_FEE_C) if result='yes', else -(bid + MAKER_FEE_C)
  Break-even WR = (bid + MAKER_FEE_C) / 100

  This tests: does the historical bid price underestimate true win probability?
  If WR > breakeven → maker edge exists (market underprices YES at this level).
  If WR < breakeven → adverse selection dominates.

Wilson 95% CI lower bound on excess WR = WR - breakeven_wr.
Two-half stability: both halves must show positive excess WR.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np
import duckdb

from research.db import connect, init_schema

log = logging.getLogger(__name__)

MAKER_FEE_C = 1.0


@dataclass
class BacktestParams:
    series: str
    half_spread_c: float = 3.0   # hs we'd post (for reference)
    min_spread_c: float = 7.0    # only quote when natural spread is this wide
    mid_lo: float = 40.0
    mid_hi: float = 60.0
    min_volume_usd: float = 50.0


@dataclass
class BacktestResult:
    series: str
    params: BacktestParams
    n_markets: int
    n_trades: int
    win_rate: float
    avg_bid_c: float        # average fill price
    breakeven_wr: float     # avg bid / 100
    avg_ev_c: float
    total_pnl_c: float
    wilson_lb: float
    wilson_lb_h1: float
    wilson_lb_h2: float
    verdict: str            # "PASS" | "FAIL" | "INSUFFICIENT"
    avg_spread_c: float = 0.0
    pct_in_zone: float = 0.0


def wilson_lb(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return -1.0
    p = wins / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * (p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5 / denom
    return centre - margin


def run_backtest(params: BacktestParams,
                 con: duckdb.DuckDBPyConnection) -> BacktestResult:
    # One row per market: the FIRST candle with a real two-sided book in the quoting zone.
    # yes_bid_open >= 10 and yes_ask_open <= 90 filter out empty-book candles
    # (yb=0, ya=99 are "no market yet" states that give a misleading mid of 49.5c).
    rows = con.execute("""
        WITH first_qualifying AS (
            SELECT
                ticker,
                result,
                yes_bid_open,
                yes_ask_open,
                (yes_bid_open + yes_ask_open) / 2.0 AS mid,
                (yes_ask_open - yes_bid_open) AS spread,
                open_time,
                ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY ts ASC) AS rn
            FROM candles
            WHERE series = ?
              AND yes_bid_open >= 10
              AND yes_ask_open <= 90
              AND result IS NOT NULL
              AND result != ''
              AND volume_usd >= ?
              AND (yes_bid_open + yes_ask_open) / 2.0 BETWEEN ? AND ?
              AND (yes_ask_open - yes_bid_open) >= ?
              AND (yes_ask_open - yes_bid_open) <= 50
        )
        SELECT ticker, result, yes_bid_open, yes_ask_open, mid, spread, open_time
        FROM first_qualifying
        WHERE rn = 1
        ORDER BY open_time
    """, [params.series, params.min_volume_usd,
          params.mid_lo, params.mid_hi, params.min_spread_c]).fetchall()

    # Zone coverage stats (all candles, not just first-qualifying)
    zone_stats = con.execute("""
        SELECT
            AVG(yes_ask_open - yes_bid_open) AS avg_spread,
            SUM(CASE WHEN (yes_bid_open + yes_ask_open)/2.0 BETWEEN ? AND ? THEN 1 ELSE 0 END) * 1.0
                / COUNT(*) AS pct_in_zone
        FROM candles
        WHERE series = ?
          AND yes_bid_open IS NOT NULL AND yes_ask_open IS NOT NULL
    """, [params.mid_lo, params.mid_hi, params.series]).fetchone()
    avg_spread_c = float(zone_stats[0] or 0)
    pct_in_zone = float(zone_stats[1] or 0)

    if len(rows) < 10:
        return BacktestResult(
            series=params.series, params=params,
            n_markets=len(rows), n_trades=0, win_rate=0,
            avg_bid_c=0, breakeven_wr=0, avg_ev_c=0, total_pnl_c=0,
            wilson_lb=-1, wilson_lb_h1=-1, wilson_lb_h2=-1,
            verdict="INSUFFICIENT",
            avg_spread_c=avg_spread_c, pct_in_zone=pct_in_zone,
        )

    pnls: list[float] = []
    bids: list[float] = []
    breakevens: list[float] = []
    wins = 0
    half = len(rows) // 2
    pnls_h1: list[float] = []
    pnls_h2: list[float] = []
    wins_h1 = wins_h2 = 0

    for i, (ticker, result, yb, ya, mid, spread, open_time) in enumerate(rows):
        # Simulate YES fill at natural market bid
        our_price = yb
        be = (our_price + MAKER_FEE_C) / 100.0  # per-market break-even WR
        if result == "yes":
            pnl = 100 - our_price - MAKER_FEE_C
            wins += 1
            if i < half:
                wins_h1 += 1
            else:
                wins_h2 += 1
        else:
            pnl = -(our_price + MAKER_FEE_C)

        pnls.append(pnl)
        bids.append(our_price)
        breakevens.append(be)
        if i < half:
            pnls_h1.append(pnl)
        else:
            pnls_h2.append(pnl)

    n = len(pnls)
    wr = wins / n
    avg_bid = float(np.mean(bids))
    breakeven = float(np.mean(breakevens))

    # Wilson LB on WIN rate
    lb = wilson_lb(wins, n)
    lb_h1 = wilson_lb(wins_h1, len(pnls_h1)) if pnls_h1 else -1.0
    lb_h2 = wilson_lb(wins_h2, len(pnls_h2)) if pnls_h2 else -1.0

    # PASS: WR beats breakeven in both halves, confirmed by Wilson LB > breakeven
    def beats_breakeven(w: int, total: int) -> bool:
        if total == 0:
            return False
        be = breakeven
        # Wilson LB of win rate must exceed breakeven
        return wilson_lb(w, total) > be

    if n >= 50 and beats_breakeven(wins, n) and beats_breakeven(wins_h1, len(pnls_h1)) and beats_breakeven(wins_h2, len(pnls_h2)):
        verdict = "PASS"
    elif n >= 50:
        verdict = "FAIL"
    else:
        verdict = "INSUFFICIENT"

    return BacktestResult(
        series=params.series,
        params=params,
        n_markets=n,
        n_trades=n,
        win_rate=wr,
        avg_bid_c=avg_bid,
        breakeven_wr=breakeven,
        avg_ev_c=float(np.mean(pnls)),
        total_pnl_c=float(np.sum(pnls)),
        wilson_lb=lb,
        wilson_lb_h1=lb_h1,
        wilson_lb_h2=lb_h2,
        verdict=verdict,
        avg_spread_c=avg_spread_c,
        pct_in_zone=pct_in_zone,
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
        log.info(
            "  %-20s  n=%4d  WR=%.1f%%  BE=%.1f%%  EV=%.2fc  "
            "Spread=%.1fc  Zone=%.0f%%  LB=%.3f  [%s]",
            s, r.n_trades, r.win_rate * 100, r.breakeven_wr * 100,
            r.avg_ev_c, r.avg_spread_c, r.pct_in_zone * 100,
            r.wilson_lb, r.verdict,
        )
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
    failed = [r for r in results if r.verdict == "FAIL"]
    print(f"\n{'='*70}")
    print(f"PASS: {len(passed)}/{len(results)}  FAIL: {len(failed)}")
    print(f"{'='*70}")
    if passed:
        print("\nPASS (sorted by EV):")
        for r in sorted(passed, key=lambda x: -x.avg_ev_c):
            print(f"  {r.series:<20} n={r.n_trades:4d}  WR={r.win_rate:.1%}  "
                  f"BE={r.breakeven_wr:.1%}  EV={r.avg_ev_c:+.2f}c  "
                  f"Spread={r.avg_spread_c:.1f}c  Zone={r.pct_in_zone:.0%}")
    if failed:
        print("\nFAIL:")
        for r in sorted(failed, key=lambda x: -x.n_trades):
            print(f"  {r.series:<20} n={r.n_trades:4d}  WR={r.win_rate:.1%}  "
                  f"BE={r.breakeven_wr:.1%}  EV={r.avg_ev_c:+.2f}c")
