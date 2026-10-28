"""Normalized, backend-only stock market data providers with safe caching."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import random
from time import monotonic

import httpx

from app.core.config import get_settings

INTERVALS = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1D": "1day", "1W": "1week"}
ALPACA_INTERVALS = {"1m": "1Min", "5m": "5Min", "15m": "15Min", "1h": "1Hour", "4h": "4Hour", "1D": "1Day", "1W": "1Week"}
_memory_cache: dict[str, tuple[float, object]] = {}


def _demo_candles(symbol: str, timeframe: str, limit: int, start_date: str | None) -> list[dict]:
    """Deterministic offline candles for local demos when no provider is configured."""
    seed = int.from_bytes(sha256(symbol.encode()).digest()[:8], "big")
    rng = random.Random(seed)
    step = {"1m": timedelta(minutes=1), "5m": timedelta(minutes=5), "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1), "4h": timedelta(hours=4), "1D": timedelta(days=1),
            "1W": timedelta(weeks=1)}[timeframe]
    current = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc) if start_date else datetime.now(timezone.utc) - step * limit
    price = 80 + rng.random() * 120
    candles = []
    for _ in range(min(limit, 5000)):
        open_ = price
        close = max(1, open_ * (1 + rng.uniform(-0.025, 0.025)))
        high = max(open_, close) * (1 + rng.uniform(0, 0.012))
        low = min(open_, close) * (1 - rng.uniform(0, 0.012))
        candles.append({"symbol": symbol, "timestamp": current, "open": open_, "high": high,
                        "low": low, "close": close, "volume": rng.randint(10000, 1000000),
                        "timeframe": timeframe, "provider": "demo"})
        price = close
        current += step
    return candles


def parse_provider_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    raise ValueError(f"Unsupported provider timestamp: {value}")


def validate_candles(candles: list[dict]) -> list[dict]:
    """Validate, deduplicate, and sort provider candles."""
    by_timestamp: dict[datetime, dict] = {}
    for candle in candles:
        open_, high, low, close = (float(candle[key]) for key in ("open", "high", "low", "close"))
        if min(open_, high, low, close) <= 0 or float(candle.get("volume", 0)) < 0:
            raise ValueError("Provider returned invalid price or volume")
        if high < max(open_, low, close) or low > min(open_, high, close):
            raise ValueError("Provider returned invalid OHLC values")
        by_timestamp[candle["timestamp"]] = candle
    return [by_timestamp[key] for key in sorted(by_timestamp)]


async def _request(url: str, *, params: dict, headers: dict | None = None) -> dict:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.25 * 2**attempt)
    raise last_error or RuntimeError("Market data request failed")


def _cache_get(key: str) -> object | None:
    item = _memory_cache.get(key)
    if item and item[0] > monotonic():
        return item[1]
    _memory_cache.pop(key, None)
    return None


def _cache_set(key: str, value: object, seconds: int) -> object:
    _memory_cache[key] = (monotonic() + seconds, value)
    return value


def _alpaca_headers() -> dict[str, str]:
    settings = get_settings()
    if not settings.alpaca_api_key or not settings.alpaca_secret_key:
        raise RuntimeError("ALPACA_API_KEY and ALPACA_SECRET_KEY are not configured")
    return {"APCA-API-KEY-ID": settings.alpaca_api_key, "APCA-API-SECRET-KEY": settings.alpaca_secret_key}


async def _alpaca_candles(symbol: str, timeframe: str, limit: int) -> list[dict]:
    settings = get_settings()
    payload = await _request(
        f"https://data.alpaca.markets/v2/stocks/{symbol}/bars",
        params={"timeframe": ALPACA_INTERVALS[timeframe], "limit": limit, "feed": settings.alpaca_data_feed},
        headers=_alpaca_headers(),
    )
    return validate_candles([{
        "symbol": symbol, "timestamp": parse_provider_timestamp(bar["t"]),
        "open": float(bar["o"]), "high": float(bar["h"]), "low": float(bar["l"]),
        "close": float(bar["c"]), "volume": float(bar.get("v", 0)), "timeframe": timeframe,
        "provider": "alpaca", "is_delayed": False,
    } for bar in payload.get("bars") or []])


async def _alpaca_quote(symbol: str) -> dict:
    settings = get_settings()
    payload = await _request(
        f"https://data.alpaca.markets/v2/stocks/{symbol}/snapshot",
        params={"feed": settings.alpaca_data_feed}, headers=_alpaca_headers(),
    )
    trade, day, previous = payload.get("latestTrade") or {}, payload.get("dailyBar") or {}, payload.get("prevDailyBar") or {}
    price = float(trade.get("p") or day.get("c") or 0)
    if price <= 0:
        raise ValueError("No quote returned")
    previous_close = float(previous.get("c") or price)
    return {
        "symbol": symbol, "price": price, "previous_close": previous_close,
        "change": round(price - previous_close, 4),
        "percent_change": round((price - previous_close) / previous_close * 100, 4) if previous_close else 0,
        "open": day.get("o"), "high": day.get("h"), "low": day.get("l"), "volume": day.get("v"),
        "is_market_open": False,
        "timestamp": parse_provider_timestamp(trade.get("t") or datetime.now(timezone.utc).isoformat()),
        "provider": "alpaca", "feed": settings.alpaca_data_feed, "is_delayed": False,
    }


async def _twelve_candles(symbol: str, timeframe: str, limit: int, start_date: str | None, end_date: str | None) -> list[dict]:
    settings = get_settings()
    if not settings.twelve_data_api_key:
        raise RuntimeError("TWELVE_DATA_API_KEY is not configured")
    params = {"symbol": symbol, "interval": INTERVALS[timeframe], "outputsize": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    payload = await _request("https://api.twelvedata.com/time_series", params=params, headers={"Authorization": f"apikey {settings.twelve_data_api_key}"})
    if payload.get("status") == "error" or not payload.get("values"):
        raise ValueError(payload.get("message", "No market data returned"))
    return validate_candles([{
        "symbol": symbol, "timestamp": parse_provider_timestamp(value["datetime"]),
        "open": float(value["open"]), "high": float(value["high"]), "low": float(value["low"]),
        "close": float(value["close"]), "volume": float(value.get("volume") or 0), "timeframe": timeframe,
        "provider": "twelve_data", "is_delayed": False,
    } for value in payload["values"]])


async def _twelve_quote(symbol: str) -> dict:
    settings = get_settings()
    if not settings.twelve_data_api_key:
        raise RuntimeError("TWELVE_DATA_API_KEY is not configured")
    payload = await _request("https://api.twelvedata.com/quote", params={"symbol": symbol}, headers={"Authorization": f"apikey {settings.twelve_data_api_key}"})
    if payload.get("status") == "error" or not payload.get("close"):
        raise ValueError(payload.get("message", "No quote returned"))
    return {
        "symbol": symbol, "price": float(payload["close"]),
        "previous_close": float(payload.get("previous_close") or payload["close"]),
        "change": float(payload.get("change") or 0), "percent_change": float(payload.get("percent_change") or 0),
        "open": float(payload.get("open") or payload["close"]), "high": float(payload.get("high") or payload["close"]),
        "low": float(payload.get("low") or payload["close"]), "volume": float(payload.get("volume") or 0),
        "is_market_open": bool(payload.get("is_market_open", False)), "timestamp": datetime.now(timezone.utc),
        "provider": "twelve_data", "feed": "provider-default", "is_delayed": False,
    }


async def fetch_live_candles(symbol: str, timeframe: str, limit: int, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    symbol = symbol.upper().strip()
    key = f"candles:{symbol}:{timeframe}:{limit}:{start_date}:{end_date}"
    cached = _cache_get(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    try:
        if get_settings().market_data_provider.lower() == "alpaca":
            candles = await _alpaca_candles(symbol, timeframe, limit)
        else:
            candles = await _twelve_candles(symbol, timeframe, limit, start_date, end_date)
    except (RuntimeError, ValueError, httpx.HTTPError):
        candles = _demo_candles(symbol, timeframe, limit, start_date)
    if not candles:
        raise ValueError("No market data returned")
    return _cache_set(key, candles, 15)  # type: ignore[return-value]


async def fetch_live_quote(symbol: str) -> dict:
    symbol = symbol.upper().strip()
    key = f"quote:{symbol}"
    cached = _cache_get(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    quote = await (_alpaca_quote(symbol) if get_settings().market_data_provider.lower() == "alpaca" else _twelve_quote(symbol))
    return _cache_set(key, quote, 5)  # type: ignore[return-value]
