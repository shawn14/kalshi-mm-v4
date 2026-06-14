"""Pre-trade gates — all must pass before quoting a market."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass
class GateResult:
    passed: bool
    reason: str = ""


def check_spread(spread: float, min_spread_c: float) -> GateResult:
    if spread < min_spread_c:
        return GateResult(False, f"spread {spread:.1f}c < min {min_spread_c}c")
    return GateResult(True)


def check_mid(mid: float, lo: float = 20.0, hi: float = 80.0) -> GateResult:
    if mid < lo or mid > hi:
        return GateResult(False, f"mid {mid:.1f}c outside [{lo},{hi}]")
    return GateResult(True)


def check_time_gate(close_time: dt.datetime, now: dt.datetime,
                    min_minutes: float) -> GateResult:
    mins = (close_time - now).total_seconds() / 60
    if mins < min_minutes:
        return GateResult(False, f"only {mins:.0f}min to close, need {min_minutes}")
    return GateResult(True)


def check_ev(half_spread_c: float, fee_c: float,
             expected_adv_sel_c: float) -> GateResult:
    """Gate-0: EV = hs*(1-fee/hs) - E[adverse_selection] > 0."""
    ev = half_spread_c - fee_c - expected_adv_sel_c
    if ev <= 0:
        return GateResult(False, f"EV {ev:.2f}c <= 0")
    return GateResult(True, f"EV={ev:.2f}c")
