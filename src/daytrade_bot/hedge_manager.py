# hedge_manager.py
import MetaTrader5 as mt5
import json
import os
from datetime import datetime, timezone, timedelta

# Importar as funções do seu projeto
from .mt5_order import open_order_hedge, close_position, get_all_open_positions

def load_hedge_state(config, logger):
    """Carrega o estado do gerenciador de hedge de um arquivo JSON."""
    
    # Usamos um arquivo de estado separado para BUY e SELL
    state_file = config.get("hedge_state_file", "hedge_state.json")
    
    try:
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
                # Converte a string de tempo do JSON de volta para um objeto datetime
                if 'hedge_manager_cooldown_until' in state and state['hedge_manager_cooldown_until']:
                    state['hedge_manager_cooldown_until'] = datetime.fromisoformat(state['hedge_manager_cooldown_until'])
                
                logger.info(f"Estado do hedge carregado de {state_file}.")
                return state
    except Exception as e:
        logger.warning(f"Não foi possível carregar o estado do hedge ({state_file}): {e}. Usando estado padrão.")
    
    # Estado padrão se o arquivo não existir ou falhar
    return {
        'hedge_manager_active': False,
        'active_hedge_trade_id': None,
        'hedge_manager_cooldown_until': None,
        'active_hedge_profit_max': 0.0,
        'active_hedge_profit_min': 0.0,
        'hedge_log': [] 
    }

def save_hedge_state(state, config, logger):
    """Salva o estado atual do gerenciador de hedge em um arquivo JSON."""
    
    state_file = config.get("hedge_state_file", "hedge_state.json")
    
    try:
        # Cria uma cópia para salvar, convertendo datetime para string
        state_to_save = state.copy()
        if 'hedge_manager_cooldown_until' in state_to_save and state_to_save['hedge_manager_cooldown_until']:
            state_to_save['hedge_manager_cooldown_until'] = state_to_save['hedge_manager_cooldown_until'].isoformat()
        
        with open(state_file, 'w') as f:
            json.dump(state_to_save, f, indent=4)
            
    except Exception as e:
        logger.error(f"Falha crítica ao salvar o estado do hedge em {state_file}: {e}")

def calculate_buy_metrics(buy_positions):
    """
    Calcula o lucro flutuante total e a contagem de posições BUY.
    Substitui o 'initial_metrics' do backtest.
    """
    if not buy_positions:
        return {'profit_buy': 0.0, 'open_buy': 0}
    
    total_profit = sum(p.profit for p in buy_positions)
    count = len(buy_positions)
    return {'profit_buy': total_profit, 'open_buy': count}

def manage_active_hedge(state, hedge_trade, current_bid, current_time, config, logger):
    """
    Gerencia um trade de hedge (SELL) que já está ativo.
    Verifica a regra de saída por drawdown de lucro.
    """
    
    hedge_drawdown_cash = config.get('hedge_close_drawdown_cash', 10.0)
    hedge_cooldown_min = config.get('hedge_cooldown_minutes', 600)

    # O objeto 'hedge_trade' é uma Posição MT5.
    # O campo 'profit' já é o lucro flutuante atualizado.
    current_profit = hedge_trade.profit 
    
    # Atualizar profit_max e profit_min no estado
    state['active_hedge_profit_max'] = max(
        state.get('active_hedge_profit_max', 0.0), 
        current_profit
    )
    state['active_hedge_profit_min'] = min(
        state.get('active_hedge_profit_min', 0.0), 
        current_profit
    )
    
    # Log (opcional, mas mantido do backtest)
    trade_open_time = datetime.fromtimestamp(hedge_trade.time, tz=timezone.utc)
    duration_min = (current_time - trade_open_time).total_seconds() / 60
    
    # (Opcional) Adicionar ao log - CUIDADO: isso pode fazer o JSON crescer muito.
    # state['hedge_log'].append({ ... }) 

    # --- VERIFICAR REGRA DE SAÍDA (DRAWDOWN DE LUCRO) ---
    if current_profit > 0:
        profit_drawdown = state['active_hedge_profit_max'] - current_profit
        
        if profit_drawdown >= hedge_drawdown_cash:
            logger.info(
                f"[HEDGE] Drawdown de lucro atingido ({profit_drawdown:.2f} >= {hedge_drawdown_cash}). "
                f"Fechando hedge Ticket {hedge_trade.ticket} com lucro {current_profit:.2f}."
            )
            
            # Usar a sua função de fechamento
            if close_position(hedge_trade, logger):
                # Sucesso ao fechar: resetar estado e aplicar cooldown
                state['hedge_manager_active'] = False
                state['active_hedge_trade_id'] = None
                state['hedge_manager_cooldown_until'] = current_time + timedelta(minutes=hedge_cooldown_min)
                logger.info(f"[HEDGE] Cooldown de {hedge_cooldown_min} min ativado. Próxima verificação após {state['hedge_manager_cooldown_until']}.")
            else:
                logger.error(f"[HEDGE] Falha ao enviar ordem de fechamento para o ticket {hedge_trade.ticket}. Tentará novamente no próximo ciclo.")
    
    return state # Retorna o estado modificado

