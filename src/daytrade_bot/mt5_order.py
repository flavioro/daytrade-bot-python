import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone, timedelta
from .config_loader import load_json_config

def carregar_conta(type_order, type_account=None):
    """
    Carrega conta a partir da pasta /config.
    Procura primeiro .local.json e senão existir usa .sample.json.
    Ex: config/account_demo_buy.local.json
    """
    base = f"account_{type_account}_{type_order.lower()}" if type_account else f"account_{type_order.lower()}"
    return load_json_config(base)


def initialize_mt5(account, logger, mt5_path):
    """Inicializa a conexão com o MetaTrader 5 usando os dados da conta."""
    
    mt5.initialize(path=mt5_path)
    
    if not mt5.initialize(login=account["login"], password=account["password"], server=account["server"]):
        logger.error(f"Falha ao inicializar o MT5, código de erro: {mt5.last_error()}")
        return False
    logger.info(f"MetaTrader 5 inicializado com sucesso para a conta {account['login']}.")
    return True
    
def get_open_positions_by_type(symbol, magic_number, type_order):
    """Busca posições abertas filtrando por símbolo e magic number."""
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return []
        
    # Filtra as posições pelo magic number do nosso robô
    return [p for p in positions if p.magic == magic_number and p.type == type_order]

def get_all_open_positions(symbol):
    """Busca posições abertas filtrando por símbolo e magic number."""
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return []
        
    return positions

def close_position(position, logger):
    """
    Fecha uma posição de mercado específica com base no objeto da posição.

    Args:
        position: O objeto da posição retornado por mt5.positions_get().
        logger: A instância do logger para registrar as ações.

    Returns:
        True se a ordem de fechamento foi enviada com sucesso, False caso contrário.
    """
    symbol = position.symbol
    ticket = position.ticket
    volume = position.volume
    order_type = position.type
    magic = position.magic

    # Para fechar uma posição de COMPRA (BUY), você precisa VENDER (SELL)
    # Para fechar uma posição de VENDA (SELL), você precisa COMPRAR (BUY)
    if order_type == mt5.ORDER_TYPE_BUY:
        close_action = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid  # Preço de venda (BID) para fechar compra
    elif order_type == mt5.ORDER_TYPE_SELL:
        close_action = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask   # Preço de compra (ASK) para fechar venda
    else:
        logger.error(f"TICKET {ticket}: Tipo de ordem desconhecido ({order_type}) para fechamento.")
        return False

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": symbol,
        "volume": volume,
        "type": close_action,
        "price": price,
        "deviation": 20,
        "magic": magic,
        "comment": "Close on Low Margin",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(
            f"FALHA AO FECHAR TICKET {ticket}. Motivo: {result.comment} (retcode: {result.retcode})"
        )
        return False

    logger.info(
        f"ORDEM DE FECHAMENTO ENVIADA para o Ticket {ticket}. "
        f"Volume: {result.volume}, Preço: {result.price}"
    )
    return True

def close_all_positions(positions, logger):
    """
    Fecha todas as posições.
    """

    for position in positions:
        logger.info(
            f"Fechando posição {position.ticket}: "
            f"Lucro/prejuizo {position.profit:.2f}$"
        )
        
        close_position(position, logger)

def handle_low_margin(margin_free_perc, open_positions, config, logger):
    """
    Verifica o percentual de margem livre. Se estiver abaixo do limite,
    fecha a posição com o menor lucro para liberar margem.
    """
    mf_perc_threshold = config.get("margin_free_perc", 0.5)

    logger.info("Verificando nivel de margem livre.")

    # A condição para agir: a margem está positiva mas abaixo do nosso limite de segurança
    if 0 < margin_free_perc < mf_perc_threshold:
        logger.warning(
            f"ALERTA DE MARGEM! Nível atual ({margin_free_perc:.2%}) "
            f"é menor que o limite ({mf_perc_threshold:.2%})."
        )

        if not open_positions:
            logger.error("Alerta de margem, mas nenhuma posição aberta encontrada para fechar.")
            return
        elif len(open_positions) == 1:
            logger.warning(
                f"ALERTA DE POSIÇÃO! Apenas uma posição aberta, ticket: ({open_positions[0].ticket}) "
            )
            return

        # Encontra a posição com o menor lucro (pode ser o maior prejuízo)
        position_to_close = min(open_positions, key=lambda p: p.profit)
        
        profit_value = position_to_close.profit
        ticket_to_close = position_to_close.ticket

        logger.info(
            f"Tentando fechar a posição de pior desempenho para liberar margem: "
            f"Ticket #{ticket_to_close} com lucro de {profit_value:.2f}."
        )

        # Chama a função para fechar a posição encontrada
        close_position(position_to_close, logger)


