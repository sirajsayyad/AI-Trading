"""
SQLAlchemy models for replay sessions and orders.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import uuid


class ReplaySession(Base):
    """A historical market replay session."""

    __tablename__ = "replay_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(4), nullable=False, default="1D")
    start_date: Mapped[str] = mapped_column(String(30), nullable=False)
    end_date: Mapped[str] = mapped_column(String(30), nullable=True)
    speed_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    blind_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    # State
    status: Mapped[str] = mapped_column(String(20), default="created")  # created/playing/paused/completed
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    total_candles: Mapped[int] = mapped_column(Integer, default=0)

    # Results
    orders_placed: Mapped[int] = mapped_column(Integer, default=0)
    final_pnl: Mapped[float] = mapped_column(Float, nullable=True)
    results: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class ReplayOrder(Base):
    """An order placed during a replay session."""

    __tablename__ = "replay_orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # buy/sell
    order_type: Mapped[str] = mapped_column(String(10), nullable=False)  # market/limit/stop
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    fill_price: Mapped[float] = mapped_column(Float, nullable=True)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
