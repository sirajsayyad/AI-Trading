"""
Coach and curriculum API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.coach_service import get_trade_critique, ask_coach, limit_requests
from app.services.behavioral_analytics import analyze_behavior
from app.models.trading import CoachReview, JournalEntry, PaperFill, RiskViolation
from app.routers.auth import get_current_user
from app.core.config import get_settings

router = APIRouter(tags=["AI Coach & Training"])


# ─── Schemas ─────────────────────────────────────────────

class CritiqueRequest(BaseModel):
    trades: list[dict] = Field(default_factory=list, max_length=100)
    session_summary: Optional[dict] = None
    context: str = Field("", max_length=12000)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    trade_context: Optional[list[dict]] = Field(None, max_length=50)
    conversation_history: Optional[list[dict]] = Field(None, max_length=10)


class BehaviorRequest(BaseModel):
    trades: list[dict] = Field(default_factory=list, max_length=100)
    account_size: float = 100000.0


# ─── Coach Endpoints ─────────────────────────────────────

@router.post("/coach/critique")
async def critique_trades(req: CritiqueRequest, user: dict = Depends(get_current_user)):
    limit_requests(user["id"])
    """Get AI coaching feedback on trades."""
    feedback = await get_trade_critique(
        trades=req.trades,
        session_summary=req.session_summary,
        context=req.context,
    )
    return {"feedback": feedback}


@router.post("/coach/ask")
async def ask_question(req: AskRequest, user: dict = Depends(get_current_user)):
    limit_requests(user["id"])
    """Ask the AI coach a free-form question."""
    answer = await ask_coach(
        question=req.question,
        trade_context=req.trade_context,
        conversation_history=req.conversation_history,
    )
    return {"answer": answer}


@router.post("/coach/behavior")
async def analyze_trading_behavior(req: BehaviorRequest):
    """Analyze trade history for behavioral patterns."""
    flags = analyze_behavior(trades=req.trades, account_size=req.account_size)
    return {"flags": flags, "total_trades_analyzed": len(req.trades)}


@router.post("/coach/review-my-trades")
async def review_my_trades(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Coach from the authenticated user's real paper-trade evidence."""
    user_id = current_user["id"]
    limit_requests(user_id)
    fills = (await db.scalars(
        select(PaperFill).where(PaperFill.user_id == user_id).order_by(PaperFill.timestamp.desc()).limit(50)
    )).all()
    journals = (await db.scalars(
        select(JournalEntry).where(JournalEntry.user_id == user_id).order_by(JournalEntry.created_at.desc()).limit(50)
    )).all()
    violations = (await db.scalars(
        select(RiskViolation).where(RiskViolation.user_id == user_id).order_by(RiskViolation.created_at.desc()).limit(50)
    )).all()
    trades = [{"id": fill.order_id, "symbol": fill.symbol, "side": fill.side,
               "exit_price": fill.price, "pnl": fill.realized_pnl} for fill in fills]
    context = {
        "journal_entries": [{"id": item.id, "trade_id": item.trade_id,
                              "mistakes": item.mistakes, "lessons": item.lessons_learned}
                             for item in journals],
        "risk_violations": [{"rule": item.rule, "message": item.message}
                            for item in violations],
    }
    feedback = await get_trade_critique(trades, context, str(context))
    settings = get_settings()
    review = CoachReview(
        user_id=user_id,
        model=settings.ollama_model,
        input_references=[fill.order_id for fill in fills],
        response=feedback,
    )
    db.add(review)
    await db.flush()
    return {"review_id": review.id, "feedback": feedback,
            "trade_count": len(trades), "paper_only": True}


# ─── Curriculum Endpoints ────────────────────────────────
