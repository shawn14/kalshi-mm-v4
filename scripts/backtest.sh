#!/bin/bash
# Run full backtest sweep and print ranked results.
set -e
echo "Running backtest sweep across all series..."
python -m research.backtest
