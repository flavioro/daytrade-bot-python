import math
import numpy as np
import random
import MetaTrader5 as mt5
from .mt5_order import place_order

# Variável global para controle de IDs (se necessário)
trade_id_counter = 0

def new_sell_trades(analise, config, logger, symbol):
    """
    Cria múltiplas SELLs de acordo com a estratégia dinâmica e executa no MT5.
    Retorna a lista de trades criadas.
    """
    global trade_id_counter
    
    mf = analise['margin_free_perc']
    buys = analise['buy_positions']
    sells = analise['sell_positions']
    total_buy_volume = analise['total_buy_volume']
    total_sell_volume = analise['total_sell_volume']

    logger.info(f"Analisando novas SELLs - MF: {mf:.2f}%, Buys: {buys}, Sells: {sells}")

    mf_config = get_dynamic_parameters(mf, config, logger)
    if not mf_config:
        # logger.info("Condições NÃO atendidas para abertura de novas SELLs")
        return []
    
    if total_sell_volume >= total_buy_volume:
        logger.info(f"Balanceamento não favorável - Volume Sells ({total_sell_volume}) >= Buys({total_buy_volume})")
        return []

    if buys <= sells:
        logger.info(f"Balanceamento não favorável - Buys({buys}) <= Sells({sells})")
        return []
    
    # Quantas ordens abrir
    round_mode = config["dynamic_mf_strategy"].get("round_orders", "ceil")
    total_orders = calculate_total_orders(buys, sells, mf_config["order_perc"], round_mode, logger)
    
    if total_orders <= 0:
        logger.info("Nenhuma ordem a ser aberta após cálculo")
        return []
    
    logger.info(f"Total de ordens SELL a abrir: {total_orders}")

    # Distribui TP/SL
    tp_sl_list = distribute_tp_sl(
        total_orders,
        mf_config["min_tp"],
        mf_config["max_tp"],
        mf_config["min_sl"],
        mf_config["max_sl"],
        mode=config["dynamic_mf_strategy"].get("tp_distribution", "linear"),
        logger=logger
    )
    
    # Cria e executa ordens no MT5
    new_trades = []
    successful_orders = 0
    
    for i, (tp, sl) in enumerate(tp_sl_list):
        trade_id_counter += 1
        
        logger.info(f"Abrindo SELL {i+1}/{total_orders} - TP: {tp}, SL: {sl}, Volume: {mf_config['volume']}")
        
        # Executa a ordem no MT5
        result = place_order(
            symbol=symbol,
            order_type=mt5.ORDER_TYPE_SELL,
            volume=mf_config["volume"],
            magic_number=config["magic_number"],
            stop_points=sl,  # Usando SL calculado
            profit_points=tp,  # Usando TP calculado
            logger=logger
        )
        
        if result:
            logger.info(f"SELL {i+1} executada com sucesso - ID: {trade_id_counter}")
        else:
            logger.error(f"Falha ao executar SELL {i+1}")
    
    logger.info(f"Operação concluída - {successful_orders}/{total_orders} SELLs executadas com sucesso")
    return new_trades

