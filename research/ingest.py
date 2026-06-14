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


def _parse_series(series_dir: Path) -> pd.DataFrame:
    """Parse all JSONL.gz files for one series into a DataFrame."""
    rows = []
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
                    rows.append((
                        ticker, series, int(c["ts"]),
                        open_time, close_time, result,
                        float(ybo),
                        float(c["yb_c"]) if c.get("yb_c") is not None else None,
                        float(c["ya_o"]) if c.get("ya_o") is not None else None,
                        float(c["ya_c"]) if c.get("ya_c") is not None else None,
                        float(c.get("vol") or 0),
                        title,
                    ))
    cols = ["ticker", "series", "ts", "open_time", "close_time", "result",
            "yes_bid_open", "yes_bid_close", "yes_ask_open", "yes_ask_close",
            "volume_usd", "title"]
    return pd.DataFrame(rows, columns=cols)


def ingest_all(data_dir: Path = DATA_DIR) -> None:
    con = connect()
    init_schema(con)

    total = 0
    for series_dir in sorted(data_dir.iterdir()):
        if not series_dir.is_dir():
            continue
        df = _parse_series(series_dir)
        if df.empty:
            continue

        # Deduplicate within the DataFrame (same market can appear in multiple files)
        df = df.drop_duplicates(subset=["ticker", "ts"])

        con.register("_stage", df)
        con.execute("""
            INSERT INTO candles
            SELECT ticker, series, ts, open_time, close_time, result,
                   yes_bid_open, yes_bid_close, yes_ask_open, yes_ask_close,
                   volume_usd, title
            FROM _stage
            ON CONFLICT DO NOTHING
        """)
        con.unregister("_stage")
        inserted = len(df)  # approximate (ON CONFLICT skips, rowcount unreliable)
        total += inserted
        log.info("  %-20s  +%d rows (df=%d)", series_dir.name, inserted, len(df))

    count = con.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    log.info("Ingest complete: %d total rows in candles table", count)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ingest_all()
