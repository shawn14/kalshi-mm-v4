#!/bin/bash
# Pull research candle data from VM and ingest into local DuckDB.
# Run once to bootstrap, then the daily cron on VM keeps the JSONL files fresh.
set -e

VM=kalshi-market-maker
ZONE=us-east1-b
PROJECT=stockalarm-8b019
REMOTE=~/kalshi-mm-v3/research/data
LOCAL=./data/candles

echo "Syncing research/data from VM..."
mkdir -p "$LOCAL"
gcloud compute scp --recurse \
  "$VM:$REMOTE/" "$LOCAL/" \
  --zone="$ZONE" --project="$PROJECT"

echo "Ingesting into DuckDB..."
python -c "from research.ingest import ingest_all; from pathlib import Path; ingest_all(Path('data/candles'))"
echo "Done."
