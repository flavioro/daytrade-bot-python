import daytrade_bot.pytest as pytest
import daytrade_bot.json as json
from daytrade_bot.datetime import datetime, timezone
# from unittest.mock import mock_open, patch
from daytrade_bot.hedge_manager import load_hedge_state, save_hedge_state

@pytest.fixture
def logger():
    """Mock simples de logger com métodos .info/.error/etc"""
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
    return MockLogger()

def test_load_hedge_state_default(tmp_path, logger):
    """Deve retornar o estado padrão se o arquivo não existir."""
    config = {"hedge_state_file": tmp_path / "missing.json"}
    state = load_hedge_state(config, logger)
    assert not state["hedge_manager_active"]
    assert state["active_hedge_trade_id"] is None

def test_load_hedge_state_existing(tmp_path, logger):
    """Deve carregar corretamente o estado de um arquivo existente."""
    fake_state = {
        "hedge_manager_active": True,
        "active_hedge_trade_id": 12345,
        "hedge_manager_cooldown_until": datetime.now(timezone.utc).isoformat()
    }
    file_path = tmp_path / "state.json"
    file_path.write_text(json.dumps(fake_state))

    config = {"hedge_state_file": str(file_path)}
    state = load_hedge_state(config, logger)

    assert state["hedge_manager_active"]
    assert isinstance(state["hedge_manager_cooldown_until"], datetime)

def test_save_hedge_state_creates_file(tmp_path, logger):
    """Deve salvar o estado corretamente em JSON."""
    config = {"hedge_state_file": str(tmp_path / "state_out.json")}
    state = {
        "hedge_manager_active": True,
        "active_hedge_trade_id": 555,
        "hedge_manager_cooldown_until": datetime(2025, 10, 21, tzinfo=timezone.utc)
    }

    save_hedge_state(state, config, logger)
    saved = json.loads(open(config["hedge_state_file"]).read())
    assert saved["active_hedge_trade_id"] == 555
    assert isinstance(saved["hedge_manager_cooldown_until"], str)
