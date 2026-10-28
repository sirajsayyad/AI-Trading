"""
Pydantic schemas for candle data endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class CandleBase(BaseModel):
    """Base candle schema with validation."""

    symbol: str = Field(..., min_length=1, max_length=20, examples=["AAPL"])
    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    timeframe: str = Field(..., pattern=r"^(1m|5m|15m|1h|4h|1D|1W)$")

    @field_validator("high")
    @classmethod
    def high_gte_low(cls, v: float, info) -> float:
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("high must be >= low")
        return v

    @field_validator("high")
    @classmethod
    def high_gte_open_close(cls, v: float, info) -> float:
        for field in ("open", "close"):
            if field in info.data and v < info.data[field]:
                raise ValueError(f"high must be >= {field}")
        return v


class CandleCreate(CandleBase):
    """Schema for creating a candle."""
    pass


class CandleResponse(CandleBase):
    """Schema for candle API responses."""

    model_config = {"from_attributes": True}
    provider: str | None = None
    is_delayed: bool = False


class CandleQueryParams(BaseModel):
    """Query parameters for fetching candles."""

    timeframe: str = Field(default="1D", pattern=r"^(1m|5m|15m|1h|4h|1D|1W)$")
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    limit: int = Field(default=1000, ge=1, le=10000)


class SymbolInfo(BaseModel):
    """Info about an available symbol."""

    symbol: str
    timeframes: list[str]
    first_date: datetime
    last_date: datetime
    candle_count: int


class UploadResponse(BaseModel):
    """Response for data upload endpoint."""

    inserted: int
    duplicates_skipped: int
    errors: list[str]
