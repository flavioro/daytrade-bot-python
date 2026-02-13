import MetaTrader5 as mt5
import json
import time
from datetime import datetime, timedelta
from .logger_config import setup_logger

def carregar_config(caminho_arquivo='config.json'):
    """Carrega as configurações do arquivo JSON."""
    try:
        with open(caminho_arquivo, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo de configuração '{caminho_arquivo}' não encontrado.")
        return None
    
def carregar_conta(type_order):
    """Carrega as configurações da conta de acordo com o type_order."""
    caminho_arquivo = f"account_{type_order.lower()}.json"
    try:
        with open(caminho_arquivo, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo de conta '{caminho_arquivo}' não encontrado.")
        return None    

def initialize_mt5(account, logger, mt5_path):
    """Inicializa a conexão com o MetaTrader 5 usando os dados da conta."""
    
    mt5.initialize(path=mt5_path)
    
    if not mt5.initialize(login=account["login"], password=account["password"], server=account["server"]):
        logger.error(f"Falha ao inicializar o MT5, código de erro: {mt5.last_error()}")
        return False
    logger.info(f"MetaTrader 5 inicializado com sucesso para a conta {account['login']}.")
    return True

# def initialize_mt5(logger):
#     """Inicializa a conexão com o MetaTrader 5."""
#     if not mt5.initialize():
#         logger.error(f"Falha ao inicializar o MT5, código de erro: {mt5.last_error()}")
#         return False
#     logger.info("MetaTrader 5 inicializado com sucesso.")
#     return True

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
        return result.retcode

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Falha ao enviar ordem: retcode={result.retcode}, comment={result.comment}")
        return False

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        modify_order_sl_tp(result.request.price, result.request.type, result.order, profit_points * point, stop_points * point, logger)

    logger.info(f"[ORDEM ENVIADA] Ticket: {result.order}, Preço: {result.price}, Volume: {result.volume}")
    return True

def get_open_positions(symbol, magic_number):
    """Busca posições abertas filtrando por símbolo e magic number."""
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return []
        
    # Filtra as posições pelo magic number do nosso robô
    # return [p for p in positions if p.magic == magic_number]
    return positions

def check_buy_positions_condition(positions, target_up, target_down, logger):
    """
    Verifica se:
    - A posição de BUY com maior profit é >= target_up
    - OU a posição de BUY com menor profit é <= target_down
    Retorna True se qualquer condição for atendida.
    """
    buy_positions = [p for p in positions if p.type == mt5.ORDER_TYPE_BUY]

    if not buy_positions:
        return True

    # Extrair lucros
    # profits = [p.profit for p in buy_positions]
    price_opens = [p.price_open for p in buy_positions]

    # max_profit = max(profits)
    max_price_open = max(price_opens)
    max_profit = buy_positions[0].price_current - max_price_open if max_price_open > buy_positions[0].price_current else max_price_open -buy_positions[0].price_current
    
    min_price_open = min(price_opens)
    min_profit = (buy_positions[0].price_current - min_price_open)

    logger.info(f"[CHECK PROFITS] Máx lucro={max_profit:.2f}, Mín lucro={min_profit:.2f}")

    if max_profit >= target_up:
        logger.info(f"[COND] Max profit {max_profit:.2f} >= target_up {target_up}")
        return True

    if min_profit <= -abs(target_down):  # garantir que seja prejuízo
        logger.info(f"[COND] Min profit {min_profit:.2f} <= target_down {-abs(target_down)}")
        return True

    return False

def check_positions_condition(positions, order_type, target_up, target_down, logger, target_down_interval_seconds):
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
        return True

    price_opens = [p.price_open for p in filtered_positions]
    price_current = filtered_positions[0].price_current

    min_price_open = min(price_opens)
    max_price_open = max(price_opens)

    logger.info(f"[CHECK RANGE {order_type}] Preço atual={price_current:.2f}, "
                f"Faixa({min_price_open:.2f} ~ {max_price_open:.2f})")

    # Bloqueia se dentro da faixa
    if min_price_open <= price_current <= max_price_open:
        logger.info(f"[COND {order_type}] Preço {price_current:.2f} dentro da faixa existente")
        return False

    if order_type == mt5.ORDER_TYPE_BUY:
        if price_current > max_price_open + target_up:
            logger.info(f"[COND BUY] Preço {price_current:.2f} > max_open {max_price_open:.2f} + target_up {target_up}")
            return True

        # --- CONDIÇÃO MODIFICADA AQUI ---
        if price_current < min_price_open - target_down:
            global last_buy_target_down_time
            # Calcula há quanto tempo a condição foi ativada pela última vez
            seconds_since_last_trigger = (datetime.now() - last_buy_target_down_time).total_seconds()
            
            if seconds_since_last_trigger >= target_down_interval_seconds:
                logger.info(f"[COND BUY] Preço {price_current:.2f} < min_open {min_price_open:.2f} - target_down {target_down}")
                logger.info(f"[COND BUY] Cooldown de {target_down_interval_seconds}s atendido. Permitindo nova ordem.")
                # Atualiza o tempo da última ativação para AGORA
                last_buy_target_down_time = datetime.now()
                return True
            else:
                logger.info(f"[COND BUY] Bloqueado por cooldown. Última ativação há {seconds_since_last_trigger:.1f}s.")
                return False
    elif order_type == mt5.ORDER_TYPE_SELL:
        if price_current < min_price_open - target_up:
            logger.info(f"[COND SELL] Preço {price_current:.2f} < min_open {min_price_open:.2f} - target_up {target_up}")
            return True

        # --- CONDIÇÃO MODIFICADA AQUI ---
        if price_current > max_price_open + target_down:
            # Calcula há quanto tempo a condição foi ativada pela última vez
            global last_sell_target_down_time
            seconds_since_last_trigger = (datetime.now() - last_sell_target_down_time).total_seconds()

            if seconds_since_last_trigger >= target_down_interval_seconds:
                logger.info(f"[COND SELL] Preço {price_current:.2f} > max_open {max_price_open:.2f} + target_down {target_down}")
                logger.info(f"[COND SELL] Cooldown de {target_down_interval_seconds}s atendido. Permitindo nova ordem.")
                # Atualiza o tempo da última ativação para AGORA
                last_sell_target_down_time = datetime.now()
                return True
            else:
                logger.info(f"[COND SELL] Bloqueado por cooldown. Última ativação há {seconds_since_last_trigger:.1f}s.")
                return False

    else:
        logger.warning(f"[WARN] Tipo de ordem inválido: {order_type}")
        return False

    return False

def check_and_place_hedge_sell(config, logger):
    """
    Verifica se deve abrir um SELL de hedge baseado na proporção de BUYs.
    Se abrir um SELL, ajusta o TP do último BUY e do SELL para o entry_price do BUY anterior.
    """
    if not config.get("use_hedge_strategy", False):
        return False

    positions = get_open_positions(config["symbol"], config["magic_number"])
    buy_positions = [p for p in positions if p.type == mt5.ORDER_TYPE_BUY]
    sell_positions = [p for p in positions if p.type == mt5.ORDER_TYPE_SELL]

    buys = len(buy_positions)
    sells = len(sell_positions)
    ratio = config.get("hedge_buy_to_sell_ratio", 3)

    logger.info(f"[HEDGE CHECK] BUYs={buys}, SELLs={sells}, ratio={ratio}")

    # Condição: a cada 'ratio' BUYs, deve ter 1 SELL
    if buys >= (sells + 1) * ratio and len(buy_positions) >= 2:
        logger.info("Condição atingida → Abrindo SELL de hedge")

        # Ordenar os BUYs por tempo de entrada
        buy_positions_sorted = sorted(buy_positions, key=lambda x: x.time)
        ultimo_buy = buy_positions_sorted[-1]
        buy_anterior = buy_positions_sorted[-2]

        # O novo TP deve ser o preço de entrada do BUY anterior
        novo_tp_price = buy_anterior.price_open
        digits = mt5.symbol_info(config["symbol"]).digits
        novo_tp_price = round(novo_tp_price, digits)

        # --- 1. Ajustar TP do último BUY ---
        logger.info(f"Ajustando TP do último BUY (ticket {ultimo_buy.ticket}) para {novo_tp_price}")
        modify_order_sl_tp(
            price_open=ultimo_buy.price_open,
            order_type=ultimo_buy.type,
            ticket=ultimo_buy.ticket,
            tp_absolute=novo_tp_price,
            logger=logger
        )

        # --- 2. Abrir SELL com TP pareado ---
        place_order(
            symbol=config["symbol"],
            order_type=mt5.ORDER_TYPE_SELL,
            volume=config["volume"],
            magic_number=config["magic_number"],
            stop_points=config["stop_loss_sell_pts"],  # stop de segurança
            profit_points=0,  # ignorado (vamos sobrescrever TP)
            logger=logger
        )

        # Buscar a SELL recém-aberta
        all_positions = get_open_positions(config["symbol"], config["magic_number"])
        novas_sells = [p for p in all_positions if p.type == mt5.ORDER_TYPE_SELL]

        if novas_sells:
            nova_sell = sorted(novas_sells, key=lambda x: x.time)[-1]
            logger.info(f"Ajustando TP da SELL (ticket {nova_sell.ticket}) para {novo_tp_price}")
            modify_order_sl_tp(
                price_open=nova_sell.price_open,
                order_type=nova_sell.type,
                ticket=nova_sell.ticket,
                tp_absolute=novo_tp_price,
                logger=logger
            )

        return True

    return False

def adjust_dynamic_tp(position, config, logger):
    """
    Ajusta dinamicamente o TP da posição se atingir o lucro definido.
    """
    trigger_profit_points = config.get("dynamic_tp_trigger_profit", 250)
    tp_increase = config.get("dynamic_tp_increase", 50)
    base_tp = config.get("profit_points", 300)
    point = config.get("point", 0.01)  # usar valor do config.json

    # Converter trigger de pontos para dólares ($)
    trigger_profit_dollars = trigger_profit_points * point

    if position.profit >= trigger_profit_dollars:
        expected_new_tp_points = base_tp + tp_increase
        logger.info(
            f"[Dynamic TP] Posição {position.ticket}: "
            f"Lucro {position.profit:.2f}$ >= {trigger_profit_dollars:.2f}$. "
            f"Ajustando TP para {expected_new_tp_points} pontos."
        )

        modify_order_sl_tp(
            price_open=position.price_open,
            order_type=position.type,
            ticket=position.ticket,
            tp=expected_new_tp_points * point,   # preço real
            sl=config["stop_points"] * point,    # preço real
            logger=logger
        )

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

def close_positions_above_profit(positions, config, logger):
    """
    Fecha todas as posições cujo lucro em $ for maior ou igual ao trigger configurado.
    Retorna True se pelo menos uma posição foi fechada.
    """
    trigger_profit_dollars = config.get("trigger_profit_dollars", 2.0)
    #PRECISO CONSIDERAR O VOLUME PARA INFORMAR O LUCRO

    closed_any = False

    for position in positions:
        if position.profit >= trigger_profit_dollars:
            logger.info(
                f"Fechando posição {position.ticket}: "
                f"Lucro {position.profit:.2f}$ >= {trigger_profit_dollars:.2f}$"
            )
            if close_position(position, logger):
                closed_any = True

    return closed_any

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
    # "target_up_pts": 200
    # "target_down_pts": 200,
    config["target_up_dollars"] = config['target_up_pts'] * config['point']
    # config["target_down_dollars"] =  (config['volume'] / config['point']) * (config['target_down_pts'] * config['point'])
    config["target_down_dollars"] =  config['target_down_pts'] * config['point']
    config["trigger_profit_dollars"]  = (config['volume'] / config['point']) * (config['profit_points'] * config['point']) / 2
    
# >= 250 volume 0.04
# >= 150 and < 250 -> VOLUME 0.03
# >= 100 and < 150 -> volume 0.02
# < 100 -> volume 0.01

# --- Lógica Principal da Estratégia ---
def open_order_buy_by_time(config, logger, type_order):

    sleep_time = config.get('time_seconds', 60)

    while True:
        try:
            positions = get_open_positions(config['symbol'], config['magic_number'])
            
            account = mt5.account_info()
            adjust_volume_by_balance(config, account.balance, logger)

            # --- 1. Fechar posições acima do lucro configurado ---
            closed = close_positions_above_profit(positions, config, logger)

            # --- 2. Atualizar positions apenas se algo foi fechado ---
            if closed:
                positions = get_open_positions(config['symbol'], config['magic_number'])

            # --- 3. Contagem e análise ---
            buys = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_BUY)
            sells = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_SELL)
            logger.info(f"Posições abertas: {buys} Compra(s), {sells} Venda(s).")
            
            sum_buys = sum(p.profit for p in positions if p.type == mt5.ORDER_TYPE_BUY)
            sum_sells = sum(p.profit for p in positions if p.type == mt5.ORDER_TYPE_SELL)
            logger.info(f"Compra(s) total {sum_buys}, Venda(s) total {sum_sells}")

            # --- 4. Condição para abrir nova BUY ---
            # Verificar condições para abrir nova BUY
            
            type_order_mt5 = mt5.ORDER_TYPE_BUY if type_order == 'BUY' else mt5.ORDER_TYPE_SELL
            
            if check_positions_condition(
                positions,
                type_order_mt5,
                config["target_up_dollars"],
                config["target_down_dollars"],
                logger,
                config["target_down_interval_seconds"]
            ):
                logger.info(f"Condição atendida → Abrindo nova {type_order}")
                result = place_order(
                    symbol=config["symbol"],
                    order_type=type_order_mt5,
                    volume=config["volume"],
                    magic_number=config["magic_number"],
                    stop_points=config["stop_points"],
                    profit_points=config["profit_points"],
                    logger=logger
                )
                
                if result and result == mt5.TRADE_RETCODE_NO_MONEY:
                    #Close all positions
                    close_all_positions(positions, logger)

            # # --- Ajuste Dinâmico de TP ---
            # if config.get("enable_dynamic_tp", False):
            #     for p in positions:
            #         adjust_dynamic_tp(p, config, logger)

            # --- Verificação de HEDGE ---
            # check_and_place_hedge_sell(config, logger)                

            time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Ocorreu um erro inesperado no loop principal: {e}")
            time.sleep(60)


# Inicializamos com um tempo muito antigo para garantir que a primeira verificação sempre passe
last_buy_target_down_time = datetime.min
last_sell_target_down_time = datetime.min

# --- Ponto de Entrada ---
def main(type_order, mt5_path):
    """Função de inicialização do robô."""
    
    config = carregar_config()
    account = carregar_conta(type_order)
    
    if not config:
        return

    logger = setup_logger(f"open_order_{type_order}_by_time", config['symbol'])
    
    if not initialize_mt5(account, logger, mt5_path):
        return

    try:
        open_order_buy_by_time(config, logger, type_order)
    except KeyboardInterrupt:
        logger.info("Desligamento solicitado pelo usuário.")
    finally:
        mt5.shutdown()
        logger.info("Conexão com MetaTrader 5 encerrada.")

if __name__ == "__main__":
    main()