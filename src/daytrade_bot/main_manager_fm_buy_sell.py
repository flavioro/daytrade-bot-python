import MetaTrader5 as mt5
import time
import datetime
import logging
from .config_loader import load_json_config
from .logger_config import setup_logger
from .manager_margin import manager_positions
from .excel_writer import salvar_em_excel, gerar_nome_excel
from .mt5_order import handle_low_margin, carregar_conta, initialize_mt5, get_open_positions_by_type
from .mt5_order import open_new_order, get_historical_by_hours
from .service_position import check_positions_condition
from .service_add_sells import new_sell_trades
from .pandas_aux import add_indicators
from .account_alert_manager import check_equity_and_alert

def carregar_config(base_name: str):
    """
    Carrega configurações a partir da pasta /config usando o loader.
    Procura primeiro:
      config/<base_name>.local.json
    e se não existir, usa:
      config/<base_name>.sample.json
    """
    return load_json_config(base_name)


def load_config_and_logger(type_order):
    """Carrega config.json e inicializa logger."""
    try:
        base_name = f"config_{type_order.lower()}"
        config = carregar_config(base_name)
        logger = setup_logger(f"{config['symbol']}_{type_order}_manager_positions_hedge")
        return config, logger
    except FileNotFoundError:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Erro Crítico: Arquivo de configuração para '{type_order}' não encontrado em /config.")
        return None, None
    except Exception as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Erro ao carregar config.json ou configurar o logger: {e}")
        return None, None

def init_mt5_connection(account, logger, mt5_path, symbol):
    """Inicializa MT5 e valida conexão."""
    if not initialize_mt5(account, logger, mt5_path):
        return False
    logger.info(f"Conectado ao MT5. Monitorando símbolo: {symbol}")
    return True

def should_save_excel(ultima_gravacao, intervalo):
    return (time.time() - ultima_gravacao) >= intervalo

def should_check_margin(ultima_verificacao, intervalo):
    return (time.time() - ultima_verificacao) >= intervalo

def should_check_target_down(ultima_verificacao, intervalo):
    return (time.time() - ultima_verificacao) >= intervalo

def should_check_hedge(ultima_verificacao, intervalo):
    return (time.time() - ultima_verificacao) >= intervalo

def should_check_drawdown(ultima_verificacao, intervalo): # <-- ADICIONAR ESTA FUNÇÃO
    return (time.time() - ultima_verificacao) >= intervalo

def process_positions(config, type_order_mt5, logger, symbol,
                      ultima_gravacao_excel, ultima_verificacao_margem,
                      ultima_verificacao_target_down, caminho_excel):
    """Processa posições abertas e executa ações conforme análise."""
    positions = get_open_positions_by_type(symbol, config['magic_number'], type_order_mt5)
    
    df = get_historical_by_hours(config, logger, 'timeframe')
    
    is_trend_signal_up = True
    
    if df is None or df.empty:
        logger.error("Erro ao carregar os dados históricos ou DataFrame vazio.")
    else:
        add_indicators(df, config)
        is_trend_signal_up = df.loc[len(df) -1].trend_signal == 'UP'
        logger.info(f"Sinal para trend é: {df.loc[len(df) -1].trend_signal}, {is_trend_signal_up} == UP")

    # Condição de abertura de novas ordens
    if should_check_target_down(ultima_verificacao_target_down, config["target_down_interval_seconds"]):
        is_true_check_positions, _ = check_positions_condition(
            positions,
            type_order_mt5,
            config["target_up_dollars"],
            config["target_down_dollars"],
            logger,
            ultima_verificacao_target_down,
            config["target_down_interval_seconds"]
        )

        ultima_verificacao_target_down = time.time()
        
        if is_true_check_positions and is_trend_signal_up:
            logger.info(f"Condição atendida → Abrindo nova ordem {type_order_mt5}")
            open_new_order(symbol, type_order_mt5, config, logger, positions)
    
    # Análise das posições
    analise, positions = manager_positions(config, type_order_mt5)
    if analise:
        logger.info(
            f"Posições: {analise['total_positions']} "
            f"(B: {analise['buy_positions']}, S: {analise['sell_positions']}) | "
            f"Lucro Total: {analise['total_profit']:.2f} | "
            f"Equity: {analise['equity']:.2f} | "
            f"Margem Livre: {analise['margin_free_perc']:.2%}"
        )

        # Salvar Excel
        if config['export_to_excel'] and should_save_excel(ultima_gravacao_excel, config['excel_save_interval_seconds']):
            logger.info(f"Salvando dados no arquivo Excel: {caminho_excel}")
            salvar_em_excel(analise, caminho_excel)
            ultima_gravacao_excel = time.time()

        # Gerenciar margem
        if should_check_margin(ultima_verificacao_margem, config['manager_margin_interval_seconds']):

            is_trend_signal = df.loc[len(df) -1].trend_signal == 'DOWN'
            logger.info(f"Sinal para trend é: {df.loc[len(df) -1].trend_signal}, {is_trend_signal} == DOWN")

            if is_trend_signal:
                # Adiciona sells para balancer hedge
                new_sell_trades(analise, config, logger, symbol)
                       
            handle_low_margin(
                margin_free_perc=analise['margin_free_perc'],
                open_positions=positions,
                config=config,
                logger=logger
            )
            ultima_verificacao_margem = time.time()
            
            #Envio de alerta, email
            check_equity_and_alert(config, logger, analise['equity'])
            
    return ultima_gravacao_excel, ultima_verificacao_margem, ultima_verificacao_target_down, positions

