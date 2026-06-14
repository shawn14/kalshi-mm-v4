"""Kalshi WebSocket feed — real-time orderbook deltas + fill channel.

Publishes events to subscribed callbacks:
  - orderbook_update(ticker, yes_bid, yes_ask, spread)
  - fill(fill_dict)
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Callable

import websockets

from core.auth import load_private_key, sign_request

log = logging.getLogger(__name__)

WS_URL = "wss://external-api-ws.kalshi.com/trade-api/ws/v2"


class KalshiWS:
    def __init__(self, api_key: str, key_path: str) -> None:
        self.api_key = api_key
        self._key = load_private_key(key_path)
        # ticker → {yes_bid, no_bid}  (best bids in cents)
        self._books: dict[str, dict[str, float]] = defaultdict(dict)
        self._ob_callbacks: list[Callable] = []
        self._fill_callbacks: list[Callable] = []
        self._subscribed: set[str] = set()
        self._ws = None
        self._running = False

    def on_orderbook(self, cb: Callable) -> None:
        self._ob_callbacks.append(cb)

    def on_fill(self, cb: Callable) -> None:
        self._fill_callbacks.append(cb)

    async def subscribe(self, tickers: list[str]) -> None:
        new = [t for t in tickers if t not in self._subscribed]
        if not new:
            return
        self._subscribed.update(new)
        if self._ws:
            await self._ws.send(json.dumps({
                "id": 1, "cmd": "subscribe",
                "params": {"channels": ["orderbook_delta", "fill"],
                           "market_tickers": new},
            }))

    async def unsubscribe(self, tickers: list[str]) -> None:
        for t in tickers:
            self._subscribed.discard(t)
            self._books.pop(t, None)
        if self._ws and tickers:
            await self._ws.send(json.dumps({
                "id": 2, "cmd": "unsubscribe",
                "params": {"channels": ["orderbook_delta"],
                           "market_tickers": tickers},
            }))

    def best_quote(self, ticker: str) -> tuple[float | None, float | None, float | None]:
        """Return (yes_bid, yes_ask, spread) or (None, None, None) if no book."""
        book = self._books.get(ticker, {})
        yb = book.get("yes_bid")
        nb = book.get("no_bid")
        if yb is None or nb is None:
            return None, None, None
        ya = 100 - nb   # YES ask = 100 - best NO bid
        spread = ya - yb
        return yb, ya, spread

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._connect_and_pump()
            except Exception as e:
                log.warning("WS disconnected: %s — reconnecting in 2s", e)
                await asyncio.sleep(2)

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _connect_and_pump(self) -> None:
        headers = sign_request(self.api_key, self._key, "GET",
                               "/trade-api/ws/v2")
        async with websockets.connect(WS_URL, additional_headers=headers,
                                      ping_interval=20) as ws:
            self._ws = ws
            if self._subscribed:
                await ws.send(json.dumps({
                    "id": 1, "cmd": "subscribe",
                    "params": {"channels": ["orderbook_delta", "fill"],
                               "market_tickers": list(self._subscribed)},
                }))
            async for raw in ws:
                self._handle(raw)

    def _handle(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except Exception:
            return
        t = msg.get("type")
        if t == "orderbook_snapshot":
            self._apply_snapshot(msg)
        elif t == "orderbook_delta":
            self._apply_delta(msg)
        elif t == "fill":
            for cb in self._fill_callbacks:
                cb(msg)

    def _apply_snapshot(self, msg: dict) -> None:
        ticker = msg.get("market_ticker", "")
        ob = msg.get("msg", {})
        yb = self._best_price(ob.get("yes", []))
        nb = self._best_price(ob.get("no", []))
        self._books[ticker] = {"yes_bid": yb, "no_bid": nb}
        self._emit_ob(ticker)

    def _apply_delta(self, msg: dict) -> None:
        ticker = msg.get("market_ticker", "")
        side = msg.get("side", "")
        price = msg.get("price")
        delta = msg.get("delta", 0)
        if price is None:
            return
        book = self._books.setdefault(ticker, {})
        key = "yes_bid" if side == "yes" else "no_bid"
        if delta == 0:
            # level removed; re-fetch best from snapshot not available — use REST fallback
            if book.get(key) == price:
                book[key] = None  # stale; engine will REST-refresh
        else:
            if book.get(key) is None or price > book[key]:
                book[key] = price
        self._emit_ob(ticker)

    def _emit_ob(self, ticker: str) -> None:
        yb, ya, sp = self.best_quote(ticker)
        if yb is not None:
            for cb in self._ob_callbacks:
                cb(ticker, yb, ya, sp)

    @staticmethod
    def _best_price(levels: list) -> float | None:
        if not levels:
            return None
        # levels: [[price, qty], ...] sorted desc by price
        return float(levels[0][0]) if levels else None
