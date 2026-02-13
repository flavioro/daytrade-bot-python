# test_drawdown_manager.py
from daytrade_bot.drawdown_manager import get_worst_positions_to_close, check_drawdown_trigger
from daytrade_bot.types import SimpleNamespace # Simples 'mock' de objeto

def test_get_worst_positions():
    # 1. Cria "posições" falsas (mocks)
    pos1 = SimpleNamespace(ticket=1, profit=10.0)
    pos2 = SimpleNamespace(ticket=2, profit=-50.0)
    pos3 = SimpleNamespace(ticket=3, profit=-20.0)
    positions = [pos1, pos2, pos3]

    # 2. Testa fechando a 1 pior
    worst_one = get_worst_positions_to_close(positions, 1)
    assert len(worst_one) == 1
    assert worst_one[0].ticket == 2 # Deve ser a pos2 (-50.0)

    # 3. Testa fechando as 2 piores
    worst_two = get_worst_positions_to_close(positions, 2)
    assert len(worst_two) == 2
    assert worst_two[0].ticket == 2 # A pior
    assert worst_two[1].ticket == 3 # A segunda pior

def test_drawdown_trigger():
    threshold = -100.0

    # 1. Testa acima do limite (Não deve disparar)
    assert check_drawdown_trigger(total_profit=-90.0, dd_threshold=threshold) == False

    # 2. Testa no limite (Deve disparar)
    assert check_drawdown_trigger(total_profit=-100.0, dd_threshold=threshold) == True

    # 3. Testa abaixo do limite (Deve disparar)
    assert check_drawdown_trigger(total_profit=-110.0, dd_threshold=threshold) == True
    
test_drawdown_trigger()
test_get_worst_positions()