def main(type_order="BUY"):
    config, logger = load_config_and_logger(type_order)
    if not config or not logger:
        return

    # Presumindo que você adicione 'shutdown_hour' ao seu config. 
    # Usamos .get() para ter um valor padrão (ex: 99) caso não esteja definido.
    # Coloque 99 (ou qualquer hora "impossível") para nunca desligar por padrão.
    shutdown_hour = config.get('shutdown_hour', 99)

    env = "demo"
    # env = "real"
    account = carregar_conta(type_order, env)
    # account = carregar_conta(type_order, "real")
    symbol = config['symbol']

    if not init_mt5_connection(account, logger, config['mt5_path'], symbol):
        return

    caminho_excel = gerar_nome_excel(symbol, config['export_folder'], type_order, env)
    
    ultima_gravacao_excel = ultima_verificacao_margem = ultima_verificacao_target_down = 0
    
    try:
        while True:
            # --- INÍCIO DA MODIFICAÇÃO ---
            # Pega a hora atual
            current_hour = datetime.datetime.now().hour
            
            # Verifica se a hora atual atingiu ou passou da hora de desligar
            if current_hour >= shutdown_hour:
                logger.info(f"Horário de encerramento ({shutdown_hour}h) atingido. Finalizando o programa.")
                break  # Sai do loop 'while True'
            # --- FIM DA MODIFICAÇÃO ---            
            
            try:
                type_order_mt5 = mt5.ORDER_TYPE_BUY if type_order == 'BUY' else mt5.ORDER_TYPE_SELL

                ultima_gravacao_excel, ultima_verificacao_margem, ultima_verificacao_target_down, positions = process_positions(
                    config, type_order_mt5, logger, symbol,
                    ultima_gravacao_excel, ultima_verificacao_margem,
                    ultima_verificacao_target_down, caminho_excel
                )

            except Exception as e:
                logger.error(f"Erro ao comunicar com o MT5: {e}", exc_info=True)
                logger.warning("Conexão perdida. Tentando reconectar em 30s...")
                mt5.shutdown()
                time.sleep(30)

                if not mt5.initialize():
                    logger.critical("Falha ao reconectar com o MT5. Encerrando.")
                    break
                else:
                    logger.info("Reconexão com sucesso. Retomando monitoramento.")

            time.sleep(config['check_interval_seconds'])

    except KeyboardInterrupt:
        logger.info("Programa interrompido pelo usuário.")
    finally:
        mt5.shutdown()
        logger.info("Conexão com MT5 encerrada.")

if __name__ == "__main__":
    main()