def check_hedge_trigger(state, buy_metrics, all_positions, current_bid, current_time, config, logger, symbol):
    """
    Verifica se um novo trade de hedge (SELL) deve ser aberto.
    """
    
    # --- 1. Checar se estamos em Cooldown ---
    cooldown_time = state.get('hedge_manager_cooldown_until')
    if cooldown_time and current_time < cooldown_time:
        # logger.info(f"[HEDGE] Em cooldown. Nenhuma ação até {cooldown_time}") # Log muito verboso
        return state # Ainda em cooldown. Não faz nada.
    elif cooldown_time:
        logger.info("[HEDGE] Período de cooldown terminado.")
        state['hedge_manager_cooldown_until'] = None # Cooldown acabou, limpar

    # --- 2. Puxar dados do config ---
    hedge_trigger_profit = config.get('hedge_trigger_profit_buy', -80.0)
    hedge_volume = config.get('hedge_sell_volume', 0.01)
    hedge_sl_pts = config.get('hedge_sell_sl_pts', 1400)
    hedge_max_buys = config.get('hedge_trigger_max_open_buys', 2)
    
    # Magic number do robô principal (para contar os BUYs)
    main_magic = config['magic_number']
    # Magic number específico para os trades de hedge (deve ser DIFERENTE)
    hedge_magic = config.get('hedge_magic_number', main_magic + 1) # Padrão: magic + 1
    
    if main_magic == hedge_magic:
        logger.error("[HEDGE] 'magic_number' e 'hedge_magic_number' NÃO PODEM ser iguais. Desativando hedge.")
        return state

    # --- 3. Checar o Trigger de Entrada ---
    current_profit_buy = buy_metrics['profit_buy']
    current_open_buys = buy_metrics['open_buy']

    bool_profit_trigger_met = (current_profit_buy < hedge_trigger_profit)
    bool_buy_count_limit_met = (current_open_buys <= hedge_max_buys)

    if bool_profit_trigger_met and bool_buy_count_limit_met:
        logger.warning(
            f"[HEDGE] TRIGGER ATIVADO! "
            f"Lucro BUY: {current_profit_buy:.2f} (Limite: {hedge_trigger_profit}) | "
            f"Posições BUY: {current_open_buys} (Limite: {hedge_max_buys})."
        )
        logger.info(f"[HEDGE] Tentando abrir ordem SELL [HEDGE] de {hedge_volume} lotes com SL de {hedge_sl_pts} pts.")

        # Prepara uma 'config' temporária para a ordem de hedge
        hedge_config = config.copy()
        hedge_config['volume'] = hedge_volume
        hedge_config['stop_points'] = hedge_sl_pts
        hedge_config['magic_number'] = hedge_magic
        
        # O hedge do backtest não tinha Take Profit.
        # Para "sem TP", passamos um valor muito alto de 'profit_points'
        hedge_config['profit_points'] = 90000 # TP "inatingível"
        
        # Chamamos sua função 'open_new_order'
        # Ela precisa da lista de posições para a lógica de 'NO_MONEY'
        result = open_order_hedge(
            symbol=symbol,
            order_type=mt5.ORDER_TYPE_SELL,
            config=hedge_config, # Passa nossa config de hedge
            logger=logger,
            positions=all_positions, # Passa todas as posições atuais
            profit_points=hedge_config['profit_points']
        )

        # --- 4. Processar resultado da ordem ---
        
        # ASSUMINDO que sua 'open_new_order' retorna o objeto 'result' do 'place_order'
        # e que 'place_order' retorna o 'result' do 'mt5.order_send' em caso de sucesso.
        
        new_ticket = None
        if result and hasattr(result, "retcode") and result.retcode == mt5.TRADE_RETCODE_DONE:
            new_ticket = result.order
            logger.info(f"[HEDGE] Ordem de hedge [SELL] aberta com sucesso. Ticket: {new_ticket}")
            
            # ATIVAR O ESTADO
            state['hedge_manager_active'] = True
            state['active_hedge_trade_id'] = new_ticket
            state['active_hedge_profit_max'] = 0.0 # Reseta métricas
            state['active_hedge_profit_min'] = 0.0 # Reseta métricas
            state['hedge_log'] = [] # Limpa log antigo
            
        elif result and hasattr(result, "retcode"):
            logger.error(f"[HEDGE] Falha ao abrir ordem de hedge. Retcode: {result.retcode}, Comentário: {result.comment}")
        else:
            # Cobre o caso de 'NO_MONEY' (retorna int) ou 'False'
            logger.error(f"[HEDGE] Falha ao abrir ordem de hedge. Resultado: {result}")

    # else: 
    #     if bool_profit_trigger_met and not bool_buy_count_limit_met:
    #         logger.info(f"[HEDGE] Trigger de profit atingido ({current_profit_buy:.2f}), mas bloqueado pelo limite de buys ({current_open_buys} > {hedge_max_buys}).")

    return state

