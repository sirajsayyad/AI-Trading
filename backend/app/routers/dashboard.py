"""Ownership-scoped dashboard analytics."""

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trading import (
    EquitySnapshot,
    PaperFill,
    PaperPortfolio,
    PaperPosition,
    RiskProfile,
    RiskViolation,
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def dashboard_summary(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    user_id = user["id"]
    portfolio = await db.scalar(select(PaperPortfolio).where(PaperPortfolio.user_id == user_id))
    fills = (
        await db.scalars(
            select(PaperFill)
            .where(PaperFill.user_id == user_id, PaperFill.side == "sell")
            .order_by(PaperFill.timestamp)
        )
    ).all()
    pnls = [fill.realized_pnl for fill in fills]
    wins, losses = [pnl for pnl in pnls if pnl > 0], [pnl for pnl in pnls if pnl < 0]
    gross_profit, gross_loss = sum(wins), abs(sum(losses))
    streak = 0
    if pnls:
        positive = pnls[-1] > 0
        for pnl in reversed(pnls):
            if (pnl > 0) != positive:
                break
            streak += 1
        if not positive:
            streak = -streak
    by_symbol: dict[str, float] = {}
    for fill in fills:
        by_symbol[fill.symbol] = by_symbol.get(fill.symbol, 0) + fill.realized_pnl
    positions = (
        await db.scalars(
            select(PaperPosition).where(
                PaperPosition.user_id == user_id, PaperPosition.quantity > 0
            )
        )
    ).all()
    violations = (
        await db.scalar(
            select(func.count()).select_from(RiskViolation).where(RiskViolation.user_id == user_id)
        )
        or 0
    )
    return {
        "paper_only": True,
        "equity": round(
            portfolio.cash_balance + sum(p.quantity * p.avg_entry_price for p in positions), 2
        )
        if portfolio
        else None,
        "cash": round(portfolio.cash_balance, 2) if portfolio else None,
        "realized_pnl": round(portfolio.realized_pnl, 2) if portfolio else None,
        "total_trades": len(pnls),
        "win_rate": round(len(wins) / len(pnls) * 100, 2) if pnls else 0,
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss else None,
        "expectancy": round(sum(pnls) / len(pnls), 2) if pnls else 0,
        "average_win": round(sum(wins) / len(wins), 2) if wins else 0,
        "average_loss": round(sum(losses) / len(losses), 2) if losses else 0,
        "current_streak": streak,
        "risk_violations": violations,
        "open_positions": len(positions),
        "best_symbol": max(by_symbol, key=by_symbol.get) if by_symbol else None,
        "worst_symbol": min(by_symbol, key=by_symbol.get) if by_symbol else None,
        "learning_progress": 0,
        "recent_trades": [
            {
                "id": f.id,
                "symbol": f.symbol,
                "timestamp": as_utc(f.timestamp),
                "realized_pnl": round(f.realized_pnl, 2),
            }
            for f in reversed(fills[-5:])
        ],
        "risk": await risk_summary(db, user_id, portfolio, positions),
    }


def as_utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=UTC)
        if value.tzinfo is None
        else value.astimezone(UTC)
    )


async def risk_summary(db, user_id, portfolio, positions):
    profile = await db.scalar(select(RiskProfile).where(RiskProfile.user_id == user_id))
    exposure = sum(p.quantity * p.avg_entry_price for p in positions)
    equity = portfolio.cash_balance + exposure if portfolio else None
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_pnl = await db.scalar(
        select(func.coalesce(func.sum(PaperFill.realized_pnl), 0)).where(
            PaperFill.user_id == user_id, PaperFill.timestamp >= midnight
        )
    )
    limit = (
        equity * profile.max_daily_loss_percent / 100 if equity is not None and profile else None
    )
    return {
        "exposure": round(exposure, 2) if portfolio else None,
        "daily_pnl": round(daily_pnl or 0, 2),
        "daily_loss_limit": round(limit, 2) if limit is not None else None,
        "daily_loss_used_percent": round(max(0, -(daily_pnl or 0)) / limit * 100, 2)
        if limit and limit > 0
        else None,
    }


def history_points(snapshots, days, now):
    """Calculate drawdown against the full recorded high, then filter and bound payload."""
    peak = 0.0
    points = []
    cutoff = now - timedelta(days=days) if days else None
    for snapshot in snapshots:
        peak = max(peak, snapshot.equity)
        timestamp = as_utc(snapshot.timestamp)
        if cutoff is None or timestamp >= cutoff:
            points.append(
                {
                    "timestamp": timestamp,
                    "equity": round(snapshot.equity, 2),
                    "drawdown": round((snapshot.equity - peak) / peak * 100, 4) if peak > 0 else 0,
                }
            )
    # Keep the final observation in each bucket; retain extremes separately in summary.
    count = len(points)
    sampled = points if count <= 500 else [points[round(i * (count - 1) / 499)] for i in range(500)]
    return {
        "points": sampled,
        "observation_count": count,
        "max_drawdown": min((p["drawdown"] for p in points), default=None),
    }


@router.get("/history")
async def dashboard_history(
    range: Literal["7D", "30D", "All"] = "30D",
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    snapshots = (
        await db.scalars(
            select(EquitySnapshot)
            .join(PaperPortfolio, EquitySnapshot.portfolio_id == PaperPortfolio.id)
            .where(PaperPortfolio.user_id == user["id"])
            .order_by(EquitySnapshot.timestamp, EquitySnapshot.id)
        )
    ).all()
    return history_points(
        snapshots, {"7D": 7, "30D": 30, "All": None}[range], datetime.now(UTC)
    )
