import json
from datetime import datetime, timezone

import pytest

from daytrade_bot.hedge_manager import load_hedge_state, save_hedge_state


@pytest.fixture
def logger():
    class MockLogger:
        def info(self, msg): pass
        def error(self, msg): pass
        def warning(self, msg): pass
    return MockLogger()


def test_load_hedge_state_default(tmp_path, logger):
    """Deve retornar o estado padrão se o arquivo não existir."""
    config = {"hedge_state_file": str(tmp_path / "missing.json")}
    state = load_hedge_state(config, logger)
    assert state["hedge_manager_active"] is False
    assert state["active_hedge_trade_id"] is None


def test_load_hedge_state_existing(tmp_path, logger):
    """Deve carregar corretamente o estado de um arquivo existente."""
    fake_state = {
        "hedge_manager_active": True,
        "active_hedge_trade_id": 12345,
        "hedge_manager_cooldown_until": datetime.now(timezone.utc).isoformat(),
    }
    file_path = tmp_path / "state.json"
    file_path.write_text(json.dumps(fake_state), encoding="utf-8")

    config = {"hedge_state_file": str(file_path)}
    state = load_hedge_state(config, logger)

    assert state["hedge_manager_active"] is True
    assert isinstance(state["hedge_manager_cooldown_until"], datetime)


def test_save_hedge_state_creates_file(tmp_path, logger):
    """Deve salvar o estado corretamente em JSON."""
    out_file = tmp_path / "state_out.json"
    config = {"hedge_state_file": str(out_file)}
    state = {
        "hedge_manager_active": True,
        "active_hedge_trade_id": 555,
        "hedge_manager_cooldown_until": datetime(2025, 10, 21, tzinfo=timezone.utc),
    }

    save_hedge_state(state, config, logger)
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved["active_hedge_trade_id"] == 555
    assert isinstance(saved["hedge_manager_cooldown_until"], str)
