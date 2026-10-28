"""
Sample SMA Crossover strategy.
Buys when short SMA crosses above long SMA, sells when it crosses below.
"""

from app.engine.strategy import Strategy, register_strategy
from app.engine.execution import CandleData


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
        }

    def initialize(self):
        """Set up parameters from config."""
        self.short_period = int(self.param("short_period", 10))
        self.long_period = int(self.param("long_period", 30))
        self.quantity = float(self.param("quantity", 100.0))
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

        if len(self.prices) < self.long_period + 1:
            return

        # Current SMAs
        short_sma = self._sma(self.short_period)
        long_sma = self._sma(self.long_period)

        # Previous SMAs (using prices[:-1])
        prev_prices = self.prices[:-1]
        prev_short = sum(prev_prices[-self.short_period:]) / self.short_period
        prev_long = sum(prev_prices[-self.long_period:]) / self.long_period

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
