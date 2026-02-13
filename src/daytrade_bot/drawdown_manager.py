# drawdown_manager.py
import MetaTrader5 as mt5
import logging # Usar o 'logging' padrão para type hinting do logger
from .mt5_order import get_all_open_positions, close_position

"""
-----------------------------------------------------------------------------
 FUNÇÕES DE LÓGICA PURA (TESTÁVEIS)
-----------------------------------------------------------------------------
"""

def get_worst_positions_to_close(robot_positions: list, num_to_close: int) -> list:
    """
    Recebe uma lista de posições e retorna as 'N' piores.
    Esta função é Pura, não depende do MT5 e é 100% testável.

    Args:
        robot_positions (list): Lista de objetos de posição (com atributo .profit)
        num_to_close (int): Quantas posições retornar.
        
    Returns:
        list: Uma lista contendo as 'N' piores posições.
    """
    if not robot_positions or num_to_close <= 0:
        return []
        
    # Ordena as posições pelo lucro (da pior para a melhor)
    sorted_positions = sorted(robot_positions, key=lambda p: p.profit)
    
    # Retorna as 'N' piores
    return sorted_positions[:num_to_close]

def check_drawdown_trigger(total_profit: float, dd_threshold: float) -> bool:
    """
    Verifica se o trigger de drawdown foi atingido.
    Função Pura e 100% testável.

    Args:
        total_profit (float): O P/L flutuante atual.
        dd_threshold (float): O limite (negativo) para o trigger.
        
    Returns:
        bool: True se o trigger foi ativado, False caso contrário.
    """
    # Trigger é ativado se o lucro for MENOR ou IGUAL ao limite
    return total_profit <= dd_threshold


"""
-----------------------------------------------------------------------------
 FUNÇÕES DE ORQUESTRAÇÃO (LIDAM COM I/O E MT5)
-----------------------------------------------------------------------------
"""

def _validate_config(config: dict, logger: logging.Logger) -> tuple[bool, dict]:
    """
    Função auxiliar para validar e carregar os parâmetros de drawdown.
    Retorna (True, params) ou (False, None).
    """
    if not config.get("enable_floating_dd_stop", False):
        return False, None # Desabilitado, não é um erro, apenas não roda.

    dd_threshold = config.get("floating_dd_stop_threshold", 0.0)
    num_to_close = config.get("num_worst_to_close_on_dd_stop", 0)
    
    if num_to_close <= 0:
        logger.warning(
            "[DRAWDOWN] 'num_worst_to_close_on_dd_stop' é 0 ou menor. "
            "Funcionalidade desativada."
        )
        return False, None
        
    if dd_threshold >= 0:
        logger.error(
            f"[DRAWDOWN] 'floating_dd_stop_threshold' ({dd_threshold}) "
            "deve ser um valor NEGATIVO. Funcionalidade desativada."
        )
        return False, None

    params = {
        'dd_threshold': dd_threshold,
        'num_to_close': num_to_close,
        'main_magic': config.get('magic_number')
    }
    return True, params

def _execute_close_positions(positions_to_close: list, logger: logging.Logger):
    """
    Função auxiliar que executa o fechamento das posições no MT5.
    Isola a lógica de I/O (escrita).
    """
    logger.info(
        f"[DRAWDOWN] Tentando fechar as {len(positions_to_close)} "
        "piores posições:"
    )
    closed_count = 0
    
    for trade in positions_to_close:
        trade_type = "BUY" if trade.type == mt5.ORDER_TYPE_BUY else "SELL"
        logger.info(
            f"[DRAWDOWN]  -> Fechando Ticket {trade.ticket} "
            f"({trade_type} {trade.volume} @ {trade.price_open}, "
            f"Lucro: {trade.profit:.2f})"
        )
        
        # A dependência de I/O está isolada aqui
        if close_position(trade, logger):
            closed_count += 1
        else:
            logger.error(
                f"[DRAWDOWN] Falha ao enviar ordem de fechamento para o "
                f"ticket {trade.ticket}. Tentará novamente no próximo ciclo."
            )
            
    logger.info(
        f"[DRAWDOWN] {closed_count} de {len(positions_to_close)} "
        "posições fechadas com sucesso."
    )

def check_and_manage_floating_drawdown(config: dict, logger: logging.Logger, symbol: str):
    """
    Função principal (Orquestradora) para gerenciar o Drawdown Flutuante.
    Esta função agora coordena as funções puras e as funções de I/O.
    """
    
    # 1. Validar Config
    is_enabled, params = _validate_config(config, logger)
    if not is_enabled:
        return # Desabilitado ou configuração inválida

    # 2. Obter Posições (I/O - Leitura)
    try:
        all_positions = get_all_open_positions(symbol)
        if all_positions is None:
            logger.error("[DRAWDOWN] Não foi possível obter posições do MT5.")
            return

        # Filtra posições (Lógica)
        robot_positions = [
            p for p in all_positions if p.magic == params['main_magic']
        ]

        if not robot_positions:
            # logger.info("[DRAWDOWN] Nenhuma posição aberta para verificar.")
            return
            
    except Exception as e:
        logger.error(f"[DRAWDOWN] Erro ao carregar posições: {e}", exc_info=True)
        return

    # 3. Checar Trigger (Lógica Pura)
    total_floating_profit = sum(p.profit for p in robot_positions)
    
    # logger.info(f"[DRAWDOWN] P/L Flutuante: {total_floating_profit:.2f} (Limite: {params['dd_threshold']:.2f})")

    # Chamamos a função de lógica pura
    if not check_drawdown_trigger(total_floating_profit, params['dd_threshold']):
        return # Trigger não ativado, tudo OK.

    # --- TRIGGER ATIVADO ---
    logger.warning(
        f"[DRAWDOWN] TRIGGER ATIVADO! "
        f"Lucro Flutuante: {total_floating_profit:.2f} "
        f"(Limite: {params['dd_threshold']:.2f})"
    )

    # 4. Identificar Posições (Lógica Pura)
    # Chamamos a outra função de lógica pura
    positions_to_close = get_worst_positions_to_close(
        robot_positions, 
        params['num_to_close']
    )

    if not positions_to_close:
        # Isso não deve acontecer se robot_positions não estiver vazio,
        # mas é uma boa verificação.
        return

    # 5. Executar Fechamento (I/O - Escrita)
    _execute_close_positions(positions_to_close, logger)