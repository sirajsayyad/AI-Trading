"""
Replay API endpoints with WebSocket streaming.
"""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.replay import ReplayControl, ReplayOrderCreate, ReplaySessionCreate
from app.services.replay_service import (
    control_session,
    create_session,
    get_next_candle,
    get_session_state,
    get_session_summary,
    place_replay_order,
)

router = APIRouter(prefix="/replay", tags=["Replay"])


@router.post("/session")
async def create_replay_session(
    config: ReplaySessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new replay session."""
    result = await create_session(
        db=db,
        symbol=config.symbol,
        timeframe=config.timeframe,
        start_date=config.start_date,
        speed_multiplier=config.speed_multiplier,
        blind_mode=config.blind_mode,
        stored_only=config.stored_only,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.websocket("/{session_id}/stream")
async def replay_stream(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for streaming candles during replay."""
    await websocket.accept()

    state = get_session_state(session_id)
    if not state:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close()
        return

    state["status"] = "playing"
    state["paused"] = False

    try:
        while True:
            candle_msg = await get_next_candle(session_id)

            if candle_msg is None:
                await websocket.send_json({"error": "Session expired"})
                break

            if candle_msg.get("completed"):
                summary = get_session_summary(session_id)
                await websocket.send_json({"type": "completed", "summary": summary})
                break

            if candle_msg.get("paused"):
                await asyncio.sleep(0.1)
                # Check for incoming messages while paused
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    msg = json.loads(data)
                    await _handle_ws_message(session_id, msg, websocket)
                except TimeoutError:
                    pass
                continue

            await websocket.send_json({"type": "candle", "data": candle_msg})

            # Calculate delay based on speed
            speed = state.get("speed", 1.0)
            delay = max(0.01, 1.0 / speed)
            await asyncio.sleep(delay)

            # Check for incoming control messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                msg = json.loads(data)
                await _handle_ws_message(session_id, msg, websocket)
            except TimeoutError:
                pass

    except WebSocketDisconnect:
        pass
    finally:
        pass  # Keep session state for summary retrieval


async def _handle_ws_message(session_id: str, msg: dict, websocket: WebSocket):
    """Handle incoming WebSocket messages during replay."""
    msg_type = msg.get("type", "")

    if msg_type == "control":
        result = control_session(session_id, msg.get("action", ""), msg.get("value"))
        await websocket.send_json({"type": "control_response", "data": result})

    elif msg_type == "order":
        result = place_replay_order(
            session_id=session_id,
            side=msg.get("side", "buy"),
            order_type=msg.get("order_type", "market"),
            quantity=float(msg.get("quantity", 0)),
            price=float(msg["price"]) if msg.get("price") else None,
        )
        await websocket.send_json({"type": "order_response", "data": result})


@router.post("/{session_id}/control")
async def control_replay(
    session_id: str,
    control: ReplayControl,
):
    """Control a replay session (pause/resume/jump/speed)."""
    result = control_session(session_id, control.action, control.value)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/{session_id}/order")
async def place_order(
    session_id: str,
    order: ReplayOrderCreate,
):
    """Place an order during replay."""
    result = place_replay_order(
        session_id=session_id,
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        price=order.price,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/{session_id}/summary")
async def session_summary(session_id: str):
    """Get summary of a replay session."""
    result = get_session_summary(session_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
