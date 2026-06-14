"""Daily loss circuit breaker and consecutive-loss counter."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(self, max_daily_loss_usd: float, max_consecutive_losses: int = 10) -> None:
        self.max_daily_loss_usd = max_daily_loss_usd
        self.max_consecutive_losses = max_consecutive_losses
        self.session_pnl_usd: float = 0.0
        self.consecutive_losses: int = 0
        self._tripped = False

    @property
    def tripped(self) -> bool:
        return self._tripped

    def record_pnl(self, pnl_usd: float) -> bool:
        """Record realized P&L. Returns True if circuit now tripped."""
        self.session_pnl_usd += pnl_usd
        if pnl_usd < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        if self.session_pnl_usd < -self.max_daily_loss_usd:
            self._tripped = True
            log.critical("CIRCUIT BREAKER: daily loss $%.2f > limit $%.2f",
                         -self.session_pnl_usd, self.max_daily_loss_usd)
        if self.consecutive_losses >= self.max_consecutive_losses:
            self._tripped = True
            log.critical("CIRCUIT BREAKER: %d consecutive losses", self.consecutive_losses)
        return self._tripped

    def reset_session(self) -> None:
        self.session_pnl_usd = 0.0
        self.consecutive_losses = 0
        self._tripped = False
