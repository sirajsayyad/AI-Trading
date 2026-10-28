import pytest

from app.services.risk_service import calculate_position_size


def test_position_size_respects_risk_budget():
    result = calculate_position_size(100_000, 1, 100, 95, 10)
    assert result["quantity"] == 198
    assert result["estimated_max_loss"] == 1000


def test_position_size_rejects_equal_prices():
    with pytest.raises(ValueError, match="different"):
        calculate_position_size(100_000, 1, 100, 100)
