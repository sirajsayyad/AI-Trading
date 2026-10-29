import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.db_init import seed_curriculum
from app.main import create_app
from app.models.ai_chat import AIMessage
from app.models.learning import Enrollment
from app.models.user import User
from app.routers.ai_coach import reply_until_disconnect
from app.services import coach_service
from app.services.auth_service import create_access_token
from app.services.learning_catalog import seed_learning


async def test_chat_context_followup_persistence_ownership_validation_and_clear():
    coach_service._requests.clear()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as db:
        await seed_curriculum(db)
        await seed_learning(db)
        db.add_all(
            [
                User(id=u, email=f"{u}@test.com", username=u, hashed_password="unused")
                for u in ["coach-a", "coach-b"]
            ]
        )
        await db.flush()
        db.add(Enrollment(user_id="coach-a", course_id="c1"))
        await db.commit()
    app = create_app()

    async def test_db():
        async with factory() as db:
            yield db
            await db.commit()

    app.dependency_overrides[get_db] = test_db
    alice = {"Authorization": f"Bearer {create_access_token('coach-a', 'student')}"}
    bob = {"Authorization": f"Bearer {create_access_token('coach-b', 'student')}"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.post("/ai-coach/chat", json={"message": "Risk?"})).status_code == 401
        for invalid in ["", "  ", "x" * 4001]:
            assert (
                await client.post("/ai-coach/chat", headers=alice, json={"message": invalid})
            ).status_code == 422
        with patch(
            "app.routers.ai_coach.generate_reply",
            new=AsyncMock(return_value="## Risk\nUse a defined loss budget."),
        ) as generate:
            first = await client.post(
                "/ai-coach/chat",
                headers=alice,
                json={
                    "message": "Explain risk",
                    "simulationContext": {
                        "kind": "backtest",
                        "symbol": "TEST",
                        "metrics": {"total_trades": 12},
                        "configuration": {"short_period": 10},
                    },
                },
            )
            assert first.status_code == 200
            conversation_id = first.json()["conversationId"]
            assert first.json()["answer"].startswith("## Risk")
            followup = await client.post(
                "/ai-coach/chat",
                headers=alice,
                json={"message": "Show a hypothetical example", "conversationId": conversation_id},
            )
            assert followup.status_code == 200
            sent = generate.call_args.args[0]
            assert [m["role"] for m in sent] == ["user", "assistant", "user"]
            assert sent[0]["content"] == "Explain risk"
            assert '"total_trades": 12' in generate.call_args.args[1]
            assert "not independently verified" in generate.call_args.args[1]
            assert "Use a defined loss budget" in sent[1]["content"]
            restored = (
                await client.get(f"/ai-coach/conversations/{conversation_id}", headers=alice)
            ).json()
            assert len(restored["messages"]) == 4
            assert (await client.get("/ai-coach/conversations", headers=bob)).json() == []
            assert (
                await client.get(f"/ai-coach/conversations/{conversation_id}", headers=bob)
            ).status_code == 404
            assert (
                await client.delete(f"/ai-coach/conversations/{conversation_id}", headers=bob)
            ).status_code == 404
            assert (
                await client.post(
                    "/ai-coach/chat",
                    headers=bob,
                    json={"message": "Read private chat", "conversationId": conversation_id},
                )
            ).status_code == 404
            lesson = await client.post(
                "/ai-coach/chat",
                headers=alice,
                json={
                    "message": "Why does this lesson use a stop?",
                    "courseId": "c1",
                    "lessonId": "l1_1_1",
                },
            )
            assert lesson.status_code == 200
            context = generate.call_args.args[1]
            assert (
                "Understanding Stop Losses" in context
                and "Stop Loss Basics" in context
                and "Why You Need a Stop Loss" in context
            )
            assert "Capital Preservation" in context
            assert (
                await client.post(
                    "/ai-coach/chat",
                    headers=bob,
                    json={"message": "Read notes", "lessonId": "l1_1_1"},
                )
            ).status_code == 403
            assert (
                await client.post(
                    "/ai-coach/chat",
                    headers=alice,
                    json={"message": "Mismatch", "courseId": "c2", "lessonId": "l1_1_1"},
                )
            ).status_code == 422
            assert (
                await client.delete(f"/ai-coach/conversations/{conversation_id}", headers=alice)
            ).status_code == 200
            assert (
                await client.get(f"/ai-coach/conversations/{conversation_id}", headers=alice)
            ).status_code == 404
            async with factory() as db:
                assert (
                    await db.scalar(
                        select(func.count())
                        .select_from(AIMessage)
                        .where(AIMessage.conversation_id == conversation_id)
                    )
                    == 0
                )
        with patch(
            "app.routers.ai_coach.generate_reply",
            new=AsyncMock(side_effect=HTTPException(503, "Model unavailable")),
        ):
            error = await client.post(
                "/ai-coach/chat", headers=alice, json={"message": "Explain drawdown"}
            )
            assert error.status_code == 503 and "answer" not in error.json()
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed_answer(*args):
            entered.set()
            await release.wait()
            return "Generated after the concurrency check"

        with patch("app.routers.ai_coach.generate_reply", side_effect=delayed_answer):
            pending = asyncio.create_task(
                client.post("/ai-coach/chat", headers=bob, json={"message": "Explain risk"})
            )
            try:
                await asyncio.wait_for(entered.wait(), timeout=2)
                second = await client.post(
                    "/ai-coach/chat", headers=bob, json={"message": "Another simultaneous question"}
                )
                assert second.status_code == 429 and "already generating" in second.json()["detail"]
            finally:
                release.set()
            assert (await pending).status_code == 200
    await engine.dispose()


