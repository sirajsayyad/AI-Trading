"""
Tests for behavioral analytics flagging logic.
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.services.behavioral_analytics import analyze_behavior


def _make_trade(day: int, pnl: float, quantity: float = 100, symbol: str = "TEST") -> dict:
    """Helper to create a synthetic trade."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
    return {
        "symbol": symbol,
        "side": "long",
        "entry_price": 100.0,
        "exit_price": 100.0 + (pnl / quantity),
        "quantity": quantity,
        "entry_time": base.isoformat(),
        "exit_time": (base + timedelta(hours=4)).isoformat(),
        "pnl": pnl,
        "duration_hours": 4.0,
    }


class TestOvertradingDetection:
    """Test overtrading flag detection."""

    def test_normal_frequency_no_flag(self):
        """Normal trading frequency should not trigger flag."""
        # 5 trades per day for 5 days = 25 trades
        trades = [_make_trade(day=i // 5, pnl=10.0 * (1 if i % 2 == 0 else -1)) for i in range(25)]
        flags = analyze_behavior(trades, account_size=100000)
        overtrading = [f for f in flags if f["flag_type"] == "overtrading"]
        assert len(overtrading) == 0

    def test_excessive_trading_flagged(self):
        """>20 trades in a single day should trigger overtrading flag."""
        # 25 trades all on same day
        trades = [_make_trade(day=0, pnl=10.0) for _ in range(25)]
        flags = analyze_behavior(trades, account_size=100000)
        overtrading = [f for f in flags if f["flag_type"] == "overtrading"]
        assert len(overtrading) == 1
        assert overtrading[0]["severity"] in ("medium", "high")


class TestPoorRiskReward:
    """Test poor risk-reward detection."""

    def test_good_rr_no_flag(self):
        """Avg win > avg loss should not trigger flag."""
        trades = [
            _make_trade(0, pnl=200),
            _make_trade(1, pnl=300),
            _make_trade(2, pnl=-100),
            _make_trade(3, pnl=-50),
        ]
        flags = analyze_behavior(trades)
        poor_rr = [f for f in flags if f["flag_type"] == "poor_risk_reward"]
        assert len(poor_rr) == 0

    def test_poor_rr_flagged(self):
        """Avg loss > avg win should trigger flag."""
        trades = [
            _make_trade(0, pnl=50),
            _make_trade(1, pnl=30),
            _make_trade(2, pnl=-200),
            _make_trade(3, pnl=-180),
        ]
        flags = analyze_behavior(trades)
        poor_rr = [f for f in flags if f["flag_type"] == "poor_risk_reward"]
        assert len(poor_rr) == 1


class TestRevengeTradingDetection:
    """Test revenge trading detection."""

    def test_no_revenge_trading(self):
        """Consistent position sizes should not trigger flag."""
        trades = [
            _make_trade(0, pnl=-50, quantity=100),
            _make_trade(1, pnl=30, quantity=100),
            _make_trade(2, pnl=-20, quantity=100),
            _make_trade(3, pnl=40, quantity=100),
        ]
        flags = analyze_behavior(trades)
        revenge = [f for f in flags if f["flag_type"] == "revenge_trading"]
        assert len(revenge) == 0

    def test_revenge_trading_flagged(self):
        """Increasing size after losses should trigger flag."""
        trades = [
            _make_trade(0, pnl=-50, quantity=100),
            _make_trade(1, pnl=-100, quantity=200),   # 2x after loss
            _make_trade(2, pnl=-200, quantity=400),    # 2x after loss
            _make_trade(3, pnl=100, quantity=800),     # 2x after loss
        ]
        flags = analyze_behavior(trades)
        revenge = [f for f in flags if f["flag_type"] == "revenge_trading"]
        assert len(revenge) == 1
