from app.services.paper_trading import preview_order, simulated_fill


def valid_preview(**changes):
    values = {
        "cash": 100_000, "equity": 100_000, "price": 100, "quantity": 100,
        "side": "buy", "stop_price": 95, "take_profit_price": 110,
        "max_risk_percent": 1, "max_position_value_percent": 20,
        "min_reward_risk_ratio": 2, "require_stop_loss": True,
        "open_positions": 0, "max_open_positions": 5, "daily_pnl": 0,
        "max_daily_loss_percent": 3, "opening_new_position": True,
    }
    values.update(changes)
    return preview_order(**values)


def test_valid_paper_order_preview():
    result = valid_preview()
    assert result["allowed"] is True
    assert result["risk_amount"] == 500
    assert result["reward_risk_ratio"] == 2


def test_paper_order_enforces_stop_and_daily_loss():
    result = valid_preview(stop_price=None, daily_pnl=-3_000)
    assert result["allowed"] is False
    assert "A stop-loss is required" in result["errors"]
    assert "Daily loss limit reached" in result["errors"]


def test_simulated_fill_is_worse_for_trader():
    buy, _, _ = simulated_fill(100, 10, "buy")
    sell, _, _ = simulated_fill(100, 10, "sell")
    assert buy > 100 > sell
