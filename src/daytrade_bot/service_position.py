import MetaTrader5 as mt5
import time
# from mt5_order import close_position

def check_positions_condition(
        positions, order_type, target_up, target_down, logger, 
        ultima_verificacao_target_down, target_down_interval
    ):
    """
    Verifica condições para abrir novas posições de compra (BUY) ou venda (SELL):

    Regras:
    - Se não houver posições do tipo especificado, retorna True.
    - Obtém o menor e o maior preço de abertura das posições existentes.
    - Se o preço atual estiver dentro dessa faixa (entre min_price_open e max_price_open),
      retorna False (bloqueia novas entradas).
    - Para BUY:
        - Se price_current > max_price_open + target_up → retorna True.
        - Se price_current < min_price_open - target_down → retorna True.
    - Para SELL:
        - Se price_current < min_price_open - target_up → retorna True.
        - Se price_current > max_price_open + target_down → retorna True.
    - Caso contrário, retorna False.
    """
    filtered_positions = [p for p in positions if p.type == order_type]

    if not filtered_positions:
        return True, ultima_verificacao_target_down

    price_opens = [p.price_open for p in filtered_positions]
    price_current = filtered_positions[0].price_current

    min_price_open = min(price_opens)
    max_price_open = max(price_opens)

    logger.info(f"[CHECK RANGE {order_type}] Preço atual={price_current:.2f}, "
                f"Faixa({min_price_open:.2f} ~ {max_price_open:.2f})")

    # Bloqueia se dentro da faixa
    if min_price_open <= price_current <= max_price_open:
        logger.info(f"[COND {order_type}] Preço {price_current:.2f} dentro da faixa existente")
        return False, ultima_verificacao_target_down

    if order_type == mt5.ORDER_TYPE_BUY:
        if price_current > max_price_open + target_up:
            logger.info(f"[COND BUY] Preço {price_current:.2f} > max_open {max_price_open:.2f} + target_up {target_up}")
            return True, ultima_verificacao_target_down

        if price_current < min_price_open - target_down:
            agora = time.time()
            if agora - ultima_verificacao_target_down >= target_down_interval:
                ultima_verificacao_target_down = agora
                return True, ultima_verificacao_target_down

    elif order_type == mt5.ORDER_TYPE_SELL:
        if price_current < min_price_open - target_up:
            logger.info(f"[COND SELL] Preço {price_current:.2f} < min_open {min_price_open:.2f} - target_up {target_up}")
            return True, ultima_verificacao_target_down

        if price_current > max_price_open + target_down:
            agora = time.time()
            if agora - ultima_verificacao_target_down >= target_down_interval:
                ultima_verificacao_target_down = agora
                return True, ultima_verificacao_target_down
            
    else:
        logger.warning(f"[WARN] Tipo de ordem inválido: {order_type}")
        return False, ultima_verificacao_target_down

    return False, ultima_verificacao_target_down

# def close_positions_above_profit(positions, config, logger):
#     """
#     Fecha todas as posições cujo lucro em $ for maior ou igual ao trigger configurado.
#     Retorna True se pelo menos uma posição foi fechada.
#     """
#     trigger_profit_dollars = config.get("trigger_profit_dollars", 2.0)
#     #PRECISO CONSIDERAR O VOLUME PARA INFORMAR O LUCRO

#     closed_any = False

#     for position in positions:
#         if position.profit >= trigger_profit_dollars:
#             logger.info(
#                 f"Fechando posição {position.ticket}: "
#                 f"Lucro {position.profit:.2f}$ >= {trigger_profit_dollars:.2f}$"
#             )
#             if close_position(position, logger):
#                 closed_any = True

#     return closed_any

def adjust_volume_by_balance(config, balance, logger):
    """
    Ajusta o volume de trading baseado no saldo da conta.
    
    Args:
        config: Dicionário de configuração que será modificado
        balance: Saldo atual da conta (deve ser >= 0)
    """    
    # Validação mais completa
    if not isinstance(balance, (int, float)) or balance < 0:
        logger.error(f"Saldo inválido: {balance}")
        return

        
 # Usando next() para encontrar o primeiro threshold que atende a condição
    volume_levels = [
        (250, 0.04),
        (150, 0.03),
        (100, 0.02),
        (0, 0.01)
    ]
    
    volume = next((vol for threshold, vol in volume_levels if balance >= threshold), 0.01)
    
    config['volume'] = volume
    config["target_up_dollars"] = config['target_up_pts'] * config['point']
    config["target_down_dollars"] =  config['target_down_pts'] * config['point']
    config["trigger_profit_dollars"]  = (config['volume'] / config['point']) * (config['profit_points'] * config['point']) / 2
    
# >= 250 volume 0.04
# >= 150 and < 250 -> VOLUME 0.03
# >= 100 and < 150 -> volume 0.02
# < 100 -> volume 0.01
