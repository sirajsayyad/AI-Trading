from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.routers.dashboard import history_points


def test_history_uses_prior_peak_filters_dates_and_handles_sqlite_times():
    now = datetime(2026, 10, 15, tzinfo=UTC)
    snapshots = [
        SimpleNamespace(timestamp=(now - timedelta(days=10)).replace(tzinfo=None), equity=100),
        SimpleNamespace(timestamp=now - timedelta(days=2), equity=80),
        SimpleNamespace(timestamp=now, equity=90),
    ]
    result = history_points(snapshots, 7, now)
    assert result["observation_count"] == 2
    assert [p["drawdown"] for p in result["points"]] == [-20, -10]
    assert result["max_drawdown"] == -20
    assert history_points([], None, now)["max_drawdown"] is None


def test_history_bounds_payload_and_keeps_endpoints_and_true_extreme():
    now = datetime.now(UTC)
    snapshots = [
        SimpleNamespace(timestamp=now + timedelta(seconds=i), equity=1 if i == 501 else 100)
        for i in range(1001)
    ]
    result = history_points(snapshots, None, now)
    assert len(result["points"]) == 500
    assert result["observation_count"] == 1001
    assert result["max_drawdown"] == -99
    assert result["points"][0]["timestamp"] == now
    assert result["points"][-1]["timestamp"] == now + timedelta(seconds=1000)


async def test_dashboard_ownership_missing_account_and_risk():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base
    from app.models.trading import (
        EquitySnapshot,
        PaperFill,
        PaperOrder,
        PaperPortfolio,
        RiskProfile,
    )
    from app.models.user import User
    from app.routers.dashboard import dashboard_history, dashboard_summary

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        db.add_all(
            [
                User(id="a", email="a@test.com", username="a", hashed_password="x"),
                User(id="b", email="b@test.com", username="b", hashed_password="x"),
            ]
        )
        await db.flush()
        missing = await dashboard_summary({"id": "a"}, db)
        assert missing["equity"] is None
        assert missing["profit_factor"] is None
        db.add_all(
            [
                PaperPortfolio(id="pa", user_id="a", cash_balance=900, starting_balance=1000),
                PaperPortfolio(id="pb", user_id="b", cash_balance=9999),
                RiskProfile(user_id="a", max_daily_loss_percent=3),
            ]
        )
        await db.flush()
        now = datetime.now(UTC)
        db.add_all(
            [
                EquitySnapshot(
                    portfolio_id="pa", equity=1000, cash=1000, timestamp=now - timedelta(hours=1)
                ),
                EquitySnapshot(portfolio_id="pa", equity=900, cash=900, timestamp=now),
                EquitySnapshot(portfolio_id="pb", equity=9999, cash=9999, timestamp=now),
            ]
        )
        order = PaperOrder(
            id="oa",
            user_id="a",
            portfolio_id="pa",
            symbol="AAPL",
            side="sell",
            order_type="market",
            quantity=1,
            submitted_price=100,
            idempotency_key="test-order",
            data_timestamp=now,
        )
        db.add(order)
        await db.flush()
        db.add(
            PaperFill(
                order_id="oa",
                user_id="a",
                symbol="AAPL",
                side="sell",
                quantity=1,
                price=100,
                realized_pnl=-100,
                timestamp=now,
            )
        )
        await db.flush()
        summary = await dashboard_summary({"id": "a"}, db)
        history = await dashboard_history("All", {"id": "a"}, db)
        assert [p["equity"] for p in history["points"]] == [1000, 900]
        assert summary["recent_trades"][0]["realized_pnl"] == -100
        assert summary["risk"]["daily_loss_limit"] == 27
        assert summary["risk"]["daily_loss_used_percent"] == 370.37
        assert summary["risk"]["exposure"] == 0
    await engine.dispose()
