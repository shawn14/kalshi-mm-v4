"""Position limits and exposure caps."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskLimits:
    max_net_contracts_per_ticker: int = 5       # net YES contracts before skew
    max_gross_contracts_per_ticker: int = 10    # abs(YES) + abs(NO) per ticker
    max_active_tickers: int = 20                # simultaneous markets quoted
    max_exposure_usd: float = 500.0             # total dollar exposure at risk
    max_daily_loss_usd: float = 100.0           # circuit breaker
    max_contracts_per_order: int = 2            # single order size
    taker_cover_threshold: int = 8              # net contracts before taker cover


@dataclass
class PositionState:
    ticker: str
    net_yes: int = 0          # positive = long YES, negative = long NO
    avg_yes_cost: float = 0   # average fill price for YES side
    avg_no_cost: float = 0    # average fill price for NO side
    session_pnl_c: float = 0

    @property
    def gross(self) -> int:
        return abs(self.net_yes)

    def update_fill(self, side: str, price_c: float, count: int) -> None:
        if side == "yes":
            prev_cost = self.avg_yes_cost * max(self.net_yes, 0)
            self.net_yes += count
            if self.net_yes > 0:
                self.avg_yes_cost = (prev_cost + price_c * count) / self.net_yes
        else:  # no fill = effectively short YES
            prev_cost = self.avg_no_cost * max(-self.net_yes, 0)
            self.net_yes -= count
            if self.net_yes < 0:
                self.avg_no_cost = (prev_cost + price_c * count) / (-self.net_yes)
