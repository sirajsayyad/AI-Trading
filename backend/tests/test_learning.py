"""End-to-end API checks against a disposable database, never local.db."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.db_init import seed_curriculum
from app.main import create_app
from app.models.curriculum import Course, Lesson
from app.models.learning import QuizResult
from app.models.user import User
from app.services.auth_service import create_access_token
from app.services.learning_catalog import CATEGORIES, seed_learning, validate_media


async def test_learning_flow_persistence_ownership_and_validation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as db:
        await seed_curriculum(db)
        await seed_learning(db)
        original = (await db.get(Lesson, "l1_1_1")).content_markdown
        await seed_learning(db)  # idempotent and preserves existing content
        assert (await db.get(Lesson, "l1_1_1")).content_markdown == original
        db.add_all(
            [
                User(id=u, email=f"{u}@test.com", username=u, hashed_password="unused")
                for u in ["alice", "bob"]
            ]
        )
        await db.commit()
    app = create_app()

    async def test_db():
        async with factory() as db:
            yield db
            await db.commit()

    app.dependency_overrides[get_db] = test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/courses")).status_code == 401
        alice = {"Authorization": f"Bearer {create_access_token('alice', 'student')}"}
        bob = {"Authorization": f"Bearer {create_access_token('bob', 'student')}"}
        courses = (await client.get("/courses", headers=alice)).json()
        assert len(courses) == 14
        assert {c["category"] for c in courses} == set(CATEGORIES)
        assert not any("python" in c["title"].lower() for c in courses)
        assert {"Understanding Stop Losses", "Risk-Reward Mastery"} <= {c["title"] for c in courses}
        assert (await client.get("/courses/missing", headers=alice)).status_code == 404
        path = "/lessons/ai-fundamentals-lesson"
        assert (await client.get(path, headers=alice)).status_code == 403
        assert (
            await client.post("/courses/ai-fundamentals/enroll", headers=alice)
        ).status_code == 200
        assert (
            await client.post("/courses/ai-fundamentals/enroll", headers=alice)
        ).status_code == 200
        lesson = (await client.get(path, headers=alice)).json()
        assert lesson["kind"] == "reading"
        assert "answer" not in lesson["quiz"][0]
        assert (
            await client.put(path + "/progress", headers=bob, json={"position": 99})
        ).status_code == 403
        for position in [-1, 86401]:
            assert (
                await client.put(path + "/progress", headers=alice, json={"position": position})
            ).status_code == 422
        await client.put(
            path + "/progress", headers=alice, json={"position": 123, "completed": True}
        )
        await client.put(path + "/progress", headers=alice, json={"position": 125})
        restored = (await client.get(path, headers=alice)).json()
        assert restored["completed"] and restored["position"] == 125
        detail = (await client.get("/courses/ai-fundamentals", headers=alice)).json()
        assert detail["progress"] == 100 and detail["last_lesson_id"] == "ai-fundamentals-lesson"
        assert (await client.get("/learning/completed", headers=alice)).json()[0][
            "lesson_id"
        ] == "ai-fundamentals-lesson"
        assert (await client.get("/learning/completed", headers=bob)).json() == []
        await client.put(
            path + "/bookmark", headers=alice, json={"position": 125, "notes": "Risk rules"}
        )
        assert (await client.get("/learning/saved", headers=bob)).json() == []
        saved = (await client.get("/learning/saved", headers=alice)).json()
        assert saved[0]["notes"] == "Risk rules"
        assert (await client.get(path, headers=alice)).json()["bookmarks"][0][
            "notes"
        ] == "Risk rules"
        assert (
            await client.post(path + "/quiz", headers=alice, json={"answers": [9]})
        ).status_code == 422
        assert (await client.post(path + "/quiz", headers=alice, json={"answers": [1]})).json()[
            "score"
        ] == 100
        assert (await client.post(path + "/quiz", headers=alice, json={"answers": [0]})).json()[
            "score"
        ] == 0
        with patch(
            "app.routers.curriculum.ask_coach", new=AsyncMock(return_value="Lesson answer")
        ) as coach:
            response = await client.post(
                path + "/coach", headers=alice, json={"question": "Explain model risk"}
            )
            assert response.json()["answer"] == "Lesson answer"
            assert (
                "AI-Assisted Trading"
                in coach.call_args.kwargs["conversation_history"][0]["content"]
            )
        await client.delete(path + "/bookmark/125", headers=bob)
        assert len((await client.get("/learning/saved", headers=alice)).json()) == 1
        await client.delete(path + "/bookmark/125", headers=alice)
        assert (await client.get("/learning/saved", headers=alice)).json() == []
        async with factory() as db:
            attempts = (await db.scalars(select(QuizResult))).all()
            assert [a.score for a in attempts] == [100, 0]
            c = await db.get(Course, "ai-fundamentals")
            c.is_published = False
            await db.commit()
        assert (await client.get(path, headers=alice)).status_code == 404
        assert (await client.get("/courses/ai-fundamentals", headers=alice)).status_code == 404
    await engine.dispose()


def test_only_video_ids_are_accepted():
    assert validate_media({"video_id": "8124kv-632k"})
    with pytest.raises(ValueError):
        validate_media({"video_id": "https://evil.example/video"})
