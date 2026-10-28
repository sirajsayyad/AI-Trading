"""
SQLAlchemy models for persisting backtest runs and results.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import uuid


class BacktestRun(Base):
    """Persisted backtest run with config and results."""

    __tablename__ = "backtest_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(4), nullable=False, default="1D")
    start_date: Mapped[str] = mapped_column(String(30), nullable=False)
    end_date: Mapped[str] = mapped_column(String(30), nullable=False)
    initial_capital: Mapped[float] = mapped_column(Float, default=100000.0)

    # Strategy params stored as JSON
    strategy_params: Mapped[dict] = mapped_column(JSON, default=dict)

    # Execution config
    slippage_bps: Mapped[float] = mapped_column(Float, default=5.0)
    commission_flat: Mapped[float] = mapped_column(Float, default=1.0)
    commission_pct: Mapped[float] = mapped_column(Float, default=0.001)

    # Results stored as JSON
    results: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Metadata
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/running/completed/failed
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BacktestRun {self.id[:8]} {self.strategy_name} {self.symbol}>"
