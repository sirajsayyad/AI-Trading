"""Authenticated risk, watchlist, paper portfolio, and journal APIs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trading import (
    EquitySnapshot, JournalEntry, PaperFill, PaperOrder, PaperPortfolio,
    PaperPosition, RiskProfile, RiskViolation, WatchlistItem,
)
from app.routers.auth import get_current_user
from app.services.market_data import fetch_live_quote
from app.services.paper_trading import preview_order, simulated_fill

router = APIRouter(tags=["Paper Trading"])


class RiskProfileInput(BaseModel):
    starting_balance: float = Field(default=100000, gt=0, le=100_000_000)
    max_risk_percent: float = Field(default=1, gt=0, le=10)
    max_daily_loss_percent: float = Field(default=3, gt=0, le=25)
    max_open_positions: int = Field(default=5, ge=1, le=100)
    max_position_value_percent: float = Field(default=20, gt=0, le=100)
    min_reward_risk_ratio: float = Field(default=2, ge=0, le=20)
    require_stop_loss: bool = True
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    trading_session: str = Field(default="regular", pattern=r"^(regular|extended|any)$")
    cooldown_after_losses: int = Field(default=0, ge=0, le=20)


class OrderInput(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Za-z./-]+$")
    side: str = Field(..., pattern=r"^(buy|sell)$")
    order_type: str = Field(default="market", pattern=r"^(market|limit|stop)$")
    quantity: float = Field(..., gt=0)
    limit_price: float | None = Field(default=None, gt=0)
    stop_price: float | None = Field(default=None, gt=0)
    take_profit_price: float | None = Field(default=None, gt=0)
    idempotency_key: str = Field(..., min_length=8, max_length=64)


class JournalInput(BaseModel):
    trade_id: str | None = None
    symbol: str = Field(..., min_length=1, max_length=20)
    strategy: str = Field(default="", max_length=100)
    setup: str = Field(default="", max_length=100)
    entry_reason: str = Field(default="", max_length=4000)
    exit_reason: str = Field(default="", max_length=4000)
    stop_price: float | None = Field(default=None, gt=0)
    target_price: float | None = Field(default=None, gt=0)
    confidence: int = Field(default=5, ge=1, le=10)
    emotion_before: str = Field(default="neutral", max_length=50)
    emotion_during: str = Field(default="neutral", max_length=50)
    emotion_after: str = Field(default="neutral", max_length=50)
    mistakes: str = Field(default="", max_length=4000)
    lessons_learned: str = Field(default="", max_length=4000)
    review: str = Field(default="", max_length=8000)
    screenshot_url: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=20)


def risk_dict(profile: RiskProfile) -> dict:
    return {key: getattr(profile, key) for key in RiskProfileInput.model_fields}


def journal_dict(entry: JournalEntry) -> dict:
    return {column.name: getattr(entry, column.name) for column in entry.__table__.columns}


async def get_or_create_risk(db: AsyncSession, user_id: str) -> RiskProfile:
    profile = await db.scalar(select(RiskProfile).where(RiskProfile.user_id == user_id))
    if not profile:
        profile = RiskProfile(user_id=user_id)
        db.add(profile)
        await db.flush()
    return profile


async def get_or_create_portfolio(db: AsyncSession, user_id: str) -> PaperPortfolio:
    portfolio = await db.scalar(select(PaperPortfolio).where(PaperPortfolio.user_id == user_id))
    if not portfolio:
        risk = await get_or_create_risk(db, user_id)
        portfolio = PaperPortfolio(user_id=user_id, starting_balance=risk.starting_balance, cash_balance=risk.starting_balance)
        db.add(portfolio)
        await db.flush()
    return portfolio


@router.get("/risk/profile")
async def read_risk_profile(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return risk_dict(await get_or_create_risk(db, user["id"]))


@router.put("/risk/profile")
async def update_risk_profile(payload: RiskProfileInput, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_risk(db, user["id"])
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    return risk_dict(profile)


async def order_context(db: AsyncSession, user_id: str, payload: OrderInput, market_price: float) -> tuple[PaperPortfolio, RiskProfile, PaperPosition | None, dict]:
    portfolio = await get_or_create_portfolio(db, user_id)
    risk = await get_or_create_risk(db, user_id)
    position = await db.scalar(select(PaperPosition).where(PaperPosition.portfolio_id == portfolio.id, PaperPosition.symbol == payload.symbol.upper()))
    open_positions = await db.scalar(select(func.count()).select_from(PaperPosition).where(PaperPosition.portfolio_id == portfolio.id, PaperPosition.quantity > 0)) or 0
    daily_pnl = await db.scalar(select(func.coalesce(func.sum(PaperFill.realized_pnl), 0)).where(PaperFill.user_id == user_id, PaperFill.timestamp >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))) or 0
    equity = portfolio.cash_balance + sum(row.quantity * row.avg_entry_price for row in (await db.scalars(select(PaperPosition).where(PaperPosition.portfolio_id == portfolio.id))).all())
    result = preview_order(
        cash=portfolio.cash_balance, equity=equity, price=market_price, quantity=payload.quantity,
        side=payload.side, stop_price=payload.stop_price, take_profit_price=payload.take_profit_price,
        max_risk_percent=risk.max_risk_percent, max_position_value_percent=risk.max_position_value_percent,
        min_reward_risk_ratio=risk.min_reward_risk_ratio, require_stop_loss=risk.require_stop_loss,
        open_positions=open_positions, max_open_positions=risk.max_open_positions, daily_pnl=float(daily_pnl),
        max_daily_loss_percent=risk.max_daily_loss_percent, opening_new_position=not position or position.quantity <= 0,
    )
    if payload.side == "sell" and (not position or position.quantity < payload.quantity):
        result["errors"].append("Sell quantity exceeds the open paper position")
        result["allowed"] = False
    return portfolio, risk, position, result


@router.post("/paper/orders/preview")
async def preview_paper_order(payload: OrderInput, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    quote = await fetch_live_quote(payload.symbol)
    _, _, _, result = await order_context(db, user["id"], payload, quote["price"])
    return {**result, "symbol": payload.symbol.upper(), "market_price": quote["price"], "data_timestamp": quote["timestamp"], "provider": quote["provider"], "paper_only": True}


@router.post("/paper/orders")
async def submit_paper_order(payload: OrderInput, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(PaperOrder).where(PaperOrder.user_id == user["id"], PaperOrder.idempotency_key == payload.idempotency_key))
    if existing:
        return {"id": existing.id, "status": existing.status, "idempotent_replay": True}
    quote = await fetch_live_quote(payload.symbol)
    portfolio, _, position, risk_result = await order_context(db, user["id"], payload, quote["price"])
    now = datetime.now(timezone.utc)
    order = PaperOrder(
        user_id=user["id"], portfolio_id=portfolio.id, symbol=payload.symbol.upper(), side=payload.side,
        order_type=payload.order_type, quantity=payload.quantity, submitted_price=quote["price"],
        limit_price=payload.limit_price, stop_price=payload.stop_price, take_profit_price=payload.take_profit_price,
        status="pending", idempotency_key=payload.idempotency_key, data_timestamp=quote["timestamp"], risk_result=risk_result,
    )
    db.add(order)
    await db.flush()
    if not risk_result["allowed"]:
        order.status = "rejected"
        order.rejection_reason = "; ".join(risk_result["errors"])
        for message in risk_result["errors"]:
            db.add(RiskViolation(user_id=user["id"], order_id=order.id, rule="order_validation", message=message))
        return {"id": order.id, "status": order.status, "errors": risk_result["errors"]}

    if payload.order_type != "market":
        return {"id": order.id, "status": "pending", "paper_only": True}

    fill_price, commission, slippage = simulated_fill(quote["price"], payload.quantity, payload.side)
    realized = 0.0
    if payload.side == "buy":
        portfolio.cash_balance -= fill_price * payload.quantity + commission
        if not position:
            position = PaperPosition(user_id=user["id"], portfolio_id=portfolio.id, symbol=payload.symbol.upper())
            db.add(position)
        total_cost = position.avg_entry_price * position.quantity + fill_price * payload.quantity
        position.quantity += payload.quantity
        position.avg_entry_price = total_cost / position.quantity
        position.stop_price = payload.stop_price
        position.take_profit_price = payload.take_profit_price
    else:
        realized = (fill_price - position.avg_entry_price) * payload.quantity - commission  # type: ignore[union-attr]
        portfolio.cash_balance += fill_price * payload.quantity - commission
        portfolio.realized_pnl += realized
        position.quantity -= payload.quantity  # type: ignore[union-attr]
        position.realized_pnl += realized  # type: ignore[union-attr]
    portfolio.total_fees += commission
    order.status, order.fill_price, order.commission, order.slippage, order.filled_at = "filled", fill_price, commission, slippage, now
    db.add(PaperFill(order_id=order.id, user_id=user["id"], symbol=order.symbol, side=order.side, quantity=order.quantity, price=fill_price, commission=commission, slippage=slippage, realized_pnl=realized, timestamp=now))
    db.add(EquitySnapshot(portfolio_id=portfolio.id, equity=portfolio.cash_balance + sum(row.quantity * row.avg_entry_price for row in (await db.scalars(select(PaperPosition).where(PaperPosition.portfolio_id == portfolio.id))).all()), cash=portfolio.cash_balance))
    return {"id": order.id, "status": "filled", "fill_price": fill_price, "commission": commission, "realized_pnl": round(realized, 2), "paper_only": True}


@router.get("/paper/portfolio")
async def paper_portfolio(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    portfolio = await get_or_create_portfolio(db, user["id"])
    positions = (await db.scalars(select(PaperPosition).where(PaperPosition.portfolio_id == portfolio.id, PaperPosition.quantity > 0))).all()
    position_data, market_value, unrealized = [], 0.0, 0.0
    for position in positions:
        try:
            mark = float((await fetch_live_quote(position.symbol))["price"])
        except Exception:
            mark = position.avg_entry_price
        pnl = (mark - position.avg_entry_price) * position.quantity
        market_value += mark * position.quantity
        unrealized += pnl
        position_data.append({"id": position.id, "symbol": position.symbol, "quantity": position.quantity, "avg_entry_price": position.avg_entry_price, "mark_price": mark, "unrealized_pnl": round(pnl, 2), "stop_price": position.stop_price, "take_profit_price": position.take_profit_price})
    orders = (await db.scalars(select(PaperOrder).where(PaperOrder.user_id == user["id"]).order_by(PaperOrder.created_at.desc()).limit(100))).all()
    return {"paper_only": True, "cash": round(portfolio.cash_balance, 2), "buying_power": round(portfolio.cash_balance, 2), "market_value": round(market_value, 2), "equity": round(portfolio.cash_balance + market_value, 2), "realized_pnl": round(portfolio.realized_pnl, 2), "unrealized_pnl": round(unrealized, 2), "total_fees": round(portfolio.total_fees, 2), "positions": position_data, "orders": [{"id": item.id, "symbol": item.symbol, "side": item.side, "quantity": item.quantity, "status": item.status, "fill_price": item.fill_price, "created_at": item.created_at} for item in orders]}


@router.post("/watchlist/{symbol}")
async def add_watchlist(symbol: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    normalized = symbol.upper().strip()
    existing = await db.scalar(select(WatchlistItem).where(WatchlistItem.user_id == user["id"], WatchlistItem.symbol == normalized))
    if not existing:
        db.add(WatchlistItem(user_id=user["id"], symbol=normalized))
    return {"symbol": normalized}


@router.get("/watchlist")
async def read_watchlist(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    items = (await db.scalars(select(WatchlistItem).where(WatchlistItem.user_id == user["id"]).order_by(WatchlistItem.created_at))).all()
    return [{"id": item.id, "symbol": item.symbol} for item in items]


@router.delete("/watchlist/{symbol}", status_code=204)
async def delete_watchlist(symbol: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(WatchlistItem).where(WatchlistItem.user_id == user["id"], WatchlistItem.symbol == symbol.upper()))
    if item:
        await db.delete(item)


@router.post("/journal")
async def create_journal(payload: JournalInput, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.trade_id:
        owned = await db.scalar(select(PaperOrder.id).where(PaperOrder.id == payload.trade_id, PaperOrder.user_id == user["id"]));
        if not owned:
            raise HTTPException(404, "Trade not found")
    entry = JournalEntry(user_id=user["id"], **payload.model_dump())
    db.add(entry)
    await db.flush()
    return journal_dict(entry)


@router.get("/journal")
async def list_journal(symbol: str | None = None, strategy: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(JournalEntry).where(JournalEntry.user_id == user["id"])
    if symbol:
        query = query.where(JournalEntry.symbol == symbol.upper())
    if strategy:
        query = query.where(JournalEntry.strategy == strategy)
    entries = (await db.scalars(query.order_by(JournalEntry.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return [journal_dict(entry) for entry in entries]


@router.put("/journal/{entry_id}")
async def update_journal(entry_id: str, payload: JournalInput, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entry = await db.scalar(select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.user_id == user["id"]))
    if not entry:
        raise HTTPException(404, "Journal entry not found")
    for key, value in payload.model_dump().items():
        setattr(entry, key, value)
    return journal_dict(entry)


@router.delete("/journal/{entry_id}", status_code=204)
async def delete_journal(entry_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entry = await db.scalar(select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.user_id == user["id"]))
    if not entry:
        raise HTTPException(404, "Journal entry not found")
    await db.delete(entry)
