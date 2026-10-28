"""
Shared execution simulator for order fill logic.
Used by both the Backtest Engine and Replay Engine.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Represents a trading order."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: float = 0.0
    price: Optional[float] = None  # limit/stop price
    status: OrderStatus = OrderStatus.PENDING
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    fill_price: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0


@dataclass
class Fill:
    """Represents an order fill event."""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    slippage_cost: float
    timestamp: datetime
    net_price: float = 0.0  # price after slippage

    def __post_init__(self):
        if self.net_price == 0.0:
            self.net_price = self.price


@dataclass
class Position:
    """Tracks current position in a symbol."""
    symbol: str = ""
    quantity: float = 0.0
    avg_entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class CandleData:
    """Simple candle data container."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "1D"


@dataclass
class SlippageModel:
    """Configurable slippage in basis points."""
    basis_points: float = 5.0  # 5 bps default

    def calculate(self, price: float, side: OrderSide) -> float:
        """Calculate slippage-adjusted price."""
        slip = price * (self.basis_points / 10000.0)
        if side == OrderSide.BUY:
            return price + slip  # pay more when buying
        return price - slip  # receive less when selling


@dataclass
class CommissionModel:
    """Configurable commission: flat fee + percentage."""
    flat_fee: float = 1.0       # $1 per trade
    percentage: float = 0.001   # 0.1% of trade value

    def calculate(self, price: float, quantity: float) -> float:
        """Calculate total commission for a trade."""
        return self.flat_fee + (price * quantity * self.percentage)


class ExecutionSimulator:
    """
    Simulates order execution against candle data.
    Shared between backtest engine and replay engine.
    """

    def __init__(
        self,
        slippage: Optional[SlippageModel] = None,
        commission: Optional[CommissionModel] = None,
    ):
        self.slippage = slippage or SlippageModel()
        self.commission = commission or CommissionModel()
        self.pending_orders: list[Order] = []
        self.fills: list[Fill] = []
        self.positions: dict[str, Position] = {}

    def submit_order(self, order: Order) -> Order:
        """Submit an order for execution."""
        if order.order_type == OrderType.LIMIT and order.price is None:
            order.status = OrderStatus.REJECTED
            return order
        if order.order_type == OrderType.STOP and order.price is None:
            order.status = OrderStatus.REJECTED
            return order
        if order.quantity <= 0:
            order.status = OrderStatus.REJECTED
            return order

        order.status = OrderStatus.PENDING
        self.pending_orders.append(order)
        return order

    def process_bar(self, candle: CandleData) -> list[Fill]:
        """
        Process a single candle bar and fill any eligible pending orders.
        Returns list of fills that occurred on this bar.
        """
        bar_fills = []
        remaining_orders = []

        for order in self.pending_orders:
            fill = self._try_fill(order, candle)
            if fill:
                bar_fills.append(fill)
                self._update_position(fill)
            else:
                remaining_orders.append(order)

        self.pending_orders = remaining_orders
        self.fills.extend(bar_fills)

        # Update unrealized P&L for all positions
        for pos in self.positions.values():
            if pos.quantity > 0:
                pos.unrealized_pnl = (candle.close - pos.avg_entry_price) * pos.quantity
            elif pos.quantity < 0:
                pos.unrealized_pnl = (pos.avg_entry_price - candle.close) * abs(pos.quantity)

        return bar_fills

    def _try_fill(self, order: Order, candle: CandleData) -> Optional[Fill]:
        """Attempt to fill an order against a candle."""

        fill_price = None

        if order.order_type == OrderType.MARKET:
            # Market orders fill at open of the bar
            fill_price = candle.open

        elif order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and candle.low <= order.price:
                fill_price = min(order.price, candle.open)
            elif order.side == OrderSide.SELL and candle.high >= order.price:
                fill_price = max(order.price, candle.open)

        elif order.order_type == OrderType.STOP:
            if order.side == OrderSide.BUY and candle.high >= order.price:
                fill_price = max(order.price, candle.open)
            elif order.side == OrderSide.SELL and candle.low <= order.price:
                fill_price = min(order.price, candle.open)

        if fill_price is None:
            return None

        # Apply slippage
        adjusted_price = self.slippage.calculate(fill_price, order.side)
        slippage_cost = abs(adjusted_price - fill_price) * order.quantity

        # Calculate commission
        comm = self.commission.calculate(adjusted_price, order.quantity)

        # Update order
        order.status = OrderStatus.FILLED
        order.fill_price = adjusted_price
        order.filled_at = candle.timestamp
        order.commission = comm
        order.slippage = slippage_cost

        return Fill(
            order_id=order.id,
            symbol=candle.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            net_price=adjusted_price,
            commission=comm,
            slippage_cost=slippage_cost,
            timestamp=candle.timestamp,
        )

    def _update_position(self, fill: Fill):
        """Update position tracking after a fill."""
        symbol = fill.symbol
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)

        pos = self.positions[symbol]

        if fill.side == OrderSide.BUY:
            if pos.quantity >= 0:
                # Adding to long or opening long
                total_cost = (pos.avg_entry_price * pos.quantity) + (fill.net_price * fill.quantity)
                pos.quantity += fill.quantity
                pos.avg_entry_price = total_cost / pos.quantity if pos.quantity > 0 else 0
            else:
                # Covering short
                pnl = (pos.avg_entry_price - fill.net_price) * min(fill.quantity, abs(pos.quantity))
                pos.realized_pnl += pnl - fill.commission
                pos.quantity += fill.quantity
                if pos.quantity > 0:
                    pos.avg_entry_price = fill.net_price
                elif pos.quantity == 0:
                    pos.avg_entry_price = 0
        else:
            if pos.quantity <= 0:
                # Adding to short or opening short
                total_cost = (pos.avg_entry_price * abs(pos.quantity)) + (fill.net_price * fill.quantity)
                pos.quantity -= fill.quantity
                pos.avg_entry_price = total_cost / abs(pos.quantity) if pos.quantity != 0 else 0
            else:
                # Selling long
                pnl = (fill.net_price - pos.avg_entry_price) * min(fill.quantity, pos.quantity)
                pos.realized_pnl += pnl - fill.commission
                pos.quantity -= fill.quantity
                if pos.quantity < 0:
                    pos.avg_entry_price = fill.net_price
                elif pos.quantity == 0:
                    pos.avg_entry_price = 0

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        for i, order in enumerate(self.pending_orders):
            if order.id == order_id:
                order.status = OrderStatus.CANCELLED
                self.pending_orders.pop(i)
                return True
        return False

    def get_position(self, symbol: str) -> Position:
        """Get current position for a symbol."""
        return self.positions.get(symbol, Position(symbol=symbol))

    def reset(self):
        """Reset simulator state."""
        self.pending_orders.clear()
        self.fills.clear()
        self.positions.clear()
