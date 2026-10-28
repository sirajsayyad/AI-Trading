"""
Replay service — manages replay sessions with candle streaming and order execution.
"""

from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.execution import (
    CandleData,
    CommissionModel,
    ExecutionSimulator,
    Order,
    OrderSide,
    OrderType,
    SlippageModel,
)
from app.models.candle import Candle
from app.models.replay import ReplaySession
from app.services.market_data import fetch_live_candles

# In-memory session state (for active sessions)
_active_sessions: dict[str, dict] = {}


async def create_session(
    db: AsyncSession,
    symbol: str,
    timeframe: str,
    start_date: str,
    speed_multiplier: float = 1.0,
    blind_mode: bool = False,
) -> dict:
    """Create a new replay session and load candle data."""

    # Count available candles
    start = datetime.fromisoformat(start_date)
    stmt = (
        select(Candle)
        .where(Candle.symbol == symbol.upper())
        .where(Candle.timeframe == timeframe)
        .where(Candle.timestamp >= start)
        .order_by(Candle.timestamp.asc())
    )
    result = await db.execute(stmt)
    candles = result.scalars().all()

    if not candles:
        try:
            provider_candles = await fetch_live_candles(
                symbol=symbol,
                timeframe=timeframe,
                limit=5000,
                start_date=start_date,
            )
        except (RuntimeError, ValueError, httpx.HTTPError) as exc:
            return {"error": str(exc)}

        if not provider_candles:
            return {"error": f"No candle data for {symbol} ({timeframe}) from {start_date}"}

        candle_list = [
            CandleData(
                symbol=candle["symbol"],
                timestamp=candle["timestamp"],
                open=candle["open"],
                high=candle["high"],
                low=candle["low"],
                close=candle["close"],
                volume=candle["volume"],
                timeframe=candle["timeframe"],
            )
            for candle in provider_candles
        ]
    else:
        candle_list = [
            CandleData(
                symbol=c.symbol,
                timestamp=c.timestamp,
                open=float(c.open),
                high=float(c.high),
                low=float(c.low),
                close=float(c.close),
                volume=float(c.volume),
                timeframe=c.timeframe,
            )
            for c in candles
        ]

    # Create session record
    session = ReplaySession(
        symbol=symbol.upper(),
        timeframe=timeframe,
        start_date=start_date,
        speed_multiplier=speed_multiplier,
        blind_mode=blind_mode,
        total_candles=len(candle_list),
        status="created",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Cache candle data and simulator in memory
    _active_sessions[session.id] = {
        "candles": candle_list,
        "index": 0,
        "speed": speed_multiplier,
        "blind_mode": blind_mode,
        "status": "created",
        "paused": False,
        "simulator": ExecutionSimulator(
            slippage=SlippageModel(basis_points=5.0),
            commission=CommissionModel(flat_fee=1.0, percentage=0.001),
        ),
    }

    return {
        "session_id": session.id,
        "symbol": session.symbol if not blind_mode else "HIDDEN",
        "timeframe": session.timeframe,
        "total_candles": session.total_candles,
        "speed_multiplier": speed_multiplier,
        "blind_mode": blind_mode,
    }


def get_session_state(session_id: str) -> dict | None:
    """Get in-memory session state."""
    return _active_sessions.get(session_id)


async def get_next_candle(session_id: str) -> dict | None:
    """Get the next candle for streaming."""
    state = _active_sessions.get(session_id)
    if not state:
        return None

    if state["paused"]:
        return {"paused": True}

    candles = state["candles"]
    idx = state["index"]

    if idx >= len(candles):
        state["status"] = "completed"
        return {"completed": True}

    candle = candles[idx]
    state["index"] = idx + 1

    # Process fills for this bar
    fills = state["simulator"].process_bar(candle)

    # Build message
    msg = {
        "index": idx,
        "total": len(candles),
        "timestamp": candle.timestamp.isoformat() if not state["blind_mode"] else f"Bar {idx + 1}",
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
    }

    if not state["blind_mode"]:
        msg["symbol"] = candle.symbol
        msg["date_display"] = candle.timestamp.strftime("%Y-%m-%d %H:%M")

    # Include fill info if any
    if fills:
        msg["fills"] = [
            {
                "order_id": f.order_id,
                "side": f.side.value,
                "quantity": f.quantity,
                "price": round(f.net_price, 4),
                "commission": round(f.commission, 4),
            }
            for f in fills
        ]

    # Include position info
    positions = state["simulator"].positions
    if positions:
        msg["positions"] = {
            sym: {
                "quantity": pos.quantity,
                "avg_entry": round(pos.avg_entry_price, 4),
                "unrealized_pnl": round(pos.unrealized_pnl, 2),
                "realized_pnl": round(pos.realized_pnl, 2),
            }
            for sym, pos in positions.items()
        }

    return msg


def place_replay_order(
    session_id: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
) -> dict:
    """Place an order in the replay session."""
    state = _active_sessions.get(session_id)
    if not state:
        return {"error": "Session not found"}

    if state["status"] == "completed":
        return {"error": "Session already completed"}

    simulator = state["simulator"]
    candles = state["candles"]
    idx = max(0, state["index"] - 1)
    symbol = candles[idx].symbol if candles else "UNKNOWN"

    order = Order(
        symbol=symbol,
        side=OrderSide(side),
        order_type=OrderType(order_type),
        quantity=quantity,
        price=price,
    )

    submitted = simulator.submit_order(order)

    return {
        "order_id": submitted.id,
        "status": submitted.status.value,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
    }


def control_session(session_id: str, action: str, value: str = None) -> dict:
    """Control a replay session: pause, resume, speed, jump."""
    state = _active_sessions.get(session_id)
    if not state:
        return {"error": "Session not found"}

    if action == "pause":
        state["paused"] = True
        state["status"] = "paused"
        return {"status": "paused"}

    elif action == "resume":
        state["paused"] = False
        state["status"] = "playing"
        return {"status": "playing"}

    elif action == "speed":
        try:
            speed = float(value)
            state["speed"] = max(0.1, min(100.0, speed))
            return {"speed": state["speed"]}
        except (ValueError, TypeError):
            return {"error": "Invalid speed value"}

    elif action == "jump":
        try:
            target_date = datetime.fromisoformat(value)
            candles = state["candles"]
            for i, c in enumerate(candles):
                if c.timestamp >= target_date:
                    state["index"] = i
                    return {"jumped_to_index": i, "timestamp": c.timestamp.isoformat()}
            return {"error": "Date is beyond available data"}
        except (ValueError, TypeError):
            return {"error": "Invalid date format"}

    return {"error": f"Unknown action: {action}"}


def get_session_summary(session_id: str) -> dict:
    """Get summary after session completion."""
    state = _active_sessions.get(session_id)
    if not state:
        return {"error": "Session not found"}

    simulator = state["simulator"]
    fills = simulator.fills

    total_pnl = sum(pos.realized_pnl for pos in simulator.positions.values())
    total_commission = sum(f.commission for f in fills)

    return {
        "session_id": session_id,
        "total_bars": len(state["candles"]),
        "bars_viewed": state["index"],
        "orders_placed": len(fills),
        "total_pnl": round(total_pnl, 2),
        "total_commission": round(total_commission, 2),
        "net_pnl": round(total_pnl - total_commission, 2),
        "positions": {
            sym: {
                "quantity": pos.quantity,
                "realized_pnl": round(pos.realized_pnl, 2),
            }
            for sym, pos in simulator.positions.items()
        },
        "fills": [
            {
                "order_id": f.order_id,
                "side": f.side.value,
                "quantity": f.quantity,
                "price": round(f.net_price, 4),
                "timestamp": f.timestamp.isoformat(),
            }
            for f in fills
        ],
    }


def cleanup_session(session_id: str):
    """Remove session from memory."""
    _active_sessions.pop(session_id, None)
