from .mt5_order import get_historical_by_hours
from .pandas_aux import add_indicators

def can_add_trend_order(config, logger):
    """
    Verifica se há sinal de tendência (DOWN) no timeframe atual e no anterior
    para decidir se uma nova ordem pode ser aberta.
    """
    symbol = config.get("symbol", "UNKNOWN")

    try:
        # --- Buscar dados históricos ---
        df_current = get_historical_by_hours(config, logger, 'timeframe')
        df_prev = get_historical_by_hours(config, logger, 'timeframe_previous')

        # --- Validações básicas ---
        if df_current is None or df_current.empty:
            logger.error(f"[{symbol}] Erro: dataframe atual vazio ou não carregado.")
            return False
        if df_prev is None or df_prev.empty:
            logger.error(f"[{symbol}] Erro: dataframe anterior vazio ou não carregado.")
            return False

        # --- Adicionar indicadores ---
        add_indicators(df_current, config)
        add_indicators(df_prev, config)

        # --- Verifica colunas obrigatórias ---
        required_cols = {"trend_signal", "trend_strength"}
        for df_name, df in [("atual", df_current), ("anterior", df_prev)]:
            missing_cols = required_cols - set(df.columns)
            if missing_cols:
                logger.error(f"[{symbol}] Colunas ausentes no DataFrame {df_name}: {missing_cols}")
                return False

        # --- Extrair últimos sinais ---
        last_signal_current = df_current.iloc[-1]["trend_signal"]
        last_signal_prev = df_prev.iloc[-1]["trend_signal"]
        last_strength_prev = df_prev.iloc[-1]["trend_strength"]

        is_signal_current_down = last_signal_current == "DOWN"
        is_signal_prev_down_strong = (last_signal_prev == "DOWN" and last_strength_prev == "STRONG")

        # --- Logs detalhados ---
        logger.info(
            f"[{symbol}] Análise de tendência:"
            f" | Atual: trend_signal={last_signal_current}"
            f" | Anterior: trend_signal={last_signal_prev}, trend_strength={last_strength_prev}"
            f" | Resultado: {'OK' if (is_signal_current_down or is_signal_prev_down_strong) else 'SEM SINAL'}"
        )

        return is_signal_current_down or is_signal_prev_down_strong

    except Exception as e:
        logger.exception(f"[{symbol}] Erro inesperado ao avaliar sinal de tendência: {e}")
        return False
