"""
Backtest API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.backtest import (
    BacktestConfig, WalkForwardConfig, MonteCarloConfig,
    BacktestResultResponse,
)
from app.services.backtest_service import (
    run_backtest_service, run_walk_forward, run_monte_carlo,
)
from app.models.backtest import BacktestRun
from app.engine.strategy import list_strategies
import app.engine.strategies  # noqa: F401 — register strategies

router = APIRouter(prefix="/backtest", tags=["Backtesting"])


@router.get("/strategies")
async def get_available_strategies():
    """List available strategies and their parameter schemas."""
    return list_strategies()


@router.post("/run")
async def run_backtest_endpoint(
    config: BacktestConfig,
    db: AsyncSession = Depends(get_db),
):
    """Run a backtest with the given configuration."""
    try:
        run_id, results = await run_backtest_service(
            db=db,
            strategy_name=config.strategy_name,
            symbol=config.symbol,
            timeframe=config.timeframe,
            start_date=config.start_date,
            end_date=config.end_date,
            initial_capital=config.initial_capital,
            strategy_params=config.strategy_params,
            slippage_bps=config.slippage_bps,
            commission_flat=config.commission_flat,
            commission_pct=config.commission_pct,
        )

        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

        return {"id": run_id, "results": results}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{backtest_id}")
async def get_backtest_result(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a saved backtest result by ID."""
    stmt = select(BacktestRun).where(BacktestRun.id == backtest_id)
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    return {
        "id": run.id,
        "strategy_name": run.strategy_name,
        "symbol": run.symbol,
        "timeframe": run.timeframe,
        "start_date": run.start_date,
        "end_date": run.end_date,
        "initial_capital": run.initial_capital,
        "strategy_params": run.strategy_params,
        "status": run.status,
        "results": run.results,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.post("/walk-forward")
async def walk_forward_endpoint(
    config: WalkForwardConfig,
    db: AsyncSession = Depends(get_db),
):
    """Run walk-forward analysis across rolling IS/OOS windows."""
    try:
        results = await run_walk_forward(
            db=db,
            strategy_name=config.strategy_name,
            symbol=config.symbol,
            timeframe=config.timeframe,
            start_date=config.start_date,
            end_date=config.end_date,
            in_sample_days=config.in_sample_days,
            out_of_sample_days=config.out_of_sample_days,
            step_days=config.step_days,
            initial_capital=config.initial_capital,
            strategy_params=config.strategy_params,
            slippage_bps=config.slippage_bps,
            commission_flat=config.commission_flat,
            commission_pct=config.commission_pct,
        )

        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/monte-carlo")
async def monte_carlo_endpoint(
    config: MonteCarloConfig,
    db: AsyncSession = Depends(get_db),
):
    """Run Monte Carlo simulation randomizing trade order."""
    if not config.symbol or not config.strategy_name:
        raise HTTPException(
            status_code=400,
            detail="symbol and strategy_name are required"
        )

    try:
        results = await run_monte_carlo(
            db=db,
            strategy_name=config.strategy_name,
            symbol=config.symbol,
            timeframe=config.timeframe,
            start_date=config.start_date,
            end_date=config.end_date,
            initial_capital=config.initial_capital,
            strategy_params=config.strategy_params,
            simulations=config.simulations,
        )

        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