def modify_order_sl_tp(price_open, order_type, ticket, tp, sl, logger):
    """
    Modifica uma ordem existente para adicionar ou alterar o Take Profit e o Stop Loss.
    """
    
    # 3. Calcular os preços absolutos de SL e TP
    if order_type == mt5.ORDER_TYPE_BUY:
        # Para uma ordem de COMPRA, o TP está acima e o SL está abaixo
        tp_price = price_open + tp
        sl_price = price_open - sl
    elif order_type == mt5.ORDER_TYPE_SELL:
        # Para uma ordem de VENDA, o TP está abaixo e o SL está acima
        tp_price = price_open - tp
        sl_price = price_open + sl
    else:
        logger.error(f"Tipo de ordem desconhecido: {order_type}")
        return None
    
    # Arredondar os preços para o número correto de dígitos do ativo
    tp_price = round(tp_price, 2)
    sl_price = round(sl_price, 2)

    # 4. Montar a requisição de modificação
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl": sl_price,
        "tp": tp_price,
        # "magic": position.magic,
    }

    # 5. Enviar a requisição de modificação
    result = mt5.order_send(request)

    if result is None:
        logger.error(f"Falha ao modificar ordem. Erro: {mt5.last_error()}")
        return None

    return result

def validate_margin_free(margin_free_perc, order_type, config, logger):
    mf_perc_config = config.get("margin_free_perc", 0.5)
    
    if margin_free_perc > 0 and margin_free_perc < mf_perc_config:
        place_order(
            symbol=config["symbol"],
            order_type=mt5.ORDER_TYPE_SELL,
            volume=config["volume"],
            magic_number=config["magic_number"],
            stop_points=config["stop_points"],
            profit_points=config["profit_points"],
            logger=logger
        )
    
def open_order_hedge(symbol, order_type, config, logger, positions=None, profit_points=None):
    """
    Abre uma ordem usando place_order. 
    - profit_points: se None, usa config['profit_points']; caso contrário sobrescreve.
    - positions: lista de posições atual (usada se precisarmos fechar tudo em NO_MONEY).
    Retorna o result (conforme seu place_order).
    """
    profit = profit_points if profit_points is not None else config.get("profit_points")
    logger.info(f"[OPEN_ORDER] Tentando abrir ordem {order_type} para {symbol} (TP={profit}, SL={config.get('stop_points')}, vol={config.get('volume')})")

    result, detail = place_order(
        symbol=symbol,
        order_type=order_type,
        volume=config["volume"],
        magic_number=config["magic_number"],
        stop_points=config["stop_points"],
        profit_points=profit,
        logger=logger
    )

    # Compatibilidade: place_order pode retornar objeto ou retcode
    retcode = None
    if result is None:
        logger.error("[OPEN_ORDER] place_order retornou None")
    else:
        # se for dict/obj com atributo/ chave 'retcode'
        if hasattr(detail, "retcode"):
            retcode = detail.retcode
        elif isinstance(detail, dict) and "retcode" in detail:
            retcode = detail["retcode"]
        else:
            # pode já ser um retcode inteiro (como você usou antes)
            retcode = result

    if retcode == mt5.TRADE_RETCODE_NO_MONEY:
        logger.warning("[OPEN_ORDER] Sem margem (NO_MONEY) — fechando posições para liberar margem")
        if positions:
            close_all_positions(positions, logger)
        else:
            logger.warning("[OPEN_ORDER] Nenhuma positions disponível para fechar.")

    return detail

