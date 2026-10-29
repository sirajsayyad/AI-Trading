"""
Backtest service — orchestrates backtest runs, walk-forward, and Monte Carlo.
"""

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.backtest import run_backtest
from app.engine.execution import CandleData
from app.models.backtest import BacktestRun
from app.models.candle import Candle
from app.services.market_data import fetch_live_candles


async def fetch_candles(
    db: AsyncSession,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    stored_only: bool = False,
) -> list[CandleData]:
    """Fetch candles from DB and convert to CandleData objects."""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    stmt = (
        select(Candle)
        .where(Candle.symbol == symbol.upper())
        .where(Candle.timeframe == timeframe)
        .where(Candle.timestamp >= start)
        .where(Candle.timestamp <= end)
        .order_by(Candle.timestamp.asc())
    )

    result = await db.execute(stmt)
    rows = result.scalars().all()

    candles = [
        CandleData(
            symbol=row.symbol,
            timestamp=row.timestamp,
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
            timeframe=row.timeframe,
        )
        for row in rows
    ]

    if candles or stored_only:
        return candles

    provider_candles = await fetch_live_candles(
        symbol=symbol,
        timeframe=timeframe,
        limit=5000,
        start_date=start_date,
        end_date=end_date,
    )
    return [
        CandleData(
            symbol=candle["symbol"],
            timestamp=candle["timestamp"],
            open=candle["open"],
            high=candle["high"],
            low=candle["low"],
            close=candle["close"],
            volume=candle["volume"],
            timeframe=candle["timeframe"],
        )
        for candle in provider_candles
    ]


async def run_backtest_service(
    db: AsyncSession,
    strategy_name: str,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0,
    strategy_params: dict = None,
    slippage_bps: float = 5.0,
    commission_flat: float = 1.0,
    commission_pct: float = 0.001,
    stored_only: bool = False,
) -> tuple[str, dict]:
    """Run a backtest and persist results. Returns (run_id, results_dict)."""

    # Create run record
    run = BacktestRun(
        strategy_name=strategy_name,
        symbol=symbol.upper(),
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        strategy_params=strategy_params or {},
        slippage_bps=slippage_bps,
        commission_flat=commission_flat,
        commission_pct=commission_pct,
        status="running",
    )
    db.add(run)
    await db.flush()

    try:
        candles = await fetch_candles(db, symbol, timeframe, start_date, end_date, stored_only)

        if not candles:
            run.status = "failed"
            run.error_message = f"No candle data found for {symbol} ({timeframe}) in date range"
            await db.commit()
            return run.id, {"error": run.error_message}

        report = run_backtest(
            strategy_name=strategy_name,
            candles=candles,
            params=strategy_params or {},
            initial_capital=initial_capital,
            slippage_bps=slippage_bps,
            commission_flat=commission_flat,
            commission_pct=commission_pct,
        )

        results = report.to_dict()
        run.results = results
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)  # noqa: UP017 - supports Python 3.11
        await db.commit()

        return run.id, results

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        await db.commit()
        return run.id, {"error": str(e)}


