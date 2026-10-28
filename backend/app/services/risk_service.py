"""Small, deterministic risk calculations used by paper trading and replay."""


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_price: float,
    commission_per_trade: float = 0.0,
) -> dict:
    """Return a conservative whole-unit position size and its risk summary."""
    values = (account_balance, risk_percent, entry_price, stop_price, commission_per_trade)
    if any(value < 0 for value in values) or entry_price <= 0 or stop_price <= 0:
        raise ValueError("All values must be non-negative and prices must be positive")
    if entry_price == stop_price:
        raise ValueError("Entry and stop prices must be different")

    risk_budget = account_balance * risk_percent / 100
    risk_per_unit = abs(entry_price - stop_price)
    units = int(max(0, (risk_budget - commission_per_trade) // risk_per_unit))
    return {
        "risk_budget": round(risk_budget, 2),
        "risk_per_unit": round(risk_per_unit, 4),
        "quantity": units,
        "notional_value": round(units * entry_price, 2),
        "estimated_max_loss": round(units * risk_per_unit + commission_per_trade, 2),
    }