@pytest.mark.parametrize(
    "case,status",
    [
        ("ok", 200),
        ("connect", 503),
        ("timeout", 504),
        ("missing", 503),
        ("error", 502),
        ("empty", 502),
        ("malformed", 502),
        ("markers", 200),
        ("unfinished", 502),
    ],
)
async def test_real_ollama_protocol_and_honest_errors(case, status):
    real_client = httpx.AsyncClient
    seen = []

    async def handler(request):
        if case == "connect":
            raise httpx.ConnectError("private server address must not leak", request=request)
        if case == "timeout":
            raise httpx.ReadTimeout("provider timeout", request=request)
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": []
                    if case == "missing"
                    else [{"name": "qwen3:4b-thinking", "capabilities": ["thinking"]}]
                },
            )
        seen.append(__import__("json").loads(request.content))
        if case == "error":
            return httpx.Response(500, json={"error": "internal diagnostics"})
        if case == "malformed":
            return httpx.Response(200, text="not json")
        return httpx.Response(
            200,
            json={
                "done": True,
                "message": {
                    "role": "assistant",
                    "content": ""
                    if case == "empty"
                    else "<think>private drafting text</think>Generated model answer"
                    if case == "markers"
                    else "<think>unfinished draft"
                    if case == "unfinished"
                    else "Generated model answer",
                    "thinking": "Private model drafting text, never returned to the client",
                },
            },
        )

    def client_factory(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    with patch("app.services.coach_service.httpx.AsyncClient", side_effect=client_factory):
        if status == 200:
            assert (
                await coach_service.generate_reply(
                    [{"role": "user", "content": "Explain volatility"}], "Authorized lesson"
                )
                == "Generated model answer"
            )
            assert seen[0]["model"] == "qwen3:4b-thinking" and seen[0]["stream"] is False
            assert seen[0]["think"] is True and seen[0]["options"]["num_predict"] == 2048
            assert "Authorized lesson" in seen[0]["messages"][0]["content"]
            assert "Never invent" in seen[0]["messages"][0]["content"]
        else:
            with pytest.raises(HTTPException) as error:
                await coach_service.generate_reply([{"role": "user", "content": "Risk?"}])
            assert error.value.status_code == status
            assert "private server address" not in error.value.detail


def test_request_rate_limit_is_per_user():
    coach_service._requests.clear()
    with patch(
        "app.services.coach_service.get_settings",
        return_value=SimpleNamespace(coach_requests_per_minute=1),
    ):
        coach_service.limit_requests("limited")
        with pytest.raises(HTTPException) as error:
            coach_service.limit_requests("limited")
        assert error.value.status_code == 429
        coach_service.limit_requests("another-user")
    coach_service._requests.clear()


async def test_stop_generation_cancels_upstream_task():
    cancelled = asyncio.Event()

    async def slow_reply(*args):
        try:
            await asyncio.sleep(30)
        finally:
            cancelled.set()

    fake_request = SimpleNamespace(is_disconnected=AsyncMock(return_value=True))
    with patch("app.routers.ai_coach.generate_reply", side_effect=slow_reply):
        with pytest.raises(HTTPException) as error:
            await reply_until_disconnect(fake_request, [], "")
        assert error.value.status_code == 499
        assert cancelled.is_set()
