"""Ingest JSONL.gz candle files from research/data/ into DuckDB.

Reads the same format ingest_daily.py writes on the VM:
  {ticker, series, candles: [{ts, ya_o, ya_c, yb_o, yb_c, vol}], ...}

Run once to backfill from existing files on VM, then daily via cron.
"""
from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path

import duckdb

from research.db import connect, init_schema

log = logging.getLogger(__name__)

DATA_DIR = Path("data/candles")   # mirrors VM's research/data/


def ingest_file(con: duckdb.DuckDBPyConnection, path: Path) -> int:
    rows = []
    series = path.parent.name
    with gzip.open(path) as f:
        for line in f:
            m = json.loads(line)
            ticker = m.get("ticker", "")
            if not ticker:
                continue
            for c in m.get("candles", []):
                ybo = c.get("yb_o")
                ybc = c.get("yb_c")
                yao = c.get("ya_o")
                yac = c.get("ya_c")
                if ybo is None:
                    continue
                rows.append({
                    "ticker": ticker,
                    "series": series,
                    "ts": int(c["ts"]),
                    "open_time": m.get("open_time"),
                    "close_time": m.get("close_time"),
                    "result": m.get("result"),
                    "yes_bid_open": float(ybo),
                    "yes_bid_close": float(ybc) if ybc is not None else None,
                    "yes_ask_open": float(yao) if yao is not None else None,
                    "yes_ask_close": float(yac) if yac is not None else None,
                    "volume_usd": float(c.get("vol", 0) or 0),
                    "title": m.get("title"),
                })
    if not rows:
        return 0
    con.executemany("""
        INSERT OR IGNORE INTO candles
          (ticker, series, ts, open_time, close_time, result,
           yes_bid_open, yes_bid_close, yes_ask_open, yes_ask_close,
           volume_usd, title)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [[r["ticker"], r["series"], r["ts"], r["open_time"], r["close_time"],
           r["result"], r["yes_bid_open"], r["yes_bid_close"],
           r["yes_ask_open"], r["yes_ask_close"], r["volume_usd"], r["title"]]
          for r in rows])
    return len(rows)


def ingest_all(data_dir: Path = DATA_DIR) -> None:
    con = connect()
    init_schema(con)
    total = 0
    for series_dir in sorted(data_dir.iterdir()):
        if not series_dir.is_dir():
            continue
        for gz in sorted(series_dir.glob("*.jsonl.gz")):
            n = ingest_file(con, gz)
            total += n
            if n:
                log.info("  %s/%s → %d rows", series_dir.name, gz.name, n)
    log.info("Ingest complete: %d total candle rows", total)
    con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ingest_all()
