"""
SQLAlchemy model for OHLCV candle data.
"""

from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Candle(Base):
    """OHLCV candle data stored in TimescaleDB hypertable."""

    __tablename__ = "candles"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    timeframe: Mapped[str] = mapped_column(String(4), primary_key=True)
    open: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(24, 4), nullable=False)

    __table_args__ = (
        Index("ix_candles_symbol_time", "symbol", "timestamp", "timeframe", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Candle {self.symbol} {self.timestamp} {self.timeframe}>"
