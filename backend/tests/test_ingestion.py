"""
Tests for the data ingestion validation logic.
"""

import pytest
from app.services.data_ingestion import validate_candle, validate_timestamp_order, CSVAdapter, JSONAdapter
from datetime import datetime, timezone


class TestCandleValidation:
    """Test candle data validation."""

    def test_valid_candle(self):
        """Valid candle should return no errors."""
        candle = {
            "symbol": "AAPL",
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open": 150.0,
            "high": 155.0,
            "low": 148.0,
            "close": 153.0,
            "volume": 1000000.0,
            "timeframe": "1D",
        }
        errors = validate_candle(candle)
        assert errors == []

    def test_negative_price_rejected(self):
        """Negative prices should be rejected."""
        candle = {
            "symbol": "AAPL",
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open": -10.0,
            "high": 155.0,
            "low": 148.0,
            "close": 153.0,
            "volume": 1000.0,
            "timeframe": "1D",
        }
        errors = validate_candle(candle)
        assert any("negative" in e.lower() for e in errors)

    def test_high_less_than_low_rejected(self):
        """High < Low should be rejected."""
        candle = {
            "symbol": "AAPL",
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open": 150.0,
            "high": 145.0,  # Less than low
            "low": 148.0,
            "close": 150.0,
            "volume": 1000.0,
            "timeframe": "1D",
        }
        errors = validate_candle(candle)
        assert any("high" in e.lower() and "low" in e.lower() for e in errors)

    def test_missing_field_rejected(self):
        """Missing required fields should be rejected."""
        candle = {
            "symbol": "AAPL",
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
            # Missing open, high, low, close, volume
            "timeframe": "1D",
        }
        errors = validate_candle(candle)
        assert len(errors) > 0

    def test_invalid_timeframe_rejected(self):
        """Invalid timeframe should be rejected."""
        candle = {
            "symbol": "AAPL",
            "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open": 150.0,
            "high": 155.0,
            "low": 148.0,
            "close": 153.0,
            "volume": 1000.0,
            "timeframe": "2h",  # Invalid
        }
        errors = validate_candle(candle)
        assert any("timeframe" in e.lower() for e in errors)


class TestTimestampOrder:
    """Test timestamp ordering validation."""

    def test_ordered_timestamps_ok(self):
        """Properly ordered timestamps should return no errors."""
        candles = [
            {"timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc)},
            {"timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc)},
            {"timestamp": datetime(2024, 1, 3, tzinfo=timezone.utc)},
        ]
        errors = validate_timestamp_order(candles)
        assert errors == []

    def test_out_of_order_detected(self):
        """Out-of-order timestamps should be detected."""
        candles = [
            {"timestamp": datetime(2024, 1, 3, tzinfo=timezone.utc)},
            {"timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc)},  # Out of order
            {"timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc)},
        ]
        errors = validate_timestamp_order(candles)
        assert len(errors) > 0


class TestCSVAdapter:
    """Test CSV data adapter."""

    @pytest.mark.asyncio
    async def test_parse_csv(self):
        csv_data = b"symbol,timestamp,open,high,low,close,volume,timeframe\nAAPL,2024-01-01T00:00:00,150.0,155.0,148.0,153.0,1000000,1D\n"
        adapter = CSVAdapter()
        candles = await adapter.parse(csv_data)
        assert len(candles) == 1
        assert candles[0]["symbol"] == "AAPL"
        assert candles[0]["open"] == 150.0


class TestJSONAdapter:
    """Test JSON data adapter."""

    @pytest.mark.asyncio
    async def test_parse_json_array(self):
        json_data = b'[{"symbol":"AAPL","timestamp":"2024-01-01","open":150,"high":155,"low":148,"close":153,"volume":1000000,"timeframe":"1D"}]'
        adapter = JSONAdapter()
        candles = await adapter.parse(json_data)
        assert len(candles) == 1
        assert candles[0]["symbol"] == "AAPL"
