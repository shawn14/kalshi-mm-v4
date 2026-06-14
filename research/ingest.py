"""Ingest JSONL.gz candle files from research/data/ into DuckDB.

Reads the same format ingest_daily.py writes on the VM:
  {ticker, series, candles: [{ts, ya_o, ya_c, yb_o, yb_c, vol}], ...}
"""
from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path

import pandas as pd

from research.db import connect, init_schema

log = logging.getLogger(__name__)

DATA_DIR = Path("data/candles")


def ingest_all(data_dir: Path = DATA_DIR) -> None:
    con = connect()
    init_schema(con)

    rows = []
    for series_dir in sorted(data_dir.iterdir()):
        if not series_dir.is_dir():
            continue
        series = series_dir.name
        for gz in sorted(series_dir.glob("*.jsonl.gz")):
            with gzip.open(gz) as f:
                for line in f:
                    try:
                        m = json.loads(line)
                    except Exception:
                        continue
                    ticker = m.get("ticker", "")
                    if not ticker:
                        continue
                    result = m.get("result")
                    open_time = m.get("open_time")
                    close_time = m.get("close_time")
                    title = m.get("title")
                    for c in m.get("candles", []):
                        ybo = c.get("yb_o")
                        if ybo is None:
                            continue
                        rows.append({
                            "ticker": ticker,
                            "series": series,
                            "ts": int(c["ts"]),
                            "open_time": open_time,
                            "close_time": close_time,
                            "result": result,
                            "yes_bid_open": float(ybo),
                            "yes_bid_close": float(c["yb_c"]) if c.get("yb_c") is not None else None,
                            "yes_ask_open": float(c["ya_o"]) if c.get("ya_o") is not None else None,
                            "yes_ask_close": float(c["ya_c"]) if c.get("ya_c") is not None else None,
                            "volume_usd": float(c.get("vol") or 0),
                            "title": title,
                        })
        log.info("  %s: %d rows so far", series, len(rows))

    log.info("Parsed %d rows — bulk loading into DuckDB via DataFrame...", len(rows))

    df = pd.DataFrame(rows)

    # DuckDB can read a registered DataFrame directly — much faster than executemany
    con.register("_stage", df)
    con.execute("""
        INSERT INTO candles
        SELECT ticker, series, ts, open_time, close_time, result,
               yes_bid_open, yes_bid_close, yes_ask_open, yes_ask_close,
               volume_usd, title
        FROM _stage
        WHERE NOT EXISTS (
            SELECT 1 FROM candles c
            WHERE c.ticker = _stage.ticker AND c.ts = _stage.ts
        )
    """)
    con.unregister("_stage")

    count = con.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    log.info("Ingest complete: %d total rows in candles table", count)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ingest_all()
