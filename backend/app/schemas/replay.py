"""
Pydantic schemas for replay endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ReplaySessionCreate(BaseModel):
    """Create a new replay session."""
    symbol: str = Field(..., min_length=1, max_length=20)
    timeframe: str = Field(default="1D", pattern=r"^(1m|5m|15m|1h|4h|1D|1W)$")
    start_date: str = Field(..., description="ISO format date")
    speed_multiplier: float = Field(default=1.0, ge=0.1, le=100.0)
    blind_mode: bool = False
    stored_only: bool = False


class ReplayControl(BaseModel):
    """Control commands for a replay session."""
    action: str = Field(..., pattern=r"^(pause|resume|jump|speed|step)$")
    value: Optional[str] = None  # For jump: date string; for speed: multiplier


class ReplayOrderCreate(BaseModel):
    """Place an order during replay."""
    side: str = Field(..., pattern=r"^(buy|sell)$")
    order_type: str = Field(default="market", pattern=r"^(market|limit|stop)$")
    quantity: float = Field(..., gt=0)
    price: Optional[float] = Field(default=None, gt=0)


class ReplaySessionResponse(BaseModel):
    """Response for replay session info."""
    id: str
    symbol: str
    timeframe: str
    start_date: str
    speed_multiplier: float
    blind_mode: bool
    status: str
    current_index: int
    total_candles: int
    orders_placed: int


class ReplayCandleMessage(BaseModel):
    """WebSocket message for a single candle."""
    index: int
    total: int
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    # These are omitted in blind mode
    symbol: Optional[str] = None
    date_display: Optional[str] = None
