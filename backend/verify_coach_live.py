"""Run three real local-model requests against a disposable application database.

Run from backend: .\.venv\Scripts\python.exe verify_coach_live.py
Requires the configured Ollama model; never substitutes mocked responses.
"""

import asyncio
import json
import re
from pathlib import Path
from time import monotonic

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.db_init import seed_curriculum
from app.main import create_app
from app.models.learning import Enrollment
from app.models.user import User
from app.services.auth_service import create_access_token
from app.services.learning_catalog import seed_learning


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            await seed_curriculum(db)
            await seed_learning(db)
            db.add(
                User(
                    id="live-test",
                    email="fixture@example.invalid",
                    username="live-test",
                    hashed_password="not-a-login",
                )
            )
            await db.flush()
            db.add(Enrollment(user_id="live-test", course_id="c1"))
            await db.commit()

        async def disposable_db():
            async with factory() as db:
                yield db
                await db.commit()

        app = create_app()
        app.dependency_overrides[get_db] = disposable_db
        headers = {"Authorization": f"Bearer {create_access_token('live-test', 'student')}"}
        report = []
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", timeout=210
        ) as client:
            conversation_id = None
            cases = [
                (
                    "normal",
                    {
                        "message": "What is volatility, and how does it affect stop-loss placement and position size? Keep the explanation concise."
                    },
                ),
                (
                    "followup",
                    {
                        "message": "Use a hypothetical risk budget of 100 and a stop distance of 5 per share. Calculate the share count before costs and explain the limitation."
                    },
                ),
                (
                    "lesson",
                    {
                        "message": "Explain the current lesson and why widening a stop without reducing the share count changes the planned risk.",
                        "courseId": "c1",
                        "lessonId": "c1-volatility-lesson",
                    },
                ),
            ]
            for label, body in cases:
                if label == "followup":
                    body["conversationId"] = conversation_id
                started = monotonic()
                response = await client.post("/ai-coach/chat", json=body, headers=headers)
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Real inference failed ({response.status_code}): {response.text}"
                    )
                data = response.json()
                assert len(data["answer"]) > 50
                assert "<think>" not in data["answer"] and "</think>" not in data["answer"]
                if label == "followup":
                    assert re.search(
                        r"\b20(?:\.0+)?\s+(?:whole\s+)?shares\b",
                        data["answer"].replace("*", ""),
                        re.I,
                    ), "Review the model's arithmetic in the follow-up"
                conversation_id = data["conversationId"]
                report.append(
                    {
                        "case": label,
                        "question": body["message"],
                        "model": data["model"],
                        "answer": data["answer"],
                        "seconds": round(monotonic() - started, 2),
                    }
                )
                print(
                    f"{label}: real model response received ({report[-1]['seconds']}s)", flush=True
                )
        target = Path(__file__).resolve().parents[1] / "docs" / "coach-live-verification.json"
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Live verification saved: {target}", flush=True)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