def open_new_order(symbol, order_type, config, logger, positions=None, profit_points=None):
    """
    Abre uma ordem usando place_order. 
    - profit_points: se None, usa config['profit_points']; caso contrário sobrescreve.
    - positions: lista de posições atual (usada se precisarmos fechar tudo em NO_MONEY).
    Retorna o result (conforme seu place_order).
    """
    profit = profit_points if profit_points is not None else config.get("profit_points")
    logger.info(f"[OPEN_ORDER] Tentando abrir ordem {order_type} para {symbol} (TP={profit}, SL={config.get('stop_points')}, vol={config.get('volume')})")

    result, _ = place_order(
        symbol=symbol,
        order_type=order_type,
        volume=config["volume"],
        magic_number=config["magic_number"],
        stop_points=config["stop_points"],
        profit_points=profit,
        logger=logger
    )

    # Compatibilidade: place_order pode retornar objeto ou retcode
    retcode = None
    if result is None:
        logger.error("[OPEN_ORDER] place_order retornou None")
    else:
        # se for dict/obj com atributo/ chave 'retcode'
        if hasattr(result, "retcode"):
            retcode = result.retcode
        elif isinstance(result, dict) and "retcode" in result:
            retcode = result["retcode"]
        else:
            # pode já ser um retcode inteiro (como você usou antes)
            retcode = result

    if retcode == mt5.TRADE_RETCODE_NO_MONEY:
        logger.warning("[OPEN_ORDER] Sem margem (NO_MONEY) — fechando posições para liberar margem")
        if positions:
            close_all_positions(positions, logger)
        else:
            logger.warning("[OPEN_ORDER] Nenhuma positions disponível para fechar.")

    return result
    
def place_order(symbol, order_type, volume, magic_number, stop_points, profit_points, logger):
    """Coloca uma ordem direcional com TP/SL."""
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"Símbolo {symbol} não encontrado")
        return False
    
    if not symbol_info.visible:
        logger.info(f"Símbolo {symbol} não está visível, tentando ativar")
        if not mt5.symbol_select(symbol, True):
            logger.error(f"Falha ao ativar {symbol}")
            return False

    # Dentro da sua função, após obter symbol_info
    if symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
        logger.error(f"A negociação para o símbolo {symbol} está desabilitada (trade_mode).")
        return False

    logger.info(f"Símbolo {symbol} esta como trade_mode {symbol_info.trade_mode}")    
            
    point = symbol_info.point
    price = 0
    
    if order_type == mt5.ORDER_TYPE_BUY:
        price = mt5.symbol_info_tick(symbol).ask
        sl = price - stop_points * point
        tp = price + profit_points * point
    elif order_type == mt5.ORDER_TYPE_SELL:
        price = mt5.symbol_info_tick(symbol).bid
        sl = price + stop_points * point
        tp = price - profit_points * point
    else:
        logger.error("Tipo de ordem inválido.")
        return False
    
    comment = f"{round(profit_points * point, 1)}x{round(stop_points * point, 1)}"

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": magic_number,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_NO_MONEY:
        logger.error(f"Falha ao enviar ordem: retcode={result.retcode}, comment={result.comment}")
        return result.retcode, result 
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Falha ao enviar ordem: retcode={result.retcode}, comment={result.comment}")
        return False, result

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        modify_order_sl_tp(result.request.price, result.request.type, result.order, profit_points * point, stop_points * point, logger)

    logger.info(f"[ORDEM ENVIADA] Ticket: {result.order}, Preço: {result.price}, Volume: {result.volume}")
    return True, result

def get_historical_data(symbol, timeframe, start_time, end_time, logger):
    """Obtém dados históricos dentro do período especificado"""
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    
    rates = mt5.copy_rates_range(symbol, timeframe, int(start_time.timestamp()), int(end_time.timestamp()))
    if rates is None or len(rates) == 0:
        logger.error(f"Não foi possível obter dados históricos para {symbol}")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize('UTC')
    return df

def get_historical_by_hours(config, logger, timeframe:None):
    server_time = datetime.fromtimestamp(mt5.symbol_info(config['symbol']).time, timezone.utc)
    end_time = server_time
    start_time = end_time - timedelta(hours=config['backtest_hours'])
    
    if timeframe is None:
        timeframe = config['timeframe']
    else:
        timeframe = config[timeframe]

    df = get_historical_data(config['symbol'], timeframe, start_time, end_time, logger)
    
    if df is None or df.empty:
        logger.error("Erro ao carregar os dados históricos ou DataFrame vazio.")
        return

    return df