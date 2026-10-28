"""
Data ingestion service with pluggable adapter pattern.
Handles CSV/JSON file ingestion with validation and deduplication.
"""

import csv
import json
import io
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candle import Candle
from app.schemas.candle import CandleCreate


# ─── Validation ──────────────────────────────────────────────────

class ValidationError(Exception):
    """Raised when candle data fails validation."""
    pass


def validate_candle(data: dict) -> list[str]:
    """Validate a single candle record. Returns list of error messages."""
    errors = []

    # Check required fields
    required = ["symbol", "timestamp", "open", "high", "low", "close", "volume", "timeframe"]
    for field in required:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors

    # No negative prices
    for field in ("open", "high", "low", "close"):
        try:
            val = float(data[field])
            if val < 0:
                errors.append(f"{field} cannot be negative: {val}")
        except (ValueError, TypeError):
            errors.append(f"{field} must be numeric: {data[field]}")

    # Volume non-negative
    try:
        vol = float(data["volume"])
        if vol < 0:
            errors.append(f"volume cannot be negative: {vol}")
    except (ValueError, TypeError):
        errors.append(f"volume must be numeric: {data['volume']}")

    # OHLC consistency
    try:
        o, h, l, c = float(data["open"]), float(data["high"]), float(data["low"]), float(data["close"])
        if h < l:
            errors.append(f"high ({h}) must be >= low ({l})")
        if h < o or h < c:
            errors.append(f"high ({h}) must be >= open ({o}) and close ({c})")
        if l > o or l > c:
            errors.append(f"low ({l}) must be <= open ({o}) and close ({c})")
    except (ValueError, TypeError):
        pass  # Already caught above

    # Valid timeframe
    valid_timeframes = {"1m", "5m", "15m", "1h", "4h", "1D", "1W"}
    if data.get("timeframe") not in valid_timeframes:
        errors.append(f"Invalid timeframe: {data.get('timeframe')}. Must be one of {valid_timeframes}")

    return errors


def validate_timestamp_order(candles: list[dict]) -> list[str]:
    """Check for out-of-order timestamps in a list of candles."""
    errors = []
    for i in range(1, len(candles)):
        prev_ts = candles[i - 1].get("timestamp")
        curr_ts = candles[i].get("timestamp")
        if prev_ts and curr_ts and curr_ts < prev_ts:
            errors.append(
                f"Out-of-order timestamp at row {i + 1}: {curr_ts} < {prev_ts}"
            )
    return errors


# ─── Abstract Adapter ────────────────────────────────────────────

class DataAdapter(ABC):
    """Abstract base class for data source adapters."""

    @abstractmethod
    async def parse(self, raw_data: bytes) -> list[dict]:
        """Parse raw data bytes into a list of candle dictionaries."""
        ...

    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this data source."""
        ...


# ─── CSV Adapter ─────────────────────────────────────────────────

class CSVAdapter(DataAdapter):
    """Adapter for CSV file ingestion."""

    def source_name(self) -> str:
        return "csv"

    async def parse(self, raw_data: bytes) -> list[dict]:
        """Parse CSV data into candle dictionaries."""
        text_data = raw_data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text_data))
        candles = []

        for row in reader:
            candle = {
                "symbol": row.get("symbol", "").strip().upper(),
                "timestamp": self._parse_timestamp(row.get("timestamp", "")),
                "open": self._parse_float(row.get("open")),
                "high": self._parse_float(row.get("high")),
                "low": self._parse_float(row.get("low")),
                "close": self._parse_float(row.get("close")),
                "volume": self._parse_float(row.get("volume")),
                "timeframe": row.get("timeframe", "1D").strip(),
            }
            candles.append(candle)

        return candles

    def _parse_timestamp(self, ts_str: str) -> datetime | None:
        if not ts_str:
            return None
        try:
            dt = datetime.fromisoformat(ts_str.strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def _parse_float(self, val: str | None) -> float | None:
        if val is None or val.strip() == "":
            return None
        try:
            return float(val.strip())
        except ValueError:
            return None


# ─── JSON Adapter ────────────────────────────────────────────────

class JSONAdapter(DataAdapter):
    """Adapter for JSON file ingestion."""

    def source_name(self) -> str:
        return "json"

    async def parse(self, raw_data: bytes) -> list[dict]:
        """Parse JSON data into candle dictionaries."""
        data = json.loads(raw_data.decode("utf-8"))
        if isinstance(data, dict):
            data = data.get("candles", data.get("data", [data]))
        if not isinstance(data, list):
            data = [data]

        candles = []
        for item in data:
            candle = {
                "symbol": str(item.get("symbol", "")).strip().upper(),
                "timestamp": self._parse_timestamp(item.get("timestamp")),
                "open": float(item["open"]) if "open" in item else None,
                "high": float(item["high"]) if "high" in item else None,
                "low": float(item["low"]) if "low" in item else None,
                "close": float(item["close"]) if "close" in item else None,
                "volume": float(item["volume"]) if "volume" in item else None,
                "timeframe": item.get("timeframe", "1D"),
            }
            candles.append(candle)

        return candles

    def _parse_timestamp(self, ts) -> datetime | None:
        if ts is None:
            return None
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                return ts.replace(tzinfo=timezone.utc)
            return ts
        try:
            dt = datetime.fromisoformat(str(ts))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None


# ─── Ingestion Service ───────────────────────────────────────────

class IngestionService:
    """Orchestrates data ingestion: parse → validate → deduplicate → store."""

    ADAPTERS: dict[str, type[DataAdapter]] = {
        "csv": CSVAdapter,
        "json": JSONAdapter,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    def get_adapter(self, file_type: str) -> DataAdapter:
        """Get the appropriate adapter for a file type."""
        adapter_cls = self.ADAPTERS.get(file_type.lower())
        if not adapter_cls:
            raise ValueError(f"Unsupported file type: {file_type}. Supported: {list(self.ADAPTERS.keys())}")
        return adapter_cls()

    async def ingest(self, raw_data: bytes, file_type: str) -> dict:
        """
        Full ingestion pipeline: parse → validate → store with deduplication.
        Returns a summary dict with counts of inserted, skipped, and errors.
        """
        adapter = self.get_adapter(file_type)
        candles = await adapter.parse(raw_data)

        inserted = 0
        duplicates_skipped = 0
        errors = []

        # Validate each candle
        valid_candles = []
        for i, candle in enumerate(candles):
            errs = validate_candle(candle)
            if errs:
                errors.extend([f"Row {i + 1}: {e}" for e in errs])
            else:
                valid_candles.append(candle)

        # Check timestamp order (warning, not blocking)
        ts_errors = validate_timestamp_order(valid_candles)
        errors.extend(ts_errors)

        # Upsert with deduplication (ON CONFLICT DO NOTHING)
        for candle in valid_candles:
            try:
                stmt = pg_insert(Candle).values(
                    symbol=candle["symbol"],
                    timestamp=candle["timestamp"],
                    timeframe=candle["timeframe"],
                    open=candle["open"],
                    high=candle["high"],
                    low=candle["low"],
                    close=candle["close"],
                    volume=candle["volume"],
                ).on_conflict_do_nothing(
                    index_elements=["symbol", "timestamp", "timeframe"]
                )
                result = await self.db.execute(stmt)
                if result.rowcount > 0:
                    inserted += 1
                else:
                    duplicates_skipped += 1
            except Exception as e:
                errors.append(f"DB error for {candle['symbol']} @ {candle['timestamp']}: {str(e)}")

        await self.db.commit()

        return {
            "inserted": inserted,
            "duplicates_skipped": duplicates_skipped,
            "errors": errors,
        }
