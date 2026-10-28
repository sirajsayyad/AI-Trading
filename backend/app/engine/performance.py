"""
Performance metrics calculator for backtest results.
"""

from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Optional

from app.engine.execution import Fill, OrderSide


@dataclass
class Trade:
    """A completed round-trip trade (entry + exit)."""
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    commission: float
    net_pnl: float
    duration_hours: float = 0.0

    def __post_init__(self):
        if self.duration_hours == 0.0:
            delta = self.exit_time - self.entry_time
            self.duration_hours = delta.total_seconds() / 3600


@dataclass
class PerformanceReport:
    """Comprehensive performance metrics for a backtest."""

    # Core metrics
    total_return: float = 0.0
    total_return_pct: float = 0.0
    cagr: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0

    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade_pnl: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    # Equity curve
    initial_capital: float = 100000.0
    final_equity: float = 0.0
    equity_curve: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)

    # Time info
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "total_return": round(self.total_return, 2),
            "total_return_pct": round(self.total_return_pct, 4),
            "cagr": round(self.cagr, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "avg_trade_pnl": round(self.avg_trade_pnl, 2),
            "largest_win": round(self.largest_win, 2),
            "largest_loss": round(self.largest_loss, 2),
            "initial_capital": self.initial_capital,
            "final_equity": round(self.final_equity, 2),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "duration_days": self.duration_days,
            "equity_curve": self.equity_curve,
            "trades": self.trades,
        }


def build_trades_from_fills(fills: list[Fill]) -> list[Trade]:
    """
    Match entry/exit fills into round-trip trades.
    Simple FIFO matching: first buy matched with first sell.
    """
    trades = []
    open_fills: dict[str, list[Fill]] = {}  # symbol -> list of entry fills

    for fill in fills:
        symbol = fill.symbol

        if symbol not in open_fills:
            open_fills[symbol] = []

        entries = open_fills[symbol]

        if fill.side == OrderSide.BUY:
            # Check if closing a short
            short_entries = [f for f in entries if f.side == OrderSide.SELL]
            if short_entries:
                entry = short_entries[0]
                entries.remove(entry)
                pnl = (entry.net_price - fill.net_price) * fill.quantity
                comm = entry.commission + fill.commission
                trades.append(Trade(
                    symbol=symbol,
                    side="short",
                    entry_price=entry.net_price,
                    exit_price=fill.net_price,
                    quantity=fill.quantity,
                    entry_time=entry.timestamp,
                    exit_time=fill.timestamp,
                    pnl=pnl,
                    commission=comm,
                    net_pnl=pnl - comm,
                ))
            else:
                entries.append(fill)
        else:
            # Check if closing a long
            long_entries = [f for f in entries if f.side == OrderSide.BUY]
            if long_entries:
                entry = long_entries[0]
                entries.remove(entry)
                pnl = (fill.net_price - entry.net_price) * fill.quantity
                comm = entry.commission + fill.commission
                trades.append(Trade(
                    symbol=symbol,
                    side="long",
                    entry_price=entry.net_price,
                    exit_price=fill.net_price,
                    quantity=fill.quantity,
                    entry_time=entry.timestamp,
                    exit_time=fill.timestamp,
                    pnl=pnl,
                    commission=comm,
                    net_pnl=pnl - comm,
                ))
            else:
                entries.append(fill)

    return trades


def calculate_performance(
    fills: list[Fill],
    equity_snapshots: list[dict],
    initial_capital: float = 100000.0,
    start_date: datetime = None,
    end_date: datetime = None,
) -> PerformanceReport:
    """
    Calculate comprehensive performance metrics from fills and equity curve.
    """
    report = PerformanceReport(initial_capital=initial_capital)

    # Build trades
    trades = build_trades_from_fills(fills)
    report.total_trades = len(trades)

    if not trades:
        report.final_equity = initial_capital
        report.equity_curve = equity_snapshots
        return report

    # Trade statistics
    winning = [t for t in trades if t.net_pnl > 0]
    losing = [t for t in trades if t.net_pnl <= 0]

    report.winning_trades = len(winning)
    report.losing_trades = len(losing)
    report.win_rate = len(winning) / len(trades) if trades else 0

    gross_profit = sum(t.net_pnl for t in winning)
    gross_loss = abs(sum(t.net_pnl for t in losing))

    report.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
    report.avg_win = gross_profit / len(winning) if winning else 0
    report.avg_loss = -gross_loss / len(losing) if losing else 0
    report.avg_trade_pnl = sum(t.net_pnl for t in trades) / len(trades)
    report.largest_win = max((t.net_pnl for t in trades), default=0)
    report.largest_loss = min((t.net_pnl for t in trades), default=0)

    # Total return
    total_pnl = sum(t.net_pnl for t in trades)
    report.total_return = total_pnl
    report.total_return_pct = total_pnl / initial_capital
    report.final_equity = initial_capital + total_pnl

    # Dates
    if start_date and end_date:
        report.start_date = start_date.isoformat()
        report.end_date = end_date.isoformat()
        delta = end_date - start_date
        report.duration_days = delta.days

    # CAGR
    if report.duration_days > 0 and report.final_equity > 0:
        years = report.duration_days / 365.25
        if years > 0:
            report.cagr = (report.final_equity / initial_capital) ** (1 / years) - 1

    # Max Drawdown from equity curve
    if equity_snapshots:
        equities = [s["equity"] for s in equity_snapshots]
        peak = equities[0]
        max_dd = 0
        max_dd_pct = 0

        for eq in equities:
            if eq > peak:
                peak = eq
            dd = peak - eq
            dd_pct = dd / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        report.max_drawdown = max_dd
        report.max_drawdown_pct = max_dd_pct

    # Sharpe Ratio (annualized, assuming daily returns)
    if len(equity_snapshots) > 1:
        equities = [s["equity"] for s in equity_snapshots]
        returns = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                returns.append((equities[i] - equities[i - 1]) / equities[i - 1])

        if returns:
            avg_return = sum(returns) / len(returns)
            std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))

            if std_return > 0:
                report.sharpe_ratio = (avg_return / std_return) * math.sqrt(252)

            # Sortino (downside deviation only)
            downside_returns = [r for r in returns if r < 0]
            if downside_returns:
                downside_std = math.sqrt(
                    sum(r ** 2 for r in downside_returns) / len(downside_returns)
                )
                if downside_std > 0:
                    report.sortino_ratio = (avg_return / downside_std) * math.sqrt(252)

    # Store trade data for API response
    report.trades = [
        {
            "symbol": t.symbol,
            "side": t.side,
            "entry_price": round(t.entry_price, 4),
            "exit_price": round(t.exit_price, 4),
            "quantity": t.quantity,
            "entry_time": t.entry_time.isoformat(),
            "exit_time": t.exit_time.isoformat(),
            "pnl": round(t.net_pnl, 2),
            "duration_hours": round(t.duration_hours, 1),
        }
        for t in trades
    ]
    report.equity_curve = equity_snapshots

    return report
