from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.db_init import seed_curriculum
from app.engine.execution import CandleData, ExecutionSimulator, OrderSide, Position
from app.engine.strategies.sma_crossover import SMACrossoverStrategy
from app.models.candle import Candle
from app.models.curriculum import Course, Lesson, Module
from app.models.learning import Bookmark, CourseInfo, Enrollment, LectureProgress
from app.models.user import User
from app.routers.curriculum import get_course, list_courses
from app.routers.data import list_symbols
from app.services.backtest_service import fetch_candles, run_backtest_service
from app.services.data_ingestion import IngestionService
from app.services.learning_catalog import seed_learning
from app.services.replay_service import (
    _active_sessions,
    control_session,
    create_session,
    get_next_candle,
)


async def test_retirement_preserves_learning_and_original_modules():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as db:
        await seed_curriculum(db)
        db.add(User(id="u", email="u@test", username="u", hashed_password="unused"))
        db.add(Course(id="python-foundations", title="General Python", is_published=True))
        db.add(Course(id="unrelated", title="Unrelated course", is_published=True))
        await db.flush()
        db.add(Module(id="python-module", course_id="python-foundations", title="Programming"))
        db.add(CourseInfo(course_id="unrelated", metadata_json={"category": "General education"}))
        await db.flush()
        db.add(
            Lesson(
                id="python-video",
                module_id="python-module",
                title="General Python",
                content_markdown="Original",
            )
        )
        await db.flush()
        db.add_all([Enrollment(user_id="u", course_id=c) for c in ["c1", "python-foundations"]])
        db.add_all(
            [
                LectureProgress(user_id="u", lesson_id=l, position=42, completed=True)
                for l in ["l1_1_1", "python-video"]
            ]
        )
        db.add(Bookmark(user_id="u", lesson_id="python-video", position=42, notes="Preserve me"))
        await db.commit()
        original = (await db.get(Lesson, "l1_1_1")).content_markdown
        await seed_learning(db)
        await seed_learning(db)
        assert not (await db.get(Course, "python-foundations")).is_published
        assert (await db.get(LectureProgress, ("u", "python-video"))).position == 42
        assert (await db.get(Bookmark, ("u", "python-video", 42))).notes == "Preserve me"
        assert (await db.get(LectureProgress, ("u", "l1_1_1"))).completed
        assert (await db.get(Lesson, "l1_1_1")).content_markdown == original
        courses = await list_courses(db, {"id": "u"})
        assert not {"python-foundations", "unrelated"} & {c["id"] for c in courses}
        assert len((await get_course("c1", db, {"id": "u"}))["modules"]) == 3
        assert len((await get_course("c2", db, {"id": "u"}))["modules"]) == 2
        db.add_all(
            [
                Candle(
                    symbol="TEST",
                    timeframe=tf,
                    timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    open=100,
                    high=101,
                    low=99,
                    close=100,
                    volume=1000,
                )
                for tf in ["1D", "1h"]
            ]
        )
        await db.flush()
        data = await list_symbols(db)
        assert len(data) == 1 and data[0].timeframes == ["1D", "1h"]
    await engine.dispose()


async def test_training_upload_and_engine_use_stored_data_without_provider_fallback():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as db:
        # Explicit synthetic test fixture, never seeded or represented as market history.
        csv = "symbol,timestamp,open,high,low,close,volume,timeframe\n"
        for i, close in enumerate(
            [
                110,
                109,
                108,
                107,
                106,
                105,
                104,
                106,
                110,
                112,
                114,
                110,
                105,
                100,
                99,
                98,
                102,
                106,
                110,
                112,
                108,
                102,
                95,
                94,
            ]
        ):
            csv += f"TEST,2024-01-{i + 1:02d},{close},{close + 1},{close - 1},{close},1000,1D\n"
        imported = await IngestionService(db).ingest(csv.encode(), "csv")
        assert imported["inserted"] == 24 and not imported["errors"]
        duplicate = await IngestionService(db).ingest(csv.encode(), "csv")
        assert duplicate["inserted"] == 0 and duplicate["duplicates_skipped"] == 24
        with patch(
            "app.services.backtest_service.fetch_live_candles",
            new=AsyncMock(side_effect=AssertionError("No demo fallback")),
        ):
            assert not await fetch_candles(
                db, "EMPTY", "1D", "2024-01-01", "2024-02-01", stored_only=True
            )
            run_id, result = await run_backtest_service(
                db,
                "sma_crossover",
                "TEST",
                "1D",
                "2024-01-01",
                "2024-02-01",
                strategy_params={
                    "short_period": 2,
                    "long_period": 5,
                    "quantity": 3,
                    "stop_loss_pct": 2,
                },
                stored_only=True,
            )
            assert run_id and "error" not in result
            assert result["total_trades"] > 0
            assert result["equity_curve"]
        with patch(
            "app.services.replay_service.fetch_live_candles",
            new=AsyncMock(side_effect=AssertionError("No demo fallback")),
        ):
            missing = await create_session(db, "EMPTY", "1D", "2024-01-01", stored_only=True)
            assert "error" in missing
    await engine.dispose()


async def test_replay_step_advances_only_one_simulated_candle():
    session_id = "training-test"
    candles = [
        CandleData(
            "TEST",
            datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
            100,
            101,
            99,
            100,
            1000,
        )
        for i in range(3)
    ]
    _active_sessions[session_id] = {
        "paused": True,
        "status": "paused",
        "candles": candles,
        "index": 0,
        "blind_mode": False,
        "simulator": ExecutionSimulator(),
    }
    try:
        assert (await get_next_candle(session_id))["paused"]
        control_session(session_id, "step")
        assert (await get_next_candle(session_id))["index"] == 0
        assert (await get_next_candle(session_id))["paused"]
        control_session(session_id, "step")
        assert (await get_next_candle(session_id))["index"] == 1
        assert _active_sessions[session_id]["paused"]
    finally:
        del _active_sessions[session_id]


def test_backtest_stop_and_target_exit_on_next_bar_not_the_signal_bar():
    for close, params in [(94, {"stop_loss_pct": 5}), (106, {"take_profit_pct": 5})]:
        strategy = SMACrossoverStrategy()
        strategy.set_params({"short_period": 2, "long_period": 5, "quantity": 7, **params})
        simulator = ExecutionSimulator()
        strategy.set_simulator(simulator)
        strategy.initialize()
        simulator.positions["TEST"] = Position(symbol="TEST", quantity=7, avg_entry_price=100)
        strategy.in_position = True
        candle = CandleData(
            "TEST", datetime(2024, 1, 1, tzinfo=timezone.utc), 100, 110, 90, close, 1000
        )
        strategy.on_bar(candle)
        assert not simulator.fills
        assert simulator.pending_orders[0].side == OrderSide.SELL
        following = CandleData("TEST", candle.timestamp + timedelta(days=1), 93, 94, 92, 93, 1000)
        fills = simulator.process_bar(following)
        assert fills[0].price == 93 and fills[0].quantity == 7
        assert simulator.get_position("TEST").quantity == 0
