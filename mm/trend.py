"""Trend detection — stops quoting when a market is directionally moving.

Three signals, any one triggers a pause:
  1. Mid drift: |mid_now - mid_T-60s| > drift_threshold_c
  2. Fill imbalance: >imbalance_pct of recent fills on one side over window
  3. Zone breach: mid exits the 40-60c core zone AND is moving away

When all three clear simultaneously the market is unpaused.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class MidObservation:
    ts: float
    mid: float


class TrendDetector:
    def __init__(self,
                 drift_threshold_c: float = 5.0,
                 drift_window_s: float = 60.0,
                 fill_window: int = 20,
                 imbalance_pct: float = 0.75,
                 core_lo: float = 40.0,
                 core_hi: float = 60.0) -> None:
        self.drift_threshold_c = drift_threshold_c
        self.drift_window_s = drift_window_s
        self.fill_window = fill_window
        self.imbalance_pct = imbalance_pct
        self.core_lo = core_lo
        self.core_hi = core_hi
        self._mids: deque[MidObservation] = deque(maxlen=300)
        self._recent_fills: deque[str] = deque(maxlen=fill_window)  # "yes" or "no"

    def record_mid(self, mid: float) -> None:
        self._mids.append(MidObservation(ts=time.time(), mid=mid))

    def record_fill(self, side: str) -> None:
        self._recent_fills.append(side)

    def is_trending(self) -> tuple[bool, str]:
        """Return (trending, reason). If trending, stop quoting both sides."""
        now = time.time()

        # Signal 1: mid drift over last window
        cutoff = now - self.drift_window_s
        old = next((o for o in self._mids if o.ts >= cutoff), None)
        if old and self._mids:
            drift = abs(self._mids[-1].mid - old.mid)
            if drift > self.drift_threshold_c:
                return True, f"mid drifted {drift:.1f}c in {self.drift_window_s:.0f}s"

        # Signal 2: fill imbalance
        if len(self._recent_fills) >= self.fill_window // 2:
            yes_fills = sum(1 for f in self._recent_fills if f == "yes")
            ratio = yes_fills / len(self._recent_fills)
            if ratio > self.imbalance_pct:
                return True, f"fill imbalance YES {ratio:.0%}"
            if ratio < (1 - self.imbalance_pct):
                return True, f"fill imbalance NO {1-ratio:.0%}"

        # Signal 3: outside core zone and moving
        if self._mids and len(self._mids) >= 2:
            cur = self._mids[-1].mid
            prev = self._mids[-2].mid
            if cur > self.core_hi and cur > prev:
                return True, f"mid {cur:.1f}c above {self.core_hi}c and rising"
            if cur < self.core_lo and cur < prev:
                return True, f"mid {cur:.1f}c below {self.core_lo}c and falling"

        return False, ""
