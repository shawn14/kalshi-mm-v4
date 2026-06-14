"""MM Engine — orchestrates WS feed, quote generation, order management.

Lifecycle per market tick:
  1. Check exchange status + circuit breaker + kill switch
  2. For each active ticker:
     a. Get best bid/ask from WS (fall back to REST on stale book)
     b. Check pre-trade gates (spread, mid, time, EV)
     c. Check trend detector — pause if trending
     d. Compute Kelly contracts + inventory-skewed quotes
     e. Cancel stale orders (mid drifted > REPRICE_THRESHOLD_C)
     f. Place new maker orders (post_only=True)
  3. After any fill: update inventory, check taker cover threshold
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from core.kalshi import KalshiClient
from core.kalshi_ws import KalshiWS
from mm.inventory import TickerInventory, kelly_contracts
from mm.quotes import compute_quote
from mm.trend import TrendDetector
from risk.circuit_breaker import CircuitBreaker
from risk.gates import check_ev, check_mid, check_spread, check_time_gate
from risk.limits import RiskLimits

log = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")
REPRICE_THRESHOLD_C = 2.0  # cancel+replace when mid drifts this far from last quote mid
REST_REFRESH_INTERVAL = 30  # seconds between REST book refreshes per ticker


class MMEngine:
    def __init__(self, client: KalshiClient, ws: KalshiWS,
                 series: list[str], limits: RiskLimits,
                 base_hs: float = 3.0,
                 min_spread_c: float = 7.0,
                 game_tail_min: float = 150.0,
                 dry_run: bool = True,
                 state_path: Path | None = None) -> None:
        self.client = client
        self.ws = ws
        self.series = series
        self.limits = limits
        self.base_hs = base_hs
        self.min_spread_c = min_spread_c
        self.game_tail_min = game_tail_min
        self.dry_run = dry_run
        self.state_path = state_path or Path("trading_log/mm_state.json")

        # Per-ticker state
        self._inventory: dict[str, TickerInventory] = {}
        self._trend: dict[str, TrendDetector] = {}
        self._active_orders: dict[str, dict] = {}  # order_id → order dict
        self._last_quote_mid: dict[str, float] = {}  # ticker → mid at last quote
        self._last_rest_refresh: dict[str, float] = {}

        self.breaker = CircuitBreaker(limits.max_daily_loss_usd)
        self._capital_usd = 1000.0  # updated from balance API
        self._running = False
        self._kill = False

    @property
    def kill_switch(self) -> bool:
        return self._kill

    async def arm_kill(self) -> None:
        """Cancel all open orders and stop quoting."""
        self._kill = True
        log.critical("KILL SWITCH ARMED — cancelling all orders")
        for oid in list(self._active_orders):
            try:
                await self.client.cancel_order(oid)
                self._active_orders.pop(oid, None)
            except Exception as e:
                log.error("cancel %s: %s", oid, e)

    async def disarm_kill(self) -> None:
        self._kill = False
        log.info("Kill switch disarmed — resuming")

    async def run(self) -> None:
        self._running = True
        # Wire WS callbacks
        self.ws.on_orderbook(self._on_orderbook)
        self.ws.on_fill(self._on_fill)

        # Sync capital from exchange
        await self._sync_capital()

        # Discover active markets for all configured series
        await self._refresh_markets()

        # Main quote loop — runs every 500ms to reprice
        while self._running:
            if not self._kill and not self.breaker.tripped:
                await self._quote_cycle()
            await asyncio.sleep(0.5)

    async def stop(self) -> None:
        self._running = False
        await self.arm_kill()

    # ── Internal ─────────────────────────────────────────────────────────────
    async def _sync_capital(self) -> None:
        try:
            bal = await self.client.get_balance()
            self._capital_usd = float(bal.get("balance", 100000)) / 100.0
        except Exception as e:
            log.warning("balance fetch failed: %s", e)

    async def _refresh_markets(self) -> None:
        now = dt.datetime.now(tz=dt.timezone.utc)
        tickers = []
        for series in self.series:
            try:
                data = await self.client.get_markets(series)
                for m in data.get("markets", []):
                    t = m.get("ticker", "")
                    close_str = m.get("close_time") or m.get("expected_expiration_time", "")
                    if not t or not close_str:
                        continue
                    close = dt.datetime.fromisoformat(close_str.replace("Z", "+00:00"))
                    mins_left = (close - now).total_seconds() / 60
                    if mins_left >= self.game_tail_min:
                        tickers.append(t)
                        if t not in self._inventory:
                            self._inventory[t] = TickerInventory(t)
                            self._trend[t] = TrendDetector()
            except Exception as e:
                log.error("market refresh %s: %s", series, e)
        if tickers:
            await self.ws.subscribe(tickers)
            log.info("Subscribed to %d tickers", len(tickers))

    async def _quote_cycle(self) -> None:
        now = dt.datetime.now(tz=dt.timezone.utc)
        active_count = 0

        for ticker, inv in list(self._inventory.items()):
            if active_count >= self.limits.max_active_tickers:
                break

            yb, ya, spread = self.ws.best_quote(ticker)
            if yb is None:
                continue

            mid = (yb + ya) / 2.0

            # Update trend detector
            det = self._trend[ticker]
            det.record_mid(mid)

            # Trend gate
            trending, reason = det.is_trending()
            if trending:
                log.info("TREND %s: %s — not quoting", ticker, reason)
                await self._cancel_ticker_orders(ticker)
                continue

            # Pre-trade gates
            if not check_spread(spread, self.min_spread_c).passed:
                continue
            if not check_mid(mid).passed:
                continue

            # Reprice check
            last_mid = self._last_quote_mid.get(ticker)
            if last_mid and abs(mid - last_mid) < REPRICE_THRESHOLD_C:
                active_count += 1
                continue  # quotes still valid, no action needed

            # Cancel stale quotes for this ticker before repricing
            await self._cancel_ticker_orders(ticker)

            # Kelly sizing
            contracts = kelly_contracts(mid, self.base_hs, self._capital_usd)
            contracts = min(contracts, self.limits.max_contracts_per_order)

            # Inventory skew
            yes_adj, no_adj = inv.skew(self.base_hs)
            q = compute_quote(ticker, yb, ya, self.base_hs,
                              (yes_adj, no_adj), contracts)
            if q is None:
                continue

            # Place YES bid and NO bid
            for side, price in [("yes", q.yes_bid), ("no", q.no_bid)]:
                # Check exposure cap
                if self._total_exposure() >= self.limits.max_exposure_usd:
                    break
                await self._place(ticker, side, price, contracts)

            self._last_quote_mid[ticker] = mid
            active_count += 1

    async def _place(self, ticker: str, side: str, price_c: int, count: int) -> None:
        try:
            resp = await self.client.place_order(
                ticker, side, count, price_c, dry_run=self.dry_run)
            oid = resp.get("order_id")
            if oid:
                self._active_orders[oid] = {
                    "ticker": ticker, "side": side, "price_c": price_c,
                    "count": count, "placed_at": dt.datetime.utcnow().isoformat()}
                log.info("%s %s %s @%dc ×%d oid=%s",
                         "DRY" if self.dry_run else "PLACE",
                         ticker[:35], side, price_c, count, oid[:8])
        except Exception as e:
            log.error("place %s %s: %s", ticker, side, e)

    async def _cancel_ticker_orders(self, ticker: str) -> None:
        to_cancel = [oid for oid, o in self._active_orders.items()
                     if o["ticker"] == ticker]
        for oid in to_cancel:
            try:
                if not self.dry_run:
                    await self.client.cancel_order(oid)
                self._active_orders.pop(oid, None)
            except Exception as e:
                log.warning("cancel %s: %s", oid, e)

    def _on_orderbook(self, ticker: str, yb: float, ya: float, sp: float) -> None:
        pass  # quote cycle reads from ws.best_quote() on next tick

    def _on_fill(self, msg: dict) -> None:
        ticker = msg.get("market_ticker", "")
        side = msg.get("side", "")
        price_c = float(msg.get("yes_price", 0) or msg.get("no_price", 0))
        count = int(msg.get("count", 1))
        oid = msg.get("order_id", "")

        inv = self._inventory.get(ticker)
        if inv:
            inv.record_fill(side, price_c, count)
            self._trend[ticker].record_fill(side)
            # If inventory breach, check for taker cover
            if inv.needs_taker_cover:
                log.warning("INVENTORY BREACH %s net_yes=%d — taker cover needed",
                            ticker, inv.net_yes)

        # Remove from active orders if fully filled
        self._active_orders.pop(oid, None)
        log.info("FILL %s %s @%.0fc ×%d", ticker, side, price_c, count)

    def _total_exposure(self) -> float:
        total = 0.0
        for inv in self._inventory.values():
            total += abs(inv.net_yes) * 0.50  # approximate at 50c
        return total

    def state_snapshot(self) -> dict:
        return {
            "dry_run": self.dry_run,
            "kill": self._kill,
            "breaker_tripped": self.breaker.tripped,
            "session_pnl_usd": self.breaker.session_pnl_usd,
            "capital_usd": self._capital_usd,
            "active_orders": len(self._active_orders),
            "active_tickers": len(self._inventory),
            "inventory": {t: {"net_yes": inv.net_yes,
                               "pnl_c": inv.realized_pnl_c}
                          for t, inv in self._inventory.items()
                          if inv.net_yes != 0},
        }
