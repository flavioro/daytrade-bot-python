# mt5_history.py
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

def get_profitable_closed_deals(symbol, original_order_type, config, logger):
    """
    Busca no histórico por negócios (deals) de fechamento que foram lucrativos,
    com base no tipo da ordem original (BUY ou SELL) e em um intervalo de tempo.

    Args:
        symbol (str): O símbolo do ativo (ex: 'EURUSD', 'WINQ24').
        original_order_type (str): O tipo da ordem original que foi fechada ('BUY' ou 'SELL').
        config (dict): Dicionário de configuração contendo 'history_minutes_interval'.
        logger: A instância do logger para registrar as ações.

    Returns:
        list: Uma lista de objetos Deal que correspondem aos critérios, ou uma lista vazia.
    """
    # 1. Determinar o tipo do negócio de fechamento
    # Se a ordem original era BUY, o negócio que a fecha é SELL, e vice-versa.
    if original_order_type.upper() == 'BUY':
        closing_deal_type = mt5.ORDER_TYPE_SELL
    elif original_order_type.upper() == 'SELL':
        closing_deal_type = mt5.ORDER_TYPE_BUY
    else:
        logger.error(f"Tipo de ordem original inválido: {original_order_type}. Use 'BUY' ou 'SELL'.")
        return []

    # 2. Calcular o intervalo de tempo usando a hora do servidor MT5
    try:
        minutes_interval = config.get('history_minutes_interval', 60) # Padrão de 60 minutos
        
        # Busca o tempo atual diretamente do servidor da corretora
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.error(f"Não foi possível obter o tick do símbolo {symbol} para pegar a hora do servidor.")
            return []
            
        # O atributo 'time' do tick é o timestamp da última cotação (UTC)
        server_time_utc = datetime.fromtimestamp(tick.time, tz=timezone.utc)
        
        end_time = server_time_utc
        start_time = end_time - timedelta(minutes=minutes_interval)
        
        logger.info(f"Buscando histórico para '{symbol}' entre {start_time.strftime('%Y-%m-%d %H:%M:%S')} e {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        logger.error(f"Erro ao calcular o intervalo de tempo: {e}")
        return []

    # 3. Buscar os negócios (deals) no histórico do MT5
    try:
        history_deals = mt5.history_deals_get(start_time, end_time, group=symbol)
        
        if history_deals is None:
            logger.error(f"Falha ao buscar o histórico de negócios. Erro: {mt5.last_error()}")
            return []
            
        if not history_deals:
            logger.info(f"Nenhum negócio encontrado para {symbol} no período especificado.")
            return []
            
    except Exception as e:
        logger.error(f"Uma exceção ocorreu ao chamar history_deals_get: {e}")
        return []

    # 4. Filtrar os negócios para encontrar os que correspondem aos critérios
    profitable_deals = []
    for deal in history_deals:
        # Critérios para ser um negócio de fechamento lucrativo:
        # - O tipo do negócio deve ser o oposto da ordem original (ex: SELL para fechar um BUY)
        # - O lucro (profit) deve ser maior que zero
        # - A entrada (entry) deve ser 'out', indicando que é um negócio de saída (fechamento)
        if (deal.type == closing_deal_type and 
            deal.profit > 0 and 
            deal.entry == mt5.DEAL_ENTRY_OUT and
            deal.symbol == symbol):
            profitable_deals.append(deal)

    logger.info(f"Encontrado(s) {len(profitable_deals)} negócio(s) de fechamento lucrativo(s) para posições de '{original_order_type}' em {symbol}.")
    
    return profitable_deals


def get_closed_orders_by_timeframe(symbol, type_order, config, logger):
    """
    Busca ordens fechadas (histórico) por símbolo, tipo e intervalo de tempo.
    
    Args:
        symbol (str): Símbolo do ativo (ex: "EURUSD")
        type_order (int): Tipo da ordem (mt5.ORDER_TYPE_BUY ou mt5.ORDER_TYPE_SELL)
        config (dict): Configurações com o parâmetro 'history_minutes_interval'
        logger: Instância do logger para registro
    
    Returns:
        list: Lista de dicionários com informações das ordens fechadas
    """
    try:
        # Calcula o intervalo de tempo
        minutes_interval = config.get('history_minutes_interval', 90)  # Default 60 minutos
        
        # Busca o tempo atual diretamente do servidor da corretora
        symbol_info = mt5.symbol_info_tick(symbol)
        if not symbol_info:
            logger.error(f"Não foi possível obter informações para o símbolo {symbol}.")
            return

        # O atributo 'time' do symbol_info é o timestamp da última cotação (UTC)
        server_time_ts = symbol_info.time
        server_time_utc = datetime.fromtimestamp(server_time_ts, tz=timezone.utc)
        
        end_time = server_time_utc
        start_time = end_time - timedelta(minutes=minutes_interval)
        
        logger.info(f"Buscando ordens fechadas - Símbolo: {symbol}, Tipo: {type_order}, "
                   f"Intervalo: {minutes_interval} minutos ({start_time} to {end_time})")
        
        # Busca ordens no histórico dentro do intervalo de tempo
        closed_orders = mt5.history_orders_get(start_time, end_time)
        
        if closed_orders is None:
            logger.warning("Nenhuma ordem no histórico encontrada ou erro na busca")
            return []
        
        # Filtra as ordens
        filtered_orders = []
        for order in closed_orders:
            if (_matches_criteria(order, symbol, type_order) and 
                _is_order_closed_profitably(order)):
                
                order_info = {
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': order.type,
                    'type_description': 'BUY' if order.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': order.volume_current or order.volume_initial,
                    'price_open': order.price_open,
                    'price_current': order.price_current,
                    'sl': order.sl,
                    'tp': order.tp,
                    'profit': order.profit,
                    'time_setup': order.time_setup,
                    'time_done': order.time_done,
                    'time_expiration': order.time_expiration,
                    'state': order.state,
                    'state_description': _get_order_state_description(order.state),
                    'magic': order.magic,
                    'comment': order.comment
                }
                filtered_orders.append(order_info)
                
                logger.debug(f"Ordem encontrada - Ticket: {order.ticket}, "
                           f"Tipo: {'BUY' if order.type == mt5.ORDER_TYPE_BUY else 'SELL'}, "
                           f"Lucro: {order.profit}, "
                           f"Fechamento: {order.time_done}")
        
        logger.info(f"Encontradas {len(filtered_orders)} ordens fechadas com lucro no intervalo")
        return filtered_orders
        
    except Exception as e:
        logger.error(f"Erro ao buscar ordens fechadas: {str(e)}")
        return []

def _matches_criteria(order, symbol, type_order):
    """Verifica se a ordem atende aos critérios de filtro."""
    return (order.symbol == symbol and 
            order.type == type_order and 
            order.state == mt5.ORDER_STATE_FILLED)

def _is_order_closed_profitably(order):
    """Verifica se a ordem foi fechada com lucro."""
    # Ordem com profit positivo indica lucro
    return order.profit > 0

def _get_order_state_description(state):
    """Retorna descrição legível do estado da ordem."""
    state_descriptions = {
        mt5.ORDER_STATE_STARTED: "Started",
        mt5.ORDER_STATE_PLACED: "Placed",
        mt5.ORDER_STATE_CANCELED: "Canceled",
        mt5.ORDER_STATE_PARTIAL: "Partial",
        mt5.ORDER_STATE_FILLED: "Filled",
        mt5.ORDER_STATE_REJECTED: "Rejected",
        mt5.ORDER_STATE_EXPIRED: "Expired",
        mt5.ORDER_STATE_REQUEST_ADD: "Request Add",
        mt5.ORDER_STATE_REQUEST_MODIFY: "Request Modify",
        mt5.ORDER_STATE_REQUEST_CANCEL: "Request Cancel"
    }
    return state_descriptions.get(state, "Unknown")

def get_closed_orders_by_magic(symbol, magic_number, config, logger):
    """
    Busca ordens fechadas filtrando por magic number.
    
    Args:
        symbol (str): Símbolo do ativo
        magic_number (int): Magic number do EA
        config (dict): Configurações
        logger: Instância do logger
    
    Returns:
        list: Lista de ordens fechadas
    """
    try:
        minutes_interval = config.get('history_minutes_interval', 60)
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes_interval)
        
        closed_orders = mt5.history_orders_get(start_time, end_time)
        
        if closed_orders is None:
            return []
        
        filtered_orders = []
        for order in closed_orders:
            if (order.symbol == symbol and 
                order.magic == magic_number and 
                order.state == mt5.ORDER_STATE_FILLED and
                order.profit > 0):
                
                order_info = {
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': order.type,
                    'type_description': 'BUY' if order.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': order.volume_current or order.volume_initial,
                    'profit': order.profit,
                    'time_done': order.time_done,
                    'magic': order.magic,
                    'comment': order.comment
                }
                filtered_orders.append(order_info)
        
        logger.info(f"Encontradas {len(filtered_orders)} ordens fechadas com magic {magic_number}")
        return filtered_orders
        
    except Exception as e:
        logger.error(f"Erro ao buscar ordens por magic: {str(e)}")
        return []

# Função auxiliar para verificar se há ordens fechadas recentemente
def has_recent_closed_orders(symbol, type_order, config, logger, min_profit=0):
    """
    Verifica se há ordens fechadas com lucro recentemente.
    
    Args:
        symbol (str): Símbolo do ativo
        type_order (int): Tipo da ordem
        config (dict): Configurações
        logger: Instância do logger
        min_profit (float): Lucro mínimo para considerar
    
    Returns:
        bool: True se há ordens fechadas com lucro, False caso contrário
    """
    orders = get_closed_orders_by_timeframe(symbol, type_order, config, logger)
    
    if not orders:
        return False
    
    # Filtra por lucro mínimo se especificado
    if min_profit > 0:
        profitable_orders = [order for order in orders if order['profit'] >= min_profit]
        return len(profitable_orders) > 0
    
    return True