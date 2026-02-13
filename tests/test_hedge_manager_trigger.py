import daytrade_bot.pytest as pytest
from daytrade_bot.datetime import datetime, timezone
from daytrade_bot.hedge_manager import check_hedge_trigger

@pytest.fixture
def logger():
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
    return MockLogger()

def test_trigger_opens_hedge(monkeypatch, logger):
    """Deve abrir nova posição SELL quando trigger é atingido."""
    now = datetime.now(timezone.utc)
    config = {
        "hedge_trigger_profit_buy": -80.0,
        "hedge_sell_volume": 0.01,
        "hedge_sell_sl_pts": 1400,
        "magic_number": 777777,
        "hedge_magic_number": 654321,
    }

    state = {"hedge_manager_active": False}
    buy_metrics = {"profit_buy": -100.0, "open_buy": 1}

    called = {"opened": False}
    def mock_open_order_hedge(**kwargs):
        called["opened"] = True
        class Result:
            retcode = 10009
            order = 123456
        return Result()

    monkeypatch.setattr("hedge_manager.open_order_hedge", mock_open_order_hedge)
    result = check_hedge_trigger(state, buy_metrics, [], 2450.0, now, config, logger, "XAUUSD")

    assert called["opened"]
    assert result["hedge_manager_active"]
    assert result["active_hedge_trade_id"] == 123456
