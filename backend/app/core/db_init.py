"""
Database initialization and curriculum seeding.
Automatically creates tables and seeds default courses, modules, and lessons.
"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, _get_engine, _get_session_factory
from app.models.user import RefreshSession, User
from app.models.candle import Candle
from app.models.backtest import BacktestRun
from app.models.replay import ReplaySession, ReplayOrder
from app.models.curriculum import Course, Module, Lesson
from app.models import ai_chat, learning  # register additive tables
from app.services.learning_catalog import seed_learning
from app.models.trading import (
    CoachReview, EquitySnapshot, JournalEntry, PaperFill, PaperOrder,
    PaperPortfolio, PaperPosition, RiskProfile, RiskViolation, WatchlistItem,
)


async def init_db():
    """Create tables and seed curriculum data."""
    engine = _get_engine()
    
    # Create all tables
    print("[INFO] Creating database tables...")
    async with engine.begin() as conn:
        # Import all models to ensure they are registered with Base
        await conn.run_sync(Base.metadata.create_all)
    print("[SUCCESS] Database tables created successfully.")

    # Create TimescaleDB hypertable for candles if supported
    if engine.dialect.name == "postgresql":
        async with engine.connect() as conn:
            try:
                # Check if timescaledb extension is loaded
                res = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'"))
                has_timescale = res.scalar() is not None
                
                if has_timescale:
                    print("[INFO] TimescaleDB detected. Creating hypertable for candles...")
                    # We need to run this outside of a transaction or catch table already hypertable exception
                    # check if it is already a hypertable
                    res = await conn.execute(text(
                        "SELECT 1 FROM _timescaledb_catalog.hypertable WHERE table_name = 'candles'"
                    ))
                    is_hypertable = res.scalar() is not None
                    if not is_hypertable:
                        # Drop existing primary key on candles first because timescaledb requires primary key to include the partition column (timestamp)
                        # Our candle model's primary key is (symbol, timestamp, timeframe), so it already includes timestamp!
                        # However, TimescaleDB create_hypertable expects it to be split or done. Let's try:
                        await conn.execute(text(
                            "SELECT create_hypertable('candles', 'timestamp', if_not_exists => TRUE);"
                        ))
                        await conn.commit()
                        print("[SUCCESS] Candles table converted to TimescaleDB hypertable.")
                    else:
                        print("[INFO] Candles table is already a TimescaleDB hypertable.")
                else:
                    print("[INFO] TimescaleDB extension not found. Running as standard PostgreSQL database.")
            except Exception as e:
                print(f"[WARNING] Non-critical error checking/creating TimescaleDB hypertable: {e}")
    else:
        print("[INFO] Skipping TimescaleDB setup for non-PostgreSQL database.")

    # Seed curriculum data
    session_factory = _get_session_factory()
    async with session_factory() as session:
        await seed_curriculum(session)
        await seed_learning(session)


async def seed_curriculum(session: AsyncSession):
    """Seed default curriculum data if courses table is empty."""
    # Check if courses already exist
    stmt = select(Course)
    res = await session.execute(stmt)
    if res.scalars().first() is not None:
        print("[INFO] Curriculum database already seeded.")
        return

    print("[INFO] Seeding curriculum database...")

    # Course 1: Understanding Stop Losses (Beginner)
    c1 = Course(
        id="c1",
        title="Understanding Stop Losses",
        description="Learn how to protect your capital with proper stop loss placement. Covers fixed, trailing, and volatility-based stops with live practice scenarios.",
        difficulty="beginner",
        order_index=1,
        is_published=True
    )
    session.add(c1)

    # Modules for Course 1
    m1_1 = Module(
        id="m1_1",
        course_id="c1",
        title="Stop Loss Basics",
        description="Core concepts of stop losses and why they are non-negotiable.",
        order_index=1
    )
    session.add(m1_1)

    # Lessons for Module 1
    l1_1_1 = Lesson(
        id="l1_1_1",
        module_id="m1_1",
        title="Why You Need a Stop Loss",
        content_markdown="""# Why You Need a Stop Loss

A stop-loss order is an order placed with a broker to buy or sell a security when it reaches a certain price. Stop-losses are designed to limit an investor's loss on a security position.

## Key Concepts
1. **Capital Preservation**: The primary goal of trading is survival. Without capital, you cannot trade.
2. **Emotional Control**: Deciding where to exit *before* you enter prevents emotional decisions during market volatility.
3. **Risk Management**: Knowing your maximum risk per trade allows correct position sizing.

## Rules of Stop Losses
- Never enter a trade without a pre-defined stop loss.
- Never move your stop loss further away (widening the stop) once the trade is active.
- Place stops based on market structure (support/resistance), not arbitrary dollar amounts.
""",
        order_index=1
    )
    l1_1_2 = Lesson(
        id="l1_1_2",
        module_id="m1_1",
        title="Fixed vs. Trailing Stops",
        content_markdown="""# Fixed vs. Trailing Stops

There are different types of stop losses you can use depending on your strategy.

## 1. Fixed Stop Loss
A static price level set at the start of the trade.
- **Pros**: Simple, reliable, easy to calculate risk.
- **Cons**: Can get stopped out right before the market reverses in your favor; doesn't protect unrealized profits.

## 2. Trailing Stop Loss
A stop loss level that automatically moves in the direction of a profitable trade.
- **Pros**: Locks in profits as the price moves in your favor; allows capturing large trends.
- **Cons**: Can exit too early during normal retracements.
""",
        order_index=2,
        replay_symbol="AAPL",
        replay_timeframe="1D",
        replay_start_date="2023-01-01",
        replay_blind_mode=False
    )
    session.add(l1_1_1)
    session.add(l1_1_2)

    # Course 2: Risk-Reward Mastery (Intermediate)
    c2 = Course(
        id="c2",
        title="Risk-Reward Mastery",
        description="Master the art of favorable risk-reward setups. Learn to identify high-probability entries with optimal reward-to-risk ratios.",
        difficulty="intermediate",
        order_index=2,
        is_published=True
    )
    session.add(c2)

    m2_1 = Module(
        id="m2_1",
        course_id="c2",
        title="Calculating Risk/Reward Ratios",
        description="Mathematics and mechanics behind favorable risk/reward ratios.",
        order_index=1
    )
    session.add(m2_1)

    l2_1_1 = Lesson(
        id="l2_1_1",
        module_id="m2_1",
        title="The Math of R:R",
        content_markdown="""# The Math of Risk-to-Reward Ratio (R:R)

The risk-to-reward ratio measures the potential profit of a trade relative to its potential loss.

## Formula
$$R:R = \\frac{\\text{Take Profit Price} - \\text{Entry Price}}{\\text{Entry Price} - \\text{Stop Loss Price}}$$

## Why 1:2 or Higher Matters
If you use a 1:2 R:R (risking $100 to make $200):
- You only need to be right **34% of the time** to break even.
- If you win 50% of your trades, you will be highly profitable.

| R:R Ratio | Win Rate Needed to Break Even |
|-----------|-------------------------------|
| 1:1       | 50%                           |
| 1:2       | 33.3%                         |
| 1:3       | 25%                           |
| 1:5       | 16.7%                         |
""",
        order_index=1
    )
    session.add(l2_1_1)

    await session.commit()
    print("[SUCCESS] Seeded default curriculum data.")


if __name__ == "__main__":
    async def initialize_and_close():
        try:
            await init_db()
        finally:
            await _get_engine().dispose()

    asyncio.run(initialize_and_close())
