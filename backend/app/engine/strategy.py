"""
Abstract strategy base class and strategy registry.
Users subclass Strategy to implement custom trading logic.
"""

from abc import ABC, abstractmethod
from typing import Optional
from app.engine.execution import CandleData, Order, Fill, ExecutionSimulator


class Strategy(ABC):
    """
    Base class for trading strategies.
    Subclass this and implement initialize(), on_bar(), and on_fill().
    """

    def __init__(self):
        self.simulator: Optional[ExecutionSimulator] = None
        self._params: dict = {}

    def set_simulator(self, simulator: ExecutionSimulator):
        """Inject the execution simulator (called by the backtest engine)."""
        self.simulator = simulator

    def set_params(self, params: dict):
        """Set strategy parameters."""
        self._params = params

    def param(self, key: str, default=None):
        """Get a strategy parameter."""
        return self._params.get(key, default)

    def buy(self, symbol: str, quantity: float, order_type: str = "market", price: float = None) -> Order:
        """Place a buy order."""
        from app.engine.execution import OrderSide, OrderType
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType(order_type),
            quantity=quantity,
            price=price,
        )
        return self.simulator.submit_order(order)

    def sell(self, symbol: str, quantity: float, order_type: str = "market", price: float = None) -> Order:
        """Place a sell order."""
        from app.engine.execution import OrderSide, OrderType
        order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType(order_type),
            quantity=quantity,
            price=price,
        )
        return self.simulator.submit_order(order)

    def get_position(self, symbol: str):
        """Get current position for a symbol."""
        return self.simulator.get_position(symbol)

    @abstractmethod
    def initialize(self):
        """Called once before the backtest starts. Set up indicators, state, etc."""
        ...

    @abstractmethod
    def on_bar(self, candle: CandleData):
        """Called for each new candle bar. Implement trading logic here."""
        ...

    def on_fill(self, fill: Fill):
        """Called when an order is filled. Override for fill-based logic."""
        pass


# ─── Strategy Registry ──────────────────────────────────────────

_STRATEGY_REGISTRY: dict[str, type[Strategy]] = {}


def register_strategy(name: str):
    """Decorator to register a strategy class."""
    def decorator(cls: type[Strategy]):
        _STRATEGY_REGISTRY[name] = cls
        return cls
    return decorator


def get_strategy(name: str) -> type[Strategy]:
    """Get a strategy class by name."""
    if name not in _STRATEGY_REGISTRY:
        available = list(_STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy: {name}. Available: {available}")
    return _STRATEGY_REGISTRY[name]


def list_strategies() -> list[dict]:
    """List all registered strategies with their parameter schemas."""
    strategies = []
    for name, cls in _STRATEGY_REGISTRY.items():
        schema = {}
        if hasattr(cls, 'param_schema'):
            schema = cls.param_schema()
        strategies.append({"name": name, "params": schema})
    return strategies
