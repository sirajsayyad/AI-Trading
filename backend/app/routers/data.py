"""
Market data API endpoints.
"""

import asyncio
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.candle import Candle
from app.schemas.candle import CandleResponse, SymbolInfo, UploadResponse
from app.services.data_ingestion import IngestionService
from app.services.market_data import fetch_live_candles, fetch_live_quote

router = APIRouter(prefix="/data", tags=["Market Data"])


@router.websocket("/stream/{symbol}")
async def stream_quote(websocket: WebSocket, symbol: str):
    """Backend-owned quote stream with reconnect-friendly heartbeat messages."""
    await websocket.accept()
    try:
        while True:
            try:
                await websocket.send_json(jsonable_encoder({"type": "quote", "data": await fetch_live_quote(symbol)}))
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                await websocket.send_json({"type": "stale", "detail": str(exc)})
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return


@router.get("/symbols", response_model=list[SymbolInfo])
async def list_symbols(db: AsyncSession = Depends(get_db)):
    """List all available symbols with date ranges and candle counts."""
    stmt = (
        select(
            Candle.symbol,
            func.array_agg(distinct(Candle.timeframe)).label("timeframes"),
            func.min(Candle.timestamp).label("first_date"),
            func.max(Candle.timestamp).label("last_date"),
            func.count().label("candle_count"),
        )
        .group_by(Candle.symbol)
        .order_by(Candle.symbol)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        SymbolInfo(
            symbol=row.symbol,
            timeframes=sorted(row.timeframes),
            first_date=row.first_date,
            last_date=row.last_date,
            candle_count=row.candle_count,
        )
        for row in rows
    ]


@router.get("/{symbol}/candles", response_model=list[CandleResponse])
async def get_candles(
    symbol: str,
    timeframe: str = Query(default="1D", pattern=r"^(1m|5m|15m|1h|4h|1D|1W)$"),
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=1000, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """Get OHLCV candles for a symbol with optional date range filter."""
    stmt = (
        select(Candle)
        .where(Candle.symbol == symbol.upper())
        .where(Candle.timeframe == timeframe)
        .order_by(Candle.timestamp.asc())
    )

    if start:
        stmt = stmt.where(Candle.timestamp >= start)
    if end:
        stmt = stmt.where(Candle.timestamp <= end)

    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    candles = result.scalars().all()

    if not candles:
        raise HTTPException(
            status_code=404,
            detail=f"No candles found for {symbol.upper()} ({timeframe})"
        )

    return candles


@router.get("/{symbol}/live-candles", response_model=list[CandleResponse])
async def get_live_candles(
    symbol: str,
    timeframe: str = Query(default="1D", pattern=r"^(1m|5m|15m|1h|4h|1D|1W)$"),
    limit: int = Query(default=100, ge=1, le=5000),
):
    """Fetch candles from Twelve Data without exposing its API key."""
    try:
        return await fetch_live_candles(symbol, timeframe, limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Market data provider error: {exc}") from exc


@router.get("/{symbol}/live-quote")
async def get_live_quote(symbol: str):
    """Fetch the latest provider quote and previous-close movement."""
    try:
        return await fetch_live_quote(symbol)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Market data provider error: {exc}") from exc


@router.post("/upload", response_model=UploadResponse)
async def upload_data(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload CSV or JSON historical data file."""
    # Determine file type
    filename = file.filename or ""
    if filename.endswith(".csv"):
        file_type = "csv"
    elif filename.endswith(".json"):
        file_type = "json"
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a .csv or .json file."
        )

    raw_data = await file.read()
    if not raw_data:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    service = IngestionService(db)
    result = await service.ingest(raw_data, file_type)

    return UploadResponse(**result)
