"""Paper trading — simulate fills against real market data without real orders.

Conservative fill model: a paper fill on side S at price P is credited only when
the real market's best bid on side S reaches or exceeds P (i.e., someone would
have taken our resting order). This matches how an actual maker order fills.

Paper fills are stored in DuckDB and tracked to settlement for Wilson validation.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid
from dataclasses import dataclass

import duckdb

from research.db import connect, init_schema

log = logging.getLogger(__name__)

MAKER_FEE_C = 1.0


@dataclass
class PaperFill:
    fill_id: str
    ticker: str
    series: str
    side: str
    price_c: float
    contracts: int
    filled_at: str
    result: str | None = None
    pnl_c: float | None = None


def record_paper_fill(ticker: str, series: str, side: str,
                      price_c: float, contracts: int = 1) -> str:
    con = connect()
    init_schema(con)
    fid = str(uuid.uuid4())
    now = dt.datetime.utcnow().isoformat()
    fee = MAKER_FEE_C * contracts
    con.execute("""
        INSERT INTO paper_fills
          (fill_id, ticker, series, side, price_c, contracts, filled_at, fee_c)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [fid, ticker, series, side, price_c, contracts, now, fee])
    con.close()
    log.info("PAPER FILL %s %s @%.0fc ×%d", ticker, side, price_c, contracts)
    return fid


def settle_paper_fills(con: duckdb.DuckDBPyConnection | None = None) -> int:
    """Settle any paper fills that now have a result in the candles table."""
    own_con = con is None
    if own_con:
        con = connect()
    settled = 0
    rows = con.execute("""
        SELECT pf.fill_id, pf.ticker, pf.side, pf.price_c, pf.contracts,
               c.result
        FROM paper_fills pf
        JOIN (
            SELECT ticker, result FROM candles
            WHERE result IS NOT NULL AND result != ''
        ) c ON c.ticker = pf.ticker
        WHERE pf.result IS NULL
    """).fetchall()

    for fill_id, ticker, side, price_c, contracts, result in rows:
        won = (side == "yes" and result == "yes") or (side == "no" and result == "no")
        pnl = ((100 - price_c) * contracts - MAKER_FEE_C * contracts if won
               else -price_c * contracts - MAKER_FEE_C * contracts)
        con.execute("""
            UPDATE paper_fills SET result=?, pnl_c=? WHERE fill_id=?
        """, [result, pnl, fill_id])
        settled += 1

    if own_con:
        con.close()
    return settled


def paper_performance_summary() -> dict:
    con = connect()
    row = con.execute("""
        SELECT
            COUNT(*) AS n,
            SUM(CASE WHEN pnl_c > 0 THEN 1 ELSE 0 END) AS wins,
            SUM(pnl_c) AS total_pnl,
            AVG(pnl_c) AS avg_pnl
        FROM paper_fills
        WHERE result IS NOT NULL
    """).fetchone()
    con.close()
    if not row or row[0] == 0:
        return {"n": 0, "win_rate": 0, "total_pnl_c": 0}
    n, wins, total, avg = row
    return {
        "n": n,
        "wins": wins,
        "win_rate": wins / n,
        "total_pnl_c": total,
        "avg_pnl_c": avg,
    }
