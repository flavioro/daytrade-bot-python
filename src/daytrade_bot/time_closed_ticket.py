import MetaTrader5 as mt5
import json
import logging
from datetime import datetime, timezone
from .logger_config import setup_logger
from .mt5_history import get_profitable_closed_deals

def carregar_config(caminho='config.json'):
    """Carrega as configurações do arquivo JSON."""
    with open(caminho, 'r') as f:
        return json.load(f)

def load_config_and_logger(type_order):
    """Carrega config.json e inicializa logger."""
    try:
        config = carregar_config()
        logger = setup_logger(f"{config['symbol']}_{type_order}_manager_positions")
        return config, logger
    except FileNotFoundError:
        logging.basicConfig(level=logging.ERROR)
        logging.error("Erro Crítico: Arquivo 'config.json' não encontrado.")
        return None, None
    except Exception as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Erro ao carregar config.json ou configurar o logger: {e}")
        return None, None


def init_mt5_connection(logger):
    """Inicializa MT5 e valida conexão."""
    
    mt5.initialize()
    
    if not mt5.initialize():
        logger.error(f"Falha ao inicializar o MT5, código de erro: {mt5.last_error()}")
        return False
    logger.info("MetaTrader 5 inicializado com sucesso.")
    return True

def main(type_order="BUY", mt5_path="D:/mt5/terminal64.exe"):
    config, logger = load_config_and_logger(type_order)
    if not config or not logger:
        return

    # account = carregar_conta(type_order)
    symbol = config['symbol']

    if not init_mt5_connection(logger):
        return
    
    account_info = mt5.account_info()
    
    if account_info:
        logger.info(f"Conectado à conta {account_info.login}")
    
    # Simula um objeto de configuração
    config = {
        'history_minutes_interval': 6 # Buscar nos últimos 120 minutos (2 horas)
    }
    
    # 1. Buscar posições de BUY que foram fechadas com lucro
    logger.info("--- Buscando por posições de BUY fechadas com lucro ---")
    closed_buy_deals = get_profitable_closed_deals(symbol, 'BUY', config, logger)

    if closed_buy_deals:
        for deal in closed_buy_deals:
            # O tempo do negócio já vem como um timestamp, podemos converter
            server_time_utc = datetime.fromtimestamp(deal.time, tz=timezone.utc)
            logger.info(f"hora server_time_utc {server_time_utc}")
            logger.info(
                f"  > Posição BUY fechada encontrada! Ticket: {deal.order}, "
                f"Lucro: {deal.profit:.2f}, "
                f"Hora de Fechamento: {server_time_utc.strftime('%Y-%m-%d %H:%M:%S')}, "
                # f"Minutos atrás: {((datetime.now() - server_time_utc).total_seconds() / 60):.1f}"
            )

    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()