def new_buy_trades(analise, config, logger, symbol):
    """
    Cria múltiplas BUYs de acordo com a estratégia dinâmica e executa no MT5.
    Retorna a lista de trades criadas.
    """
    global trade_id_counter
    
    mf = analise['margin_free_perc']
    buys = analise['buy_positions']
    sells = analise['sell_positions']
    total_buy_volume = analise['total_buy_volume']
    total_sell_volume = analise['total_sell_volume']

    logger.info(f"Analisando novas BUYs - MF: {mf:.2f}%, Buys: {buys}, Sells: {sells}")

    mf_config = get_dynamic_parameters(mf, config, logger)
    if not mf_config:
        # logger.info("Condições NÃO atendidas para abertura de novas BUYs")
        return []
    
    # --- LÓGICA INVERTIDA ---
    # Só abre BUY se o volume de compra for MENOR OU IGUAL que o de venda
    if total_buy_volume > total_sell_volume:
        logger.info(f"Balanceamento não favorável - Volume Buys ({total_buy_volume}) >= Sells({total_sell_volume})")
        return []

    # --- LÓGICA INVERTIDA ---
    # Só abre BUY se o número de posições de compra for MENOR que o de venda
    if buys > sells:
        logger.info(f"Balanceamento não favorável - Buys({buys}) > Sells({sells})")
        return []
    
    # --- LÓGICA INVERTIDA ---
    # Quantas ordens abrir, baseado na diferença de SELLS para BUYS
    round_mode = config["dynamic_mf_strategy"].get("round_orders", "ceil")
    total_orders = calculate_total_orders(sells, buys, mf_config["order_perc"], round_mode, logger)
    
    if total_orders <= 0:
        logger.info("Nenhuma ordem a ser aberta após cálculo")
        return []
    
    logger.info(f"Total de ordens BUY a abrir: {total_orders}")

    # Distribui TP/SL (esta lógica permanece a mesma)
    tp_sl_list = distribute_tp_sl(
        total_orders,
        mf_config["min_tp"],
        mf_config["max_tp"],
        mf_config["min_sl"],
        mf_config["max_sl"],
        mode=config["dynamic_mf_strategy"].get("tp_distribution", "linear"),
        logger=logger
    )
    
    # Cria e executa ordens no MT5
    new_trades = []
    successful_orders = 0
    
    for i, (tp, sl) in enumerate(tp_sl_list):
        trade_id_counter += 1
        
        logger.info(f"Abrindo BUY {i+1}/{total_orders} - TP: {tp}, SL: {sl}, Volume: {mf_config['volume']}")
        
        # --- LÓGICA INVERTIDA ---
        # Executa a ordem de COMPRA (BUY) no MT5
        result = place_order(
            symbol=symbol,
            order_type=mt5.ORDER_TYPE_BUY, # Alterado para BUY
            volume=mf_config["volume"],
            magic_number=config["magic_number"],
            stop_points=sl,
            profit_points=tp,
            logger=logger
        )
        
        if result:
            successful_orders += 1 # CORREÇÃO: Incrementando ordens bem-sucedidas
            new_trades.append(result) # SUGESTÃO: Adicionando o trade à lista de retorno
            logger.info(f"BUY {i+1} executada com sucesso - ID: {trade_id_counter}")
        else:
            logger.error(f"Falha ao executar BUY {i+1}")
    
    logger.info(f"Operação concluída - {successful_orders}/{total_orders} BUYs executadas com sucesso")
    return new_trades

def get_dynamic_parameters(mf_percentage, config, logger=None):
    """
    Retorna os parâmetros dinâmicos baseados no nível de Margin Free.
    """
    if not config.get("dynamic_mf_strategy", {}).get("enabled", False):
        if logger:
            logger.debug("Estratégia dinâmica MF desabilitada")
        return None
    
    strategy_levels = config["dynamic_mf_strategy"]["levels"]
    
    for level in strategy_levels:
        if mf_percentage <= level["max_mf"]:
            if logger:
                logger.debug(f"MF {mf_percentage:.2f}% → Nível encontrado: MF máximo {level['max_mf']}%")
            return level
    
    if logger:
        logger.debug(f"MF {mf_percentage:.2f}% → Nenhum nível adequado encontrado")
    return None

def calculate_total_orders(buys, sells, order_perc, round_mode="ceil", logger=None):
    """
    Calcula quantas novas ordens SELL abrir.
    """
    diff = max(buys - sells, 0)
    raw_value = diff * order_perc

    if round_mode == "ceil":
        result = math.ceil(raw_value)
    elif round_mode == "floor":
        result = math.floor(raw_value)
    else:
        result = round(raw_value)
    
    if logger:
        logger.debug(f"Cálculo de ordens - Diff: {diff}, Perc: {order_perc}, Raw: {raw_value}, Result: {result}")
    
    return result

def distribute_tp_sl(total_orders, min_tp, max_tp, min_sl, max_sl, mode="linear", logger=None):
    """
    Distribui TP/SL entre as ordens.
    """
    if total_orders <= 0:
        return []
    
    if mode == "linear":
        tp_values = np.linspace(min_tp, max_tp, total_orders)
        sl_values = np.linspace(min_sl, max_sl, total_orders)
    elif mode == "random":
        tp_values = [random.uniform(min_tp, max_tp) for _ in range(total_orders)]
        sl_values = [random.uniform(min_sl, max_sl) for _ in range(total_orders)]
    else:
        tp_values = [min_tp] * total_orders
        sl_values = [min_sl] * total_orders
    
    result = list(zip(tp_values, sl_values))
    
    if logger:
        logger.debug(f"Distribuição TP/SL - Modo: {mode}, TP: {min_tp}-{max_tp}, SL: {min_sl}-{max_sl}")
        for i, (tp, sl) in enumerate(result):
            logger.debug(f"Ordem {i+1}: TP={tp:.2f}, SL={sl:.2f}")
    
    return result

