"""
Sample SMA Crossover strategy.
Buys when short SMA crosses above long SMA, sells when it crosses below.
"""

import math

from app.engine.execution import CandleData
from app.engine.strategy import Strategy, register_strategy


@register_strategy("sma_crossover")
class SMACrossoverStrategy(Strategy):
    """
    Simple Moving Average Crossover Strategy.

    Parameters:
        short_period (int): Short SMA period (default: 10)
        long_period (int): Long SMA period (default: 30)
        quantity (float): Trade quantity per signal (default: 100)
    """

    def __init__(self):
        super().__init__()
        self.prices: list[float] = []
        self.short_period: int = 10
        self.long_period: int = 30
        self.quantity: float = 100.0
        self.in_position: bool = False

    @staticmethod
    def param_schema() -> dict:
        return {
            "short_period": {"type": "int", "default": 10, "min": 2, "max": 200},
            "long_period": {"type": "int", "default": 30, "min": 5, "max": 500},
            "quantity": {"type": "float", "default": 100, "min": 0.01},
            "stop_loss_pct": {"type": "float", "default": 0, "min": 0, "max": 99},
            "take_profit_pct": {"type": "float", "default": 0, "min": 0, "max": 99},
        }

    def initialize(self):
        """Set up parameters from config."""
        self.short_period = int(self.param("short_period", 10))
        self.long_period = int(self.param("long_period", 30))
        self.quantity = float(self.param("quantity", 100.0))
        self.stop_loss_pct = float(self.param("stop_loss_pct", 0))
        self.take_profit_pct = float(self.param("take_profit_pct", 0))
        if not (2 <= self.short_period < self.long_period <= 500):
            raise ValueError("SMA periods must satisfy 2 <= short < long <= 500")
        if not math.isfinite(self.quantity) or self.quantity <= 0:
            raise ValueError("Share quantity must be finite and positive")
        if any(
            not math.isfinite(value) or not 0 <= value < 100
            for value in (self.stop_loss_pct, self.take_profit_pct)
        ):
            raise ValueError("Stop and target percentages must be between 0 and 100")
        self.prices = []
        self.in_position = False

    def _sma(self, period: int) -> float | None:
        """Calculate simple moving average."""
        if len(self.prices) < period:
            return None
        return sum(self.prices[-period:]) / period

    def on_bar(self, candle: CandleData):
        """Evaluate SMA crossover signals."""
        self.prices.append(candle.close)

        # Evaluate on the known close and execute at the next open, as with SMA exits.
        position = self.get_position(candle.symbol)
        if self.in_position and position.quantity > 0:
            change = (candle.close / position.avg_entry_price - 1) * 100
            if (self.stop_loss_pct and change <= -self.stop_loss_pct) or (
                self.take_profit_pct and change >= self.take_profit_pct
            ):
                self.sell(candle.symbol, position.quantity)
                self.in_position = False
                return

        if len(self.prices) < self.long_period + 1:
            return

        # Current SMAs
        short_sma = self._sma(self.short_period)
        long_sma = self._sma(self.long_period)

        # Previous SMAs (using prices[:-1])
        prev_prices = self.prices[:-1]
        prev_short = sum(prev_prices[-self.short_period :]) / self.short_period
        prev_long = sum(prev_prices[-self.long_period :]) / self.long_period

        if short_sma is None or long_sma is None:
            return

        # Golden cross: short crosses above long → BUY
        if prev_short <= prev_long and short_sma > long_sma and not self.in_position:
            self.buy(candle.symbol, self.quantity)
            self.in_position = True

        # Death cross: short crosses below long → SELL
        elif prev_short >= prev_long and short_sma < long_sma and self.in_position:
            self.sell(candle.symbol, self.quantity)
            self.in_position = False
