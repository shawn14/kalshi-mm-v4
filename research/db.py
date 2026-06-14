"""DuckDB schema for research data — candles, backtest results, paper fills."""
from __future__ import annotations

import duckdb
from pathlib import Path

DB_PATH = Path("data/research.duckdb")


def connect(path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            ticker       VARCHAR NOT NULL,
            series       VARCHAR NOT NULL,
            ts           BIGINT NOT NULL,        -- Unix epoch seconds (candle open)
            open_time    TIMESTAMP,
            close_time   TIMESTAMP,
            result       VARCHAR,                -- 'yes' | 'no' | null
            yes_bid_open DOUBLE,
            yes_bid_close DOUBLE,
            yes_ask_open DOUBLE,
            yes_ask_close DOUBLE,
            volume_usd   DOUBLE,
            title        VARCHAR,
            PRIMARY KEY (ticker, ts)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS backtest_runs (
            run_id        VARCHAR NOT NULL,
            series        VARCHAR NOT NULL,
            ran_at        TIMESTAMP NOT NULL,
            n_markets     INTEGER,
            n_candles     INTEGER,
            half_spread_c DOUBLE,
            min_spread_c  DOUBLE,
            mid_lo        DOUBLE,
            mid_hi        DOUBLE,
            win_rate      DOUBLE,
            avg_ev_c      DOUBLE,
            total_pnl_c   DOUBLE,
            wilson_lb     DOUBLE,      -- 95% lower bound on win rate
            wilson_lb_h1  DOUBLE,      -- first half of date range
            wilson_lb_h2  DOUBLE,      -- second half
            n_trades      INTEGER,
            params        JSON,
            PRIMARY KEY (run_id)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS paper_fills (
            fill_id      VARCHAR NOT NULL,
            ticker       VARCHAR NOT NULL,
            series       VARCHAR NOT NULL,
            side         VARCHAR NOT NULL,        -- 'yes' | 'no'
            price_c      DOUBLE NOT NULL,
            contracts    INTEGER NOT NULL,
            filled_at    TIMESTAMP NOT NULL,
            result       VARCHAR,                  -- populated on settlement
            pnl_c        DOUBLE,
            fee_c        DOUBLE,
            strategy     VARCHAR DEFAULT 'mm_v4',
            PRIMARY KEY (fill_id)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS series_scores (
            series       VARCHAR NOT NULL,
            scored_at    TIMESTAMP NOT NULL,
            n_markets    INTEGER,
            avg_spread_c DOUBLE,
            pct_in_zone  DOUBLE,    -- % of candles with mid 40-60c
            avg_volume   DOUBLE,
            ev_estimate  DOUBLE,
            rank         INTEGER,
            notes        VARCHAR,
            PRIMARY KEY (series, scored_at)
        )
    """)