# import math
# import numpy as np
# import random
# import MetaTrader5 as mt5
# from mt5_order import place_order

# def create_sell_trade(trade_id, entry_time, entry_price, config, tp, sl, volume):
#     """
#     Cria uma trade de VENDA (SELL).
#     """
#     return {
#         'id': trade_id,
#         'type': 'SELL',
#         'status': 'open',
#         'volume': volume,
#         'entry_time': entry_time,
#         'entry_price': entry_price,
#         'sl_level': entry_price + (sl * config['point']),
#         'tp_level': entry_price - (tp * config['point']),
#         'is_hedge_trigger': False,
#         'hedge_pair_id': None
#     }


# def new_sell_trades(analise, config, logger):
#     """
#     Cria múltiplas SELLs de acordo com a estratégia dinâmica.
#     """
#     mf = analise['mf%']
#     buys = analise['buy_positions']
#     sells = analise['sell_positions']

#     mf_config = get_dynamic_parameters(mf, config)
#     if not mf_config or buys <= sells:
#         return []
    
#     # Quantas ordens abrir
#     round_mode = config["dynamic_mf_strategy"].get("round_orders", "ceil")
#     total_orders = calculate_total_orders(buys, sells, mf_config["order_perc"], round_mode)
    
#     # Distribui TP/SL
#     tp_sl_list = distribute_tp_sl(
#         total_orders,
#         mf_config["min_tp"],
#         mf_config["max_tp"],
#         mf_config["min_sl"],
#         mf_config["max_sl"],
#         mode=config["dynamic_mf_strategy"].get("tp_distribution", "linear")
#     )
    
#     # Cria ordens
#     for tp, sl in tp_sl_list:
#         logger.info("Condição atendida → Abrindo nova SELL")
#         result = place_order(
#             symbol=config.get("symbol", "XAUUSD"),
#             order_type=mt5.ORDER_TYPE_SELL,
#             volume=config["volume"],
#             magic_number=config["magic_number"],
#             stop_points=config["stop_points"],
#             profit_points=config["profit_points"],
#             logger=logger
#         )
    

# def get_dynamic_parameters(mf_percentage, config):
#     """
#     Retorna os parâmetros dinâmicos baseados no nível de Margin Free.
#     """
#     if not config.get("dynamic_mf_strategy", {}).get("enabled", False):
#         return None
    
#     strategy_levels = config["dynamic_mf_strategy"]["levels"]
    
#     for level in strategy_levels:
#         if mf_percentage <= level["max_mf"]:
#             return level
    
#     return None


# def calculate_total_orders(buys, sells, order_perc, round_mode="ceil"):
#     """
#     Calcula quantas novas ordens SELL abrir.
#     """
#     diff = max(buys - sells, 0)
#     raw_value = diff * order_perc

#     if round_mode == "ceil":
#         return math.ceil(raw_value)
#     elif round_mode == "floor":
#         return math.floor(raw_value)
#     else:
#         return round(raw_value)


# def distribute_tp_sl(total_orders, min_tp, max_tp, min_sl, max_sl, mode="linear"):
#     """
#     Distribui TP/SL entre as ordens.
#     """
#     if total_orders <= 0:
#         return []
    
#     if mode == "linear":
#         tp_values = np.linspace(min_tp, max_tp, total_orders)
#         sl_values = np.linspace(min_sl, max_sl, total_orders)
#     elif mode == "random":
#         tp_values = [random.uniform(min_tp, max_tp) for _ in range(total_orders)]
#         sl_values = [random.uniform(min_sl, max_sl) for _ in range(total_orders)]
#     else:
#         tp_values = [min_tp] * total_orders
#         sl_values = [min_sl] * total_orders
    
#     return list(zip(tp_values, sl_values))