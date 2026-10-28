"""
Event-driven backtest engine.
Processes candles bar-by-bar through a strategy, simulating realistic fills.
"""

from typing import Optional
from app.engine.execution import (
    ExecutionSimulator, SlippageModel, CommissionModel, CandleData
)
from app.engine.strategy import Strategy
from app.engine.performance import calculate_performance, PerformanceReport


class BacktestEngine:
    """
    Event-driven backtesting engine.
    Feeds candles one-by-one to a strategy and tracks equity over time.
    """

    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float = 100000.0,
        slippage_bps: float = 5.0,
        commission_flat: float = 1.0,
        commission_pct: float = 0.001,
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.equity_snapshots: list[dict] = []

        # Shared execution simulator
        self.simulator = ExecutionSimulator(
            slippage=SlippageModel(basis_points=slippage_bps),
            commission=CommissionModel(flat_fee=commission_flat, percentage=commission_pct),
        )

        # Wire strategy to simulator
        self.strategy.set_simulator(self.simulator)

    def run(self, candles: list[CandleData]) -> PerformanceReport:
        """
        Run the backtest over a list of candles.
        Returns a PerformanceReport with all metrics.
        """
        if not candles:
            return PerformanceReport(initial_capital=self.initial_capital)

        # Initialize strategy
        self.strategy.initialize()

        start_date = candles[0].timestamp
        end_date = candles[-1].timestamp

        for candle in candles:
            # 1. Process pending orders against this bar
            fills = self.simulator.process_bar(candle)

            # 2. Notify strategy of fills
            for fill in fills:
                self.strategy.on_fill(fill)

            # 3. Let strategy react to new bar
            self.strategy.on_bar(candle)

            # 4. Snapshot equity
            equity = self._calculate_equity(candle.close)
            self.equity_snapshots.append({
                "timestamp": candle.timestamp.isoformat(),
                "equity": round(equity, 2),
                "price": candle.close,
            })

        # Calculate performance report
        return calculate_performance(
            fills=self.simulator.fills,
            equity_snapshots=self.equity_snapshots,
            initial_capital=self.initial_capital,
            start_date=start_date,
            end_date=end_date,
        )

    def _calculate_equity(self, current_price: float) -> float:
        """Calculate total equity: cash + unrealized P&L."""
        total_pnl = 0.0
        for pos in self.simulator.positions.values():
            total_pnl += pos.realized_pnl
            if pos.quantity > 0:
                total_pnl += (current_price - pos.avg_entry_price) * pos.quantity
            elif pos.quantity < 0:
                total_pnl += (pos.avg_entry_price - current_price) * abs(pos.quantity)

        return self.initial_capital + total_pnl


def run_backtest(
    strategy_name: str,
    candles: list[CandleData],
    params: dict = None,
    initial_capital: float = 100000.0,
    slippage_bps: float = 5.0,
    commission_flat: float = 1.0,
    commission_pct: float = 0.001,
) -> PerformanceReport:
    """
    Convenience function to run a backtest by strategy name.
    """
    from app.engine.strategy import get_strategy
    # Ensure strategies are registered
    import app.engine.strategies  # noqa: F401

    strategy_cls = get_strategy(strategy_name)
    strategy = strategy_cls()
    strategy.set_params(params or {})

    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=initial_capital,
        slippage_bps=slippage_bps,
        commission_flat=commission_flat,
        commission_pct=commission_pct,
    )

    return engine.run(candles)
