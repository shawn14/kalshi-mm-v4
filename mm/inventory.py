"""Inventory tracking and Kelly-based quote skewing.

Kelly sizing: f* = (p*b - q) / b, where b = profit/loss ratio.
For a maker at 50c mid with hs=3c: b = (50+3)/(50-3) ≈ 1.13, p = 0.5 → f* ≈ 0.056.
We use fractional Kelly (25%) as the baseline contract count.

Inventory skew: when net YES exposure grows, we move our YES bid down (quote less
aggressively to get YES fills) and our NO bid down (more aggressively to get NO fills
to reduce inventory). The skew magnitude scales linearly with |net_yes|.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


KELLY_FRACTION = 0.25
MAKER_FEE_C = 1.0  # roundup(0.0175 * 50 * 50) ≈ 1c at mid=50c


@dataclass
class TickerInventory:
    ticker: str
    net_yes: int = 0          # positive = net long YES
    fills_yes: int = 0
    fills_no: int = 0
    realized_pnl_c: float = 0.0

    def skew(self, half_spread_c: float, skew_per_contract: float = 0.5) -> tuple[float, float]:
        """Return (yes_bid_adjustment, no_bid_adjustment) in cents.

        Positive adjustment = more aggressive (higher bid).
        When net_yes > 0, we want fewer YES fills → lower YES bid, more NO fills → raise NO bid.
        """
        s = self.net_yes * skew_per_contract
        yes_adj = -s  # pull YES bid down when long YES
        no_adj = +s   # push NO bid up when long YES (more aggressive to fill NO)
        return yes_adj, no_adj

    def record_fill(self, side: str, price_c: float, count: int,
                    outcome: str | None = None) -> None:
        if side == "yes":
            self.net_yes += count
            self.fills_yes += count
        else:
            self.net_yes -= count
            self.fills_no += count
        if outcome is not None:
            self._settle(side, price_c, count, outcome)

    def _settle(self, side: str, price_c: float, count: int, outcome: str) -> None:
        won = (side == "yes" and outcome == "yes") or (side == "no" and outcome == "no")
        pnl = (100 - price_c) * count if won else -price_c * count
        pnl -= MAKER_FEE_C * count
        self.realized_pnl_c += pnl

    @property
    def needs_taker_cover(self) -> bool:
        """True when inventory is skewed enough to warrant a taker hedge."""
        return abs(self.net_yes) >= 8


def kelly_contracts(mid_c: float, half_spread_c: float,
                    capital_usd: float, kelly_fraction: float = KELLY_FRACTION) -> int:
    """Return the Kelly-optimal contract count for one side of a maker quote."""
    if mid_c <= 0 or mid_c >= 100:
        return 1
    p = mid_c / 100.0
    q = 1 - p
    win_amt = (100 - (mid_c - half_spread_c))  # win: settle at 100, cost = mid - hs
    loss_amt = (mid_c - half_spread_c)          # lose: settle at 0
    if loss_amt <= 0:
        return 1
    b = win_amt / loss_amt
    f_star = max(0, (p * b - q) / b)
    f_kelly = f_star * kelly_fraction
    max_bet_usd = capital_usd * f_kelly
    price_usd = loss_amt / 100.0
    contracts = max(1, int(max_bet_usd / price_usd))
    return min(contracts, 5)  # hard cap per quote
