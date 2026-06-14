"""Kalshi REST client — rate-limited, RSA-PSS signed."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from core.auth import load_private_key, sign_request

log = logging.getLogger(__name__)

BASE = "https://external-api.kalshi.com/trade-api/v2"
_RATE = asyncio.Semaphore(10)  # max concurrent in-flight requests


class KalshiClient:
    def __init__(self, api_key: str, key_path: str) -> None:
        self.api_key = api_key
        self._key = load_private_key(key_path)
        self._http = httpx.AsyncClient(
            base_url=BASE,
            timeout=10.0,
            headers={"Content-Type": "application/json"},
        )

    async def _req(self, method: str, path: str, *, params: dict | None = None,
                   body: dict | None = None) -> dict:
        # Kalshi signs the full path including /trade-api/v2 prefix
        sign_path = f"/trade-api/v2{path}"
        if params:
            path = f"{path}?{urlencode(params)}"
        headers = sign_request(self.api_key, self._key, method.upper(), sign_path)
        async with _RATE:
            r = await self._http.request(method, path, headers=headers,
                                          json=body)
        if r.status_code == 429:
            await asyncio.sleep(1)
            return await self._req(method, sign_path, params=params, body=body)
        r.raise_for_status()
        return r.json()

    # ── Exchange ──────────────────────────────────────────────────────────────
    async def exchange_status(self) -> dict:
        return await self._req("GET", "/exchange/status")

    # ── Markets ───────────────────────────────────────────────────────────────
    async def get_markets(self, series_ticker: str, status: str = "open",
                          limit: int = 200, cursor: str | None = None) -> dict:
        p: dict[str, Any] = {"series_ticker": series_ticker, "status": status,
                              "limit": limit}
        if cursor:
            p["cursor"] = cursor
        return await self._req("GET", "/markets", params=p)

    async def get_orderbook(self, ticker: str, depth: int = 10) -> dict:
        return await self._req("GET", f"/markets/{ticker}/orderbook",
                               params={"depth": depth})

    # ── Orders ────────────────────────────────────────────────────────────────
    async def place_order(self, ticker: str, side: str, count: int,
                          price_c: int, *, dry_run: bool = False) -> dict:
        """Place a post-only GTC maker limit order.

        post_only=True  — rejected if it would cross the book (never becomes taker)
        cancel_order_on_pause=True — auto-cancels if exchange pauses mid-session
        """
        if dry_run:
            log.info("DRY place %s %s %dc @%dc", ticker, side, count, price_c)
            return {"order_id": f"dry_{ticker}_{side}_{price_c}", "dry": True}

        body: dict[str, Any] = {
            "ticker": ticker,
            "side": side,
            "action": "buy",
            "count": count,
            "time_in_force": "good_till_canceled",
            "post_only": True,
            "cancel_order_on_pause": True,
        }
        # Kalshi uses yes_price for YES orders, no_price for NO orders
        if side == "yes":
            body["yes_price"] = price_c
        else:
            body["no_price"] = price_c

        return await self._req("POST", "/portfolio/orders", body=body)

    async def cancel_order(self, order_id: str) -> dict:
        return await self._req("DELETE", f"/portfolio/orders/{order_id}")

    async def get_open_orders(self, ticker: str | None = None) -> dict:
        p: dict[str, Any] = {"status": "resting", "limit": 200}
        if ticker:
            p["ticker"] = ticker
        return await self._req("GET", "/portfolio/orders", params=p)

    async def get_positions(self) -> dict:
        return await self._req("GET", "/portfolio/positions")

    async def get_balance(self) -> dict:
        return await self._req("GET", "/portfolio/balance")

    async def get_fills(self, ticker: str | None = None, limit: int = 100) -> dict:
        p: dict[str, Any] = {"limit": limit}
        if ticker:
            p["ticker"] = ticker
        return await self._req("GET", "/portfolio/fills", params=p)

    async def close(self) -> None:
        await self._http.aclose()
