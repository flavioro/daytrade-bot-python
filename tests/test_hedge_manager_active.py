from datetime import datetime, timezone, timedelta

import pytest

import daytrade_bot.hedge_manager as hm


class MockTrade:
    def __init__(self, profit, time):
        self.profit = profit
        self.time = time
        self.ticket = 987654


def test_manage_active_hedge_close_by_drawdown(monkeypatch):
    """Fecha a posição quando drawdown >= limite."""
    logger = type("L", (), {"info": lambda *a, **k: None, "error": lambda *a, **k: None})
    now = datetime.now(timezone.utc)

    trade = MockTrade(profit=50.0, time=(now - timedelta(minutes=10)).timestamp())
    state = {"active_hedge_profit_max": 70.0, "hedge_manager_active": True}

    called = {"closed": False}

    def mock_close_position(t, logger):
        called["closed"] = True
        return True

    monkeypatch.setattr(hm, "close_position", mock_close_position)

    config = {"hedge_close_drawdown_cash": 10.0, "hedge_cooldown_minutes": 600}
    result = hm.manage_active_hedge(state, trade, 2450.0, now, config, logger)
    assert called["closed"] is True
    assert result["hedge_manager_active"] is False
