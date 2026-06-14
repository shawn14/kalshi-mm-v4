"""Quote generation — compute bid/ask prices for one market.

Zone-based half-spread ladder (from deck slide 9):
  40-60c (core):   hs = base_hs
  30-40 / 60-70:   hs = base_hs + 1  (skew wider outside core)
  20-30 / 70-80:   hs = base_hs + 2  (defensive)
  <20 / >80:       skip entirely

Inventory skew applied on top of zone ladder.
EV gate: EV = hs - fee - expected_adv_sel > 0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

MAKER_FEE_C = 1.0        # roundup(0.0175*P*(1-P)) ≈ 1c at 50c
EXPECTED_ADV_SEL_C = 1.5 # conservative estimate from v3 KXMLBKS backtest


@dataclass
class Quote:
    ticker: str
    yes_bid: int      # cents, integer
    yes_ask: int      # derived: 100 - no_bid
    no_bid: int
    no_ask: int       # derived: 100 - yes_bid
    half_spread: float
    mid: float
    ev_c: float
    contracts: int


def compute_quote(ticker: str, yes_bid_raw: float, yes_ask_raw: float,
                  base_hs: float, inventory_skew: tuple[float, float],
                  contracts: int) -> Quote | None:
    """Return a Quote or None if EV gate fails or mid is out of range."""
    mid = (yes_bid_raw + yes_ask_raw) / 2.0
    natural_spread = yes_ask_raw - yes_bid_raw

    if mid < 20 or mid > 80:
        return None

    # Zone-based half-spread
    if 40 <= mid <= 60:
        hs = base_hs
    elif 30 <= mid < 40 or 60 < mid <= 70:
        hs = base_hs + 1.0
    elif 20 <= mid < 30 or 70 < mid <= 80:
        hs = base_hs + 2.0
    else:
        return None

    # Must have enough natural spread to place within market
    if natural_spread < hs * 2:
        return None

    # Apply inventory skew
    yes_adj, no_adj = inventory_skew
    yes_bid_f = mid - hs + yes_adj
    no_bid_f = (100 - mid) - hs + no_adj

    yes_bid = max(1, min(99, round(yes_bid_f)))
    no_bid = max(1, min(99, round(no_bid_f)))
    yes_ask = 100 - no_bid
    no_ask = 100 - yes_bid

    # EV gate: earnings-per-contract for the maker
    ev_c = hs - MAKER_FEE_C - EXPECTED_ADV_SEL_C
    if ev_c <= 0:
        return None

    return Quote(
        ticker=ticker,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        no_bid=no_bid,
        no_ask=no_ask,
        half_spread=hs,
        mid=mid,
        ev_c=ev_c,
        contracts=contracts,
    )
