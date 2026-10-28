"""
Behavioral analytics service.
Analyzes user trade history and flags common behavioral patterns.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class BehavioralFlag:
    """A detected behavioral pattern."""
    flag_type: str  # "overtrading", "poor_risk_reward", "revenge_trading"
    severity: str   # "low", "medium", "high"
    description: str
    details: dict
    recommendation: str


def analyze_behavior(trades: list[dict], account_size: float = 100000.0) -> list[dict]:
    """
    Analyze trade history and flag behavioral patterns.
    Returns structured flags (not prose) for frontend visualization.
    """
    if not trades or len(trades) < 3:
        return []

    flags = []

    # 1. Overtrading detection
    overtrading = _detect_overtrading(trades, account_size)
    if overtrading:
        flags.append(overtrading)

    # 2. Poor risk-reward
    risk_reward = _detect_poor_risk_reward(trades)
    if risk_reward:
        flags.append(risk_reward)

    # 3. Revenge trading
    revenge = _detect_revenge_trading(trades)
    if revenge:
        flags.append(revenge)

    return [_flag_to_dict(f) for f in flags]


def _detect_overtrading(trades: list[dict], account_size: float) -> Optional[BehavioralFlag]:
    """
    Detect overtrading: excessive trade frequency relative to account size.
    Threshold: >20 trades per day or >5% of account risked per day.
    """
    # Group trades by date
    trades_by_date: dict[str, list] = {}
    for t in trades:
        entry_time = t.get("entry_time", "")
        if entry_time:
            try:
                date = datetime.fromisoformat(entry_time).strftime("%Y-%m-%d")
                if date not in trades_by_date:
                    trades_by_date[date] = []
                trades_by_date[date].append(t)
            except (ValueError, TypeError):
                pass

    if not trades_by_date:
        return None

    max_daily = max(len(v) for v in trades_by_date.values())
    avg_daily = len(trades) / len(trades_by_date)

    # Calculate daily volume
    total_volume = sum(
        abs(t.get("quantity", 0) * t.get("entry_price", 0))
        for t in trades
    )
    avg_daily_volume = total_volume / len(trades_by_date) if trades_by_date else 0
    volume_ratio = avg_daily_volume / account_size if account_size > 0 else 0

    if max_daily > 20 or avg_daily > 10 or volume_ratio > 0.5:
        severity = "high" if max_daily > 30 or volume_ratio > 1.0 else "medium" if max_daily > 20 else "low"
        return BehavioralFlag(
            flag_type="overtrading",
            severity=severity,
            description=f"Averaging {avg_daily:.1f} trades/day with peak of {max_daily} trades in a single day",
            details={
                "avg_daily_trades": round(avg_daily, 1),
                "max_daily_trades": max_daily,
                "daily_volume_ratio": round(volume_ratio, 2),
                "total_trading_days": len(trades_by_date),
            },
            recommendation="Reduce trade frequency. Focus on high-conviction setups only. Consider implementing a maximum daily trade limit.",
        )

    return None


def _detect_poor_risk_reward(trades: list[dict]) -> Optional[BehavioralFlag]:
    """
    Detect poor risk-reward: average loss > average win.
    """
    winners = [t for t in trades if t.get("pnl", t.get("net_pnl", 0)) > 0]
    losers = [t for t in trades if t.get("pnl", t.get("net_pnl", 0)) < 0]

    if not winners or not losers:
        return None

    avg_win = sum(t.get("pnl", t.get("net_pnl", 0)) for t in winners) / len(winners)
    avg_loss = abs(sum(t.get("pnl", t.get("net_pnl", 0)) for t in losers) / len(losers))

    risk_reward = avg_win / avg_loss if avg_loss > 0 else float('inf')

    if avg_loss > avg_win:
        severity = "high" if risk_reward < 0.5 else "medium"
        return BehavioralFlag(
            flag_type="poor_risk_reward",
            severity=severity,
            description=f"Average loss (${avg_loss:.2f}) exceeds average win (${avg_win:.2f}). Risk/reward ratio: {risk_reward:.2f}",
            details={
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "risk_reward_ratio": round(risk_reward, 2),
                "winning_trades": len(winners),
                "losing_trades": len(losers),
            },
            recommendation="Improve risk/reward by widening profit targets or tightening stop losses. Aim for at least 1.5:1 reward-to-risk.",
        )

    return None


def _detect_revenge_trading(trades: list[dict]) -> Optional[BehavioralFlag]:
    """
    Detect revenge trading: increased position size immediately after a loss.
    """
    if len(trades) < 3:
        return None

    revenge_count = 0
    total_after_loss = 0

    for i in range(1, len(trades)):
        prev = trades[i - 1]
        curr = trades[i]

        prev_pnl = prev.get("pnl", prev.get("net_pnl", 0))
        if prev_pnl < 0:
            total_after_loss += 1
            prev_qty = abs(prev.get("quantity", 1))
            curr_qty = abs(curr.get("quantity", 1))

            if curr_qty > prev_qty * 1.3:  # 30% larger position
                revenge_count += 1

    if revenge_count > 0 and total_after_loss > 0:
        ratio = revenge_count / total_after_loss
        if ratio > 0.2:  # >20% of post-loss trades are larger
            severity = "high" if ratio > 0.5 else "medium" if ratio > 0.3 else "low"
            return BehavioralFlag(
                flag_type="revenge_trading",
                severity=severity,
                description=f"Increased position size after {revenge_count} of {total_after_loss} losing trades ({ratio:.0%} of the time)",
                details={
                    "revenge_trade_count": revenge_count,
                    "total_post_loss_trades": total_after_loss,
                    "revenge_ratio": round(ratio, 2),
                },
                recommendation="After a loss, take a pause before the next trade. Never increase position size to recover losses — this compounds risk.",
            )

    return None


def _flag_to_dict(flag: BehavioralFlag) -> dict:
    """Convert flag to dict for API response."""
    return {
        "flag_type": flag.flag_type,
        "severity": flag.severity,
        "description": flag.description,
        "details": flag.details,
        "recommendation": flag.recommendation,
    }
