"""Risk-management endpoints for simulated trading."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.risk_service import calculate_position_size

router = APIRouter(prefix="/risk", tags=["Risk Management"])


class PositionSizeRequest(BaseModel):
    account_balance: float = Field(..., gt=0)
    risk_percent: float = Field(..., gt=0, le=100)
    entry_price: float = Field(..., gt=0)
    stop_price: float = Field(..., gt=0)
    commission_per_trade: float = Field(default=0, ge=0)


@router.post("/position-size")
async def position_size(request: PositionSizeRequest):
    try:
        return calculate_position_size(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
