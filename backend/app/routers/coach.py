"""
Coach and curriculum API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.coach_service import get_trade_critique, ask_coach
from app.services.behavioral_analytics import analyze_behavior
from app.models.curriculum import Course, Module, Lesson
from app.models.trading import CoachReview, JournalEntry, PaperFill, RiskViolation
from app.routers.auth import get_current_user
from app.core.config import get_settings

router = APIRouter(tags=["AI Coach & Training"])


# ─── Schemas ─────────────────────────────────────────────

class CritiqueRequest(BaseModel):
    trades: list[dict] = Field(default_factory=list)
    session_summary: Optional[dict] = None
    context: str = ""


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    trade_context: Optional[list[dict]] = None
    conversation_history: Optional[list[dict]] = None


class BehaviorRequest(BaseModel):
    trades: list[dict] = Field(default_factory=list)
    account_size: float = 100000.0


# ─── Coach Endpoints ─────────────────────────────────────

@router.post("/coach/critique")
async def critique_trades(req: CritiqueRequest):
    """Get AI coaching feedback on trades."""
    feedback = await get_trade_critique(
        trades=req.trades,
        session_summary=req.session_summary,
        context=req.context,
    )
    return {"feedback": feedback}


@router.post("/coach/ask")
async def ask_question(req: AskRequest):
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
        model="claude-sonnet-4-6" if settings.anthropic_api_key else "offline",
        input_references=[fill.order_id for fill in fills],
        response=feedback,
    )
    db.add(review)
    await db.flush()
    return {"review_id": review.id, "feedback": feedback,
            "trade_count": len(trades), "paper_only": True}


# ─── Curriculum Endpoints ────────────────────────────────

@router.get("/courses")
async def list_courses(db: AsyncSession = Depends(get_db)):
    """List all published courses."""
    stmt = (
        select(Course)
        .where(Course.is_published == True)
        .order_by(Course.order_index)
    )
    result = await db.execute(stmt)
    courses = result.scalars().all()

    return [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "difficulty": c.difficulty,
        }
        for c in courses
    ]


@router.get("/courses/{course_id}")
async def get_course(course_id: str, db: AsyncSession = Depends(get_db)):
    """Get course details with modules and lessons."""
    # Get course
    stmt = select(Course).where(Course.id == course_id)
    result = await db.execute(stmt)
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get modules
    stmt = select(Module).where(Module.course_id == course_id).order_by(Module.order_index)
    result = await db.execute(stmt)
    modules = result.scalars().all()

    # Get lessons for each module
    module_data = []
    for mod in modules:
        stmt = select(Lesson).where(Lesson.module_id == mod.id).order_by(Lesson.order_index)
        result = await db.execute(stmt)
        lessons = result.scalars().all()

        module_data.append({
            "id": mod.id,
            "title": mod.title,
            "description": mod.description,
            "lessons": [
                {
                    "id": l.id,
                    "title": l.title,
                    "has_replay": l.replay_symbol is not None,
                }
                for l in lessons
            ],
        })

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "difficulty": course.difficulty,
        "modules": module_data,
    }


@router.get("/lessons/{lesson_id}")
async def get_lesson(lesson_id: str, db: AsyncSession = Depends(get_db)):
    """Get lesson content with optional replay scenario."""
    stmt = select(Lesson).where(Lesson.id == lesson_id)
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    response = {
        "id": lesson.id,
        "title": lesson.title,
        "content_markdown": lesson.content_markdown,
    }

    if lesson.replay_symbol:
        response["replay_scenario"] = {
            "symbol": lesson.replay_symbol,
            "timeframe": lesson.replay_timeframe,
            "start_date": lesson.replay_start_date,
            "blind_mode": lesson.replay_blind_mode,
        }

    return response
