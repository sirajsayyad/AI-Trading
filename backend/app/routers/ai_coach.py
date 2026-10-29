"""Authenticated, persistent lesson-aware local AI chat. No executable model tools."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.ai_chat import AIConversation, AIMessage
from app.models.curriculum import Module
from app.routers.auth import get_current_user
from app.routers.curriculum import published_course, require_enrollment
from app.services.coach_service import generate_reply, limit_requests

router = APIRouter(prefix="/ai-coach", tags=["AI Coach Chat"])
_busy_users: set[str] = set()


class SimulationContext(BaseModel):
    kind: Literal["replay", "backtest"]
    symbol: str = Field(min_length=1, max_length=20)
    metrics: dict[str, float | str | None] = Field(default_factory=dict, max_length=30)
    configuration: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, max_length=30
    )

    @model_validator(mode="after")
    def bounded_context(self):
        try:
            serialized = json.dumps(self.model_dump(), allow_nan=False)
        except ValueError as exc:
            raise ValueError("Simulation values must be finite") from exc
        if len(serialized) > 8000 or any(
            len(key) > 80 for key in [*self.metrics, *self.configuration]
        ):
            raise ValueError("Simulation context is too large")
        return self


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    simulationContext: SimulationContext | None = None
    conversationId: str | None = Field(None, max_length=36)
    courseId: str | None = Field(None, max_length=36)
    lessonId: str | None = Field(None, max_length=36)

    @field_validator("message")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Enter a trading question")
        return value.strip()


async def owned_conversation(db, conversation_id, user_id):
    row = await db.get(AIConversation, conversation_id)
    if not row or row.user_id != user_id:
        raise HTTPException(404, "Conversation not found")
    return row


async def lesson_context(db, user_id, course_id, lesson_id):
    if lesson_id:
        lesson = await require_enrollment(db, user_id, lesson_id)
        module = await db.get(Module, lesson.module_id)
        if course_id and course_id != module.course_id:
            raise HTTPException(422, "The lesson does not belong to this course")
        course = await published_course(db, module.course_id)
        return (
            course.id,
            f"Course: {course.title}\nModule: {module.title}\nLecture: {lesson.title}\nLesson notes:\n{lesson.content_markdown[:12000]}",
        )
    if course_id:
        course = await published_course(db, course_id)
        return course_id, f"Course overview only: {course.title}\n{course.description}"
    return (
        None,
        "No current lesson or trading results were supplied. Use general educational explanations; never claim to have run a backtest.",
    )


@router.get("/conversations")
async def conversations(
    lesson_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rows = (
        await db.scalars(
            select(AIConversation)
            .where(AIConversation.user_id == user["id"], AIConversation.lesson_id == lesson_id)
            .order_by(AIConversation.updated_at.desc())
            .limit(30)
        )
    ).all()
    return [{"id": c.id, "title": c.title, "updated_at": c.updated_at} for c in rows]


@router.get("/conversations/{conversation_id}")
async def conversation(
    conversation_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
):
    row = await owned_conversation(db, conversation_id, user["id"])
    await lesson_context(db, user["id"], row.course_id, row.lesson_id)
    messages = (
        await db.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == row.id, AIMessage.role.in_(["user", "assistant"]))
            .order_by(AIMessage.id.desc())
            .limit(100)
        )
    ).all()
    return {
        "id": row.id,
        "courseId": row.course_id,
        "lessonId": row.lesson_id,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content} for m in reversed(messages)
        ],
    }


@router.delete("/conversations/{conversation_id}")
async def clear_conversation(
    conversation_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
):
    if user["id"] in _busy_users:
        raise HTTPException(409, "Stop generation before clearing the conversation")
    row = await owned_conversation(db, conversation_id, user["id"])
    if user["id"] in _busy_users:
        raise HTTPException(409, "Stop generation before clearing the conversation")
    _busy_users.add(user["id"])
    try:
        await db.execute(delete(AIMessage).where(AIMessage.conversation_id == row.id))
        await db.delete(row)
        await db.commit()
        return {"cleared": True}
    finally:
        _busy_users.discard(user["id"])


async def reply_until_disconnect(request: Request, messages, context):
    task = asyncio.create_task(generate_reply(messages, context))
    try:
        while not task.done():
            await asyncio.wait({task}, timeout=0.25)
            if await request.is_disconnected():
                raise HTTPException(499, "Generation stopped")
        return await task
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@router.post("/chat")
async def chat(
    data: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    limit_requests(user["id"])
    if user["id"] in _busy_users:
        raise HTTPException(
            429,
            "A response is already generating. Stop or wait for it before sending another question.",
        )
    row = (
        await owned_conversation(db, data.conversationId, user["id"])
        if data.conversationId
        else None
    )
    if row and (
        (data.lessonId and data.lessonId != row.lesson_id)
        or (data.courseId and data.courseId != row.course_id)
    ):
        raise HTTPException(422, "Start a new conversation for a different lesson")
    course_id = row.course_id if row else data.courseId
    lesson_id = row.lesson_id if row else data.lessonId
    course_id, context = await lesson_context(db, user["id"], course_id, lesson_id)
    simulation = ""
    if row:
        reference = await db.scalar(
            select(AIMessage)
            .where(AIMessage.conversation_id == row.id, AIMessage.role == "reference")
            .limit(1)
        )
        simulation = reference.content if reference else ""
    elif data.simulationContext:
        simulation = (
            "Client-supplied historical simulation output, not independently verified. You did not execute this simulation. Ratios in metrics are fractions unless labeled otherwise:\n"
            + json.dumps(data.simulationContext.model_dump(), allow_nan=False)
        )
    if simulation:
        context += "\n\n" + simulation
    history = []
    if row:
        recent = (
            await db.scalars(
                select(AIMessage)
                .where(
                    AIMessage.conversation_id == row.id, AIMessage.role.in_(["user", "assistant"])
                )
                .order_by(AIMessage.id.desc())
                .limit(10)
            )
        ).all()
        budget = 10000
        for item in recent:
            if len(item.content) > budget:
                break
            history.insert(0, {"role": item.role, "content": item.content})
            budget -= len(item.content)
    # Context/history reads yield; recheck atomically before taking the generation slot.
    if user["id"] in _busy_users:
        raise HTTPException(429, "A response is already generating. Wait or stop it first.")
    _busy_users.add(user["id"])
    try:
        answer = await reply_until_disconnect(
            request, [*history, {"role": "user", "content": data.message}], context
        )
        if not row:
            row = AIConversation(
                user_id=user["id"],
                course_id=course_id,
                lesson_id=lesson_id,
                title=data.message[:80],
            )
            db.add(row)
            await db.flush()
            if simulation:
                db.add(AIMessage(conversation_id=row.id, role="reference", content=simulation))
        row.updated_at = datetime.now(timezone.utc)
        db.add_all(
            [
                AIMessage(conversation_id=row.id, role="user", content=data.message),
                AIMessage(conversation_id=row.id, role="assistant", content=answer),
            ]
        )
        await db.commit()
        return {"conversationId": row.id, "answer": answer, "model": get_settings().ollama_model}
    finally:
        _busy_users.discard(user["id"])
