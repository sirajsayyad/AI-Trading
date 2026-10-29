"""
Pydantic schemas for backtest API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BacktestConfig(BaseModel):
    """Configuration for running a backtest."""
    symbol: str = Field(..., min_length=1, max_length=20)
    strategy_name: str = Field(..., min_length=1)
    timeframe: str = Field(default="1D", pattern=r"^(1m|5m|15m|1h|4h|1D|1W)$")
    start_date: str = Field(..., description="ISO format date string")
    end_date: str = Field(..., description="ISO format date string")
    initial_capital: float = Field(default=100000.0, gt=0)
    strategy_params: dict = Field(default_factory=dict)
    stored_only: bool = False
    slippage_bps: float = Field(default=5.0, ge=0, le=100)
    commission_flat: float = Field(default=1.0, ge=0)
    commission_pct: float = Field(default=0.001, ge=0, le=0.1)


class WalkForwardConfig(BacktestConfig):
    """Walk-forward analysis configuration."""
    in_sample_days: int = Field(default=180, ge=30)
    out_of_sample_days: int = Field(default=60, ge=7)
    step_days: int = Field(default=30, ge=7)


class MonteCarloConfig(BaseModel):
    """Monte Carlo simulation configuration."""
    backtest_id: Optional[str] = None
    # Or provide inline config
    symbol: Optional[str] = None
    strategy_name: Optional[str] = None
    timeframe: str = "1D"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000.0
    strategy_params: dict = Field(default_factory=dict)
    simulations: int = Field(default=1000, ge=100, le=10000)


class BacktestResultResponse(BaseModel):
    """Response for a backtest run."""
    id: str
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float
    strategy_params: dict
    status: str
    results: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class MonteCarloResult(BaseModel):
    """Monte Carlo simulation results."""
    simulations: int
    percentile_returns: dict  # {"5th": ..., "25th": ..., "50th": ..., "75th": ..., "95th": ...}
    percentile_drawdowns: dict
    percentile_final_equity: dict
    distribution: list[dict]  # [{return, drawdown, final_equity}, ...]


class WalkForwardResult(BaseModel):
    """Walk-forward analysis results."""
    windows: list[dict]
    aggregate_oos_return: float
    aggregate_oos_sharpe: float
    aggregate_oos_max_drawdown: float
    consistency_ratio: float  # % of OOS windows that are profitable
