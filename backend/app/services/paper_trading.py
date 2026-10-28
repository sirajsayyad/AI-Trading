"""Risk checks and portfolio accounting for internal paper trading only."""

from datetime import datetime, timezone

from app.engine.execution import CommissionModel, OrderSide, SlippageModel


def preview_order(
    *,
    cash: float,
    equity: float,
    price: float,
    quantity: float,
    side: str,
    stop_price: float | None,
    take_profit_price: float | None,
    max_risk_percent: float,
    max_position_value_percent: float,
    min_reward_risk_ratio: float,
    require_stop_loss: bool,
    open_positions: int,
    max_open_positions: int,
    daily_pnl: float,
    max_daily_loss_percent: float,
    opening_new_position: bool,
) -> dict:
    """Return deterministic pre-trade metrics and rule violations."""
    errors: list[str] = []
    if price <= 0 or quantity <= 0:
        errors.append("Price and quantity must be positive")
    position_value = max(0, price * quantity)
    risk_per_share = abs(price - stop_price) if stop_price else 0
    risk_amount = risk_per_share * quantity
    risk_percent = risk_amount / equity * 100 if equity else 0
    reward = abs(take_profit_price - price) * quantity if take_profit_price else 0
    reward_risk = reward / risk_amount if risk_amount else 0

    if side == "buy":
        if require_stop_loss and stop_price is None:
            errors.append("A stop-loss is required")
        if stop_price is not None and stop_price >= price:
            errors.append("A long trade stop-loss must be below entry")
        if take_profit_price is not None and take_profit_price <= price:
            errors.append("A long trade target must be above entry")
        if stop_price is not None and risk_percent > max_risk_percent:
            errors.append(f"Trade risk exceeds {max_risk_percent:g}% of equity")
        if stop_price is not None and take_profit_price is not None and reward_risk < min_reward_risk_ratio:
            errors.append(f"Reward-to-risk must be at least {min_reward_risk_ratio:g}:1")
        if position_value > equity * max_position_value_percent / 100:
            errors.append("Position value exceeds the configured limit")
        if opening_new_position and open_positions >= max_open_positions:
            errors.append("Maximum open positions reached")
        estimated_fee = CommissionModel().calculate(price, quantity)
        if position_value + estimated_fee > cash:
            errors.append("Insufficient paper buying power")
    else:
        estimated_fee = CommissionModel().calculate(price, quantity)

    if daily_pnl <= -(equity * max_daily_loss_percent / 100):
        errors.append("Daily loss limit reached")

    return {
        "allowed": not errors,
        "errors": errors,
        "position_value": round(position_value, 2),
        "risk_per_share": round(risk_per_share, 4),
        "risk_amount": round(risk_amount, 2),
        "risk_percent": round(risk_percent, 4),
        "potential_reward": round(reward, 2),
        "reward_risk_ratio": round(reward_risk, 2),
        "estimated_commission": round(estimated_fee, 2),
        "estimated_slippage": round(price * 0.0005 * quantity, 2),
        "buying_power_after": round(cash - position_value - estimated_fee if side == "buy" else cash, 2),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def simulated_fill(price: float, quantity: float, side: str) -> tuple[float, float, float]:
    order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
    fill_price = SlippageModel().calculate(price, order_side)
    commission = CommissionModel().calculate(fill_price, quantity)
    slippage = abs(fill_price - price) * quantity
    return round(fill_price, 6), round(commission, 2), round(slippage, 2)
