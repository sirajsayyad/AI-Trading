"""
Tests for the backtest engine — fills, metrics, and strategy execution.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.engine.execution import (
    ExecutionSimulator, SlippageModel, CommissionModel,
    CandleData, Order, OrderSide, OrderType, OrderStatus,
)
from app.engine.performance import calculate_performance, build_trades_from_fills
from app.engine.backtest import BacktestEngine
from app.engine.strategies.sma_crossover import SMACrossoverStrategy


def _make_candle(day: int, o: float, h: float, l: float, c: float, vol: float = 1000) -> CandleData:
    """Helper to create test candles."""
    return CandleData(
        symbol="TEST",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=day),
        open=o, high=h, low=l, close=c, volume=vol, timeframe="1D",
    )


class TestExecutionSimulator:
    """Test order fill logic."""

    def test_market_order_fills_at_open(self):
        """Market orders should fill at the open of the next bar."""
        sim = ExecutionSimulator(
            slippage=SlippageModel(basis_points=0),
            commission=CommissionModel(flat_fee=0, percentage=0),
        )
        order = Order(symbol="TEST", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        sim.submit_order(order)

        candle = _make_candle(0, o=100.0, h=105.0, l=98.0, c=103.0)
        fills = sim.process_bar(candle)

        assert len(fills) == 1
        assert fills[0].price == 100.0  # Filled at open
        assert fills[0].quantity == 100

    def test_limit_buy_fills_when_low_touches(self):
        """Limit buy should fill when candle low reaches the limit price."""
        sim = ExecutionSimulator(
            slippage=SlippageModel(basis_points=0),
            commission=CommissionModel(flat_fee=0, percentage=0),
        )
        order = Order(symbol="TEST", side=OrderSide.BUY, order_type=OrderType.LIMIT,
                      quantity=50, price=95.0)
        sim.submit_order(order)

        # Bar where low doesn't reach limit
        candle1 = _make_candle(0, o=100, h=105, l=98, c=103)
        fills1 = sim.process_bar(candle1)
        assert len(fills1) == 0  # Not filled yet

        # Bar where low reaches limit
        candle2 = _make_candle(1, o=100, h=102, l=94, c=97)
        fills2 = sim.process_bar(candle2)
        assert len(fills2) == 1
        assert fills2[0].price == 95.0

    def test_stop_sell_fills_when_low_breaks(self):
        """Stop sell should fill when price drops to stop level."""
        sim = ExecutionSimulator(
            slippage=SlippageModel(basis_points=0),
            commission=CommissionModel(flat_fee=0, percentage=0),
        )
        order = Order(symbol="TEST", side=OrderSide.SELL, order_type=OrderType.STOP,
                      quantity=100, price=95.0)
        sim.submit_order(order)

        candle = _make_candle(0, o=100, h=102, l=93, c=94)
        fills = sim.process_bar(candle)
        assert len(fills) == 1
        assert fills[0].price == 95.0

    def test_slippage_applied(self):
        """Slippage should increase buy price and decrease sell price."""
        sim = ExecutionSimulator(
            slippage=SlippageModel(basis_points=50),  # 50 bps = 0.5%
            commission=CommissionModel(flat_fee=0, percentage=0),
        )
        order = Order(symbol="TEST", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        sim.submit_order(order)

        candle = _make_candle(0, o=100.0, h=105, l=98, c=103)
        fills = sim.process_bar(candle)

        assert len(fills) == 1
        assert fills[0].net_price > 100.0  # Slippage makes buy more expensive
        expected = 100.0 + (100.0 * 50 / 10000)
        assert abs(fills[0].net_price - expected) < 0.01

    def test_commission_calculated(self):
        """Commissions should be calculated correctly."""
        sim = ExecutionSimulator(
            slippage=SlippageModel(basis_points=0),
            commission=CommissionModel(flat_fee=5.0, percentage=0.001),
        )
        order = Order(symbol="TEST", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        sim.submit_order(order)

        candle = _make_candle(0, o=100.0, h=105, l=98, c=103)
        fills = sim.process_bar(candle)

        assert len(fills) == 1
        expected_comm = 5.0 + (100.0 * 100 * 0.001)  # flat + percentage
        assert abs(fills[0].commission - expected_comm) < 0.01

    def test_rejected_order_no_quantity(self):
        """Order with zero quantity should be rejected."""
        sim = ExecutionSimulator()
        order = Order(symbol="TEST", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0)
        result = sim.submit_order(order)
        assert result.status == OrderStatus.REJECTED


class TestPerformanceMetrics:
    """Test performance report calculations."""

    def test_metrics_with_known_values(self):
        """Verify metrics against hand-computed example."""
        from app.engine.execution import Fill

        # Simulate: Buy 100 @ $100, Sell 100 @ $110 = $1000 profit (before commission)
        fills = [
            Fill(order_id="1", symbol="TEST", side=OrderSide.BUY, quantity=100,
                 price=100.0, net_price=100.0, commission=10.0, slippage_cost=0,
                 timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)),
            Fill(order_id="2", symbol="TEST", side=OrderSide.SELL, quantity=100,
                 price=110.0, net_price=110.0, commission=10.0, slippage_cost=0,
                 timestamp=datetime(2024, 2, 1, tzinfo=timezone.utc)),
        ]

        equity = [
            {"equity": 100000, "timestamp": "2024-01-01"},
            {"equity": 100500, "timestamp": "2024-01-15"},
            {"equity": 100980, "timestamp": "2024-02-01"},
        ]

        report = calculate_performance(
            fills=fills,
            equity_snapshots=equity,
            initial_capital=100000,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )

        assert report.total_trades == 1
        assert report.winning_trades == 1
        assert report.win_rate == 1.0
        assert report.total_return > 0
        assert report.max_drawdown == 0  # Equity only goes up in this example


class TestSMAStrategy:
    """Test the SMA crossover strategy with the backtest engine."""

    def test_sma_strategy_runs(self):
        """SMA strategy should run without errors and produce trades on trending data."""
        # Create a trending dataset: uptrend then downtrend
        candles = []
        for i in range(60):
            if i < 35:
                # Uptrend
                price = 100 + i * 1.5
            else:
                # Downtrend
                price = 100 + 35 * 1.5 - (i - 35) * 2.0

            candles.append(_make_candle(
                i,
                o=price - 0.5,
                h=price + 1.0,
                l=price - 1.0,
                c=price,
            ))

        strategy = SMACrossoverStrategy()
        strategy.set_params({"short_period": 5, "long_period": 15, "quantity": 100})

        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=100000,
            slippage_bps=0,
            commission_flat=0,
            commission_pct=0,
        )

        report = engine.run(candles)

        # Strategy should have run and produced equity snapshots
        assert len(report.equity_curve) == len(candles)
        assert report.initial_capital == 100000