def check_and_manage_hedge(config, logger, symbol):
    """
    Função principal para gerenciar a lógica do Hedge Defensivo.
    Esta função deve ser chamada dentro do seu loop principal (main).
    """
    
    # 1. Verificar se o gerenciador está habilitado no config
    if not config.get('hedge_manager_enabled', False):
        return # Desabilitado, não faz nada

    # 2. Carregar dados essenciais
    try:
        state = load_hedge_state(config, logger)
        
        # Pegar TODAS as posições abertas para este símbolo
        all_positions = get_all_open_positions(symbol)
        if all_positions is None:
            logger.error("[HEDGE] Não foi possível obter posições do MT5.")
            return

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.error(f"[HEDGE] Não foi possível obter o tick para {symbol}.")
            return
        
        current_bid = tick.bid
        # Usar o tempo do servidor MT5 é mais robusto que o tempo local
        current_time = datetime.fromtimestamp(tick.time, tz=timezone.utc)

    except Exception as e:
        logger.error(f"[HEDGE] Erro ao carregar dados iniciais: {e}", exc_info=True)
        return

    # 3. Separar posições por tipo e magic number
    main_magic = config['magic_number']
    hedge_magic = config.get('hedge_magic_number', main_magic + 1)

    # Posições BUY do robô principal (que estamos monitorando)
    buy_positions = [p for p in all_positions if p.magic == main_magic and p.type == mt5.ORDER_TYPE_BUY]
    
    # O trade de hedge (SELL) ativo, se houver
    hedge_sell_position = None
    if state['hedge_manager_active']:
        ticket_id = state['active_hedge_trade_id']
        # Encontra o trade de hedge pelo TICKET salvo no estado E pelo magic de hedge
        hedge_sell_position = next((
            p for p in all_positions 
            if p.ticket == ticket_id and 
               p.magic == hedge_magic and 
               p.type == mt5.ORDER_TYPE_SELL
        ), None)

    # 4. Executar a lógica de estado
    if state['hedge_manager_active']:
        if hedge_sell_position:
            # --- ESTADO ATIVO: O trade ainda está ativo ---
            # logger.info(f"[HEDGE] Gerenciador ATIVO. Monitorando Ticket {hedge_sell_position.ticket}...")
            state = manage_active_hedge(state, hedge_sell_position, current_bid, current_time, config, logger)
        else:
            # --- ESTADO ATIVO (Mas trade sumiu): Bateu SL ou foi fechado manualmente ---
            logger.warning(
                f"[HEDGE] Gerenciador estava ATIVO para o Ticket {state['active_hedge_trade_id']}, "
                f"mas a posição não foi encontrada. (Provavelmente SL ou fechamento manual)."
            )
            state['hedge_manager_active'] = False
            state['active_hedge_trade_id'] = None
            hedge_cooldown_min = config.get('hedge_cooldown_minutes', 600)
            state['hedge_manager_cooldown_until'] = current_time + timedelta(minutes=hedge_cooldown_min)
            logger.info(f"[HEDGE] Cooldown de {hedge_cooldown_min} min ativado até {state['hedge_manager_cooldown_until']}.")
    
    else:
        # --- ESTADO INATIVO: Monitorando o trigger para abrir um hedge ---
        # logger.info("[HEDGE] Gerenciador INATIVO. Monitorando trigger...")
        buy_metrics = calculate_buy_metrics(buy_positions)
        state = check_hedge_trigger(state, buy_metrics, all_positions, current_bid, current_time, config, logger, symbol)

    # 5. Salvar o estado no arquivo JSON
    save_hedge_state(state, config, logger)