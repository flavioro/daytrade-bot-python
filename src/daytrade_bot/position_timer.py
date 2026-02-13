# position_timer.py

from datetime import datetime, timezone
import MetaTrader5 as mt5
from .mt5_order import close_position # Importando a sua função

def check_and_close_positions_by_time(positions, config, logger):
    """
    Verifica o tempo de vida de todas as posições abertas e fecha aquelas
    que excederam o tempo máximo definido na configuração.
    Utiliza o tempo do servidor MT5 como referência.

    Args:
        positions (list): A lista de posições abertas (retornada por mt5.positions_get()).
        config (module): O módulo de configuração com as variáveis.
        logger (Logger): A instância do logger para registrar as ações.
    """
    # 1. Verifica se a funcionalidade está habilitada no config
    if not config.get('close_positions_by_time_enabled', False):
        return

    try:
        max_duration_minutes = config['max_position_duration_minutes']
    except AttributeError:
        logger.error("As variáveis 'CLOSE_POSITIONS_BY_TIME_ENABLED' ou 'MAX_POSITION_DURATION_MINUTES' não foram encontradas no config.")
        return

    logger.info("Iniciando verificação de tempo de vida das posições usando o tempo do servidor MT5...")

    # 2. Itera sobre cada posição aberta
    for position in positions:
        # Pega o tempo de abertura da posição (timestamp UTC)
        position_open_time_utc = datetime.fromtimestamp(position.time, tz=timezone.utc)
        
        # 3. Busca o tempo atual diretamente do servidor da corretora
        symbol_info = mt5.symbol_info_tick(position.symbol)
        if not symbol_info:
            logger.error(f"Não foi possível obter informações para o símbolo {position.symbol}. Pulando verificação para o TICKET {position.ticket}.")
            continue # Pula para a próxima posição

        # O atributo 'time' do symbol_info é o timestamp da última cotação (UTC)
        server_time_ts = symbol_info.time
        server_time_utc = datetime.fromtimestamp(server_time_ts, tz=timezone.utc)
        
        # 4. Calcula a duração que a posição está aberta, usando o tempo do servidor
        duration = server_time_utc - position_open_time_utc
        duration_in_minutes = duration.total_seconds() / 60

        # 5. Compara com o tempo máximo definido
        if duration_in_minutes > max_duration_minutes:
            logger.warning(
                f"TICKET {position.ticket}: Tempo limite excedido! "
                f"Aberta por {duration_in_minutes:.2f} min. Limite: {max_duration_minutes} min."
            )
            # 6. Chama a função para fechar a posição
            close_position(position, logger)