from types import SimpleNamespace

from daytrade_bot.drawdown_manager import (
    get_worst_positions_to_close,
    check_drawdown_trigger,
)


def test_get_worst_positions():
    pos1 = SimpleNamespace(ticket=1, profit=10.0)
    pos2 = SimpleNamespace(ticket=2, profit=-50.0)
    pos3 = SimpleNamespace(ticket=3, profit=-20.0)
    positions = [pos1, pos2, pos3]

    worst_one = get_worst_positions_to_close(positions, 1)
    assert len(worst_one) == 1
    assert worst_one[0].ticket == 2  # -50.0

    worst_two = get_worst_positions_to_close(positions, 2)
    assert len(worst_two) == 2
    assert worst_two[0].ticket == 2
    assert worst_two[1].ticket == 3


def test_drawdown_trigger():
    threshold = -100.0

    assert check_drawdown_trigger(total_profit=-90.0, dd_threshold=threshold) is False
    assert check_drawdown_trigger(total_profit=-100.0, dd_threshold=threshold) is True
    assert check_drawdown_trigger(total_profit=-110.0, dd_threshold=threshold) is True