async def run_walk_forward(
    db: AsyncSession,
    strategy_name: str,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    in_sample_days: int = 180,
    out_of_sample_days: int = 60,
    step_days: int = 30,
    initial_capital: float = 100000.0,
    strategy_params: dict = None,
    slippage_bps: float = 5.0,
    commission_flat: float = 1.0,
    commission_pct: float = 0.001,
) -> dict:
    """
    Walk-forward analysis: roll through IS/OOS windows.
    """
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    all_candles = await fetch_candles(db, symbol, timeframe, start_date, end_date)
    if not all_candles:
        return {"error": "No candle data found"}

    windows = []
    window_start = start
    profitable_windows = 0

    while window_start + timedelta(days=in_sample_days + out_of_sample_days) <= end:
        is_end = window_start + timedelta(days=in_sample_days)
        oos_end = is_end + timedelta(days=out_of_sample_days)

        # In-sample candles
        is_candles = [c for c in all_candles if window_start <= c.timestamp < is_end]
        # Out-of-sample candles
        oos_candles = [c for c in all_candles if is_end <= c.timestamp < oos_end]

        if is_candles and oos_candles:
            # Run IS backtest
            is_report = run_backtest(
                strategy_name=strategy_name, candles=is_candles,
                params=strategy_params or {}, initial_capital=initial_capital,
                slippage_bps=slippage_bps, commission_flat=commission_flat,
                commission_pct=commission_pct,
            )

            # Run OOS backtest
            oos_report = run_backtest(
                strategy_name=strategy_name, candles=oos_candles,
                params=strategy_params or {}, initial_capital=initial_capital,
                slippage_bps=slippage_bps, commission_flat=commission_flat,
                commission_pct=commission_pct,
            )

            if oos_report.total_return > 0:
                profitable_windows += 1

            windows.append({
                "window_start": window_start.isoformat(),
                "is_end": is_end.isoformat(),
                "oos_end": oos_end.isoformat(),
                "is_return": round(is_report.total_return_pct, 4),
                "oos_return": round(oos_report.total_return_pct, 4),
                "oos_sharpe": round(oos_report.sharpe_ratio, 4),
                "oos_max_dd": round(oos_report.max_drawdown_pct, 4),
                "oos_trades": oos_report.total_trades,
            })

        window_start += timedelta(days=step_days)

    if not windows:
        return {"error": "Insufficient data for walk-forward analysis"}

    total_windows = len(windows)
    return {
        "windows": windows,
        "aggregate_oos_return": round(sum(w["oos_return"] for w in windows) / total_windows, 4),
        "aggregate_oos_sharpe": round(sum(w["oos_sharpe"] for w in windows) / total_windows, 4),
        "aggregate_oos_max_drawdown": round(max(w["oos_max_dd"] for w in windows), 4),
        "consistency_ratio": round(profitable_windows / total_windows, 4),
    }


async def run_monte_carlo(
    db: AsyncSession,
    strategy_name: str,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0,
    strategy_params: dict = None,
    slippage_bps: float = 5.0,
    commission_flat: float = 1.0,
    commission_pct: float = 0.001,
    simulations: int = 1000,
) -> dict:
    """
    Monte Carlo simulation: randomize trade order to get distribution of outcomes.
    """
    # First run the base backtest
    candles = await fetch_candles(db, symbol, timeframe, start_date, end_date)
    if not candles:
        return {"error": "No candle data found"}

    base_report = run_backtest(
        strategy_name=strategy_name, candles=candles,
        params=strategy_params or {}, initial_capital=initial_capital,
        slippage_bps=slippage_bps, commission_flat=commission_flat,
        commission_pct=commission_pct,
    )

    if not base_report.trades:
        return {"error": "No trades generated — cannot run Monte Carlo"}

    # Extract trade P&Ls
    trade_pnls = [t["pnl"] for t in base_report.trades]

    results = []
    for _ in range(simulations):
        shuffled = trade_pnls.copy()
        random.shuffle(shuffled)

        equity = initial_capital
        peak = equity
        max_dd = 0.0
        curve = [equity]

        for pnl in shuffled:
            equity += pnl
            curve.append(equity)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        total_return = (equity - initial_capital) / initial_capital
        results.append({
            "return": round(total_return, 4),
            "drawdown": round(max_dd, 4),
            "final_equity": round(equity, 2),
        })

    # Sort results for percentile calculation
    results.sort(key=lambda x: x["return"])

    def percentile(data, p):
        idx = int(len(data) * p / 100)
        idx = min(idx, len(data) - 1)
        return data[idx]

    return {
        "simulations": simulations,
        "base_return": round(base_report.total_return_pct, 4),
        "base_trades": len(trade_pnls),
        "percentile_returns": {
            "5th": percentile(results, 5)["return"],
            "25th": percentile(results, 25)["return"],
            "50th": percentile(results, 50)["return"],
            "75th": percentile(results, 75)["return"],
            "95th": percentile(results, 95)["return"],
        },
        "percentile_drawdowns": {
            "5th": percentile(sorted(results, key=lambda x: x["drawdown"]), 5)["drawdown"],
            "50th": percentile(sorted(results, key=lambda x: x["drawdown"]), 50)["drawdown"],
            "95th": percentile(sorted(results, key=lambda x: x["drawdown"]), 95)["drawdown"],
        },
        "percentile_final_equity": {
            "5th": percentile(results, 5)["final_equity"],
            "50th": percentile(results, 50)["final_equity"],
            "95th": percentile(results, 95)["final_equity"],
        },
        "distribution": results[:100],  # Send first 100 for visualization
    }
