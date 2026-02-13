#manager_margin
import MetaTrader5 as mt5
from datetime import datetime
from .mt5_order import get_open_positions_by_type, get_all_open_positions

def manager_positions(config, type_order_mt5):
    """Analisa as posições abertas e retorna um resumo e a lista de posições."""

    if config.get("all_positions", False):
        my_positions = get_all_open_positions(config['symbol'])                      
    else:
        my_positions = get_open_positions_by_type(config['symbol'], config['magic_number'], type_order_mt5)                      
    
    # if not my_positions:
    #     return None, None # Nenhuma posição com o magic number especificado

    buy_count = sell_count = 0
    sum_buy_profit = sum_sell_profit = 0
    
    total_buy_volume = 0.0
    total_sell_volume = 0.0
    
    for p in my_positions:
        if p.type == mt5.ORDER_TYPE_BUY:
            buy_count += 1
            sum_buy_profit += p.profit
            total_buy_volume += p.volume
        elif p.type == mt5.ORDER_TYPE_SELL:
            sell_count += 1
            sum_sell_profit += p.profit
            total_sell_volume += p.volume
            
    # ===================== MUDANÇAS AQUI =====================
    account = mt5.account_info()
    tick = mt5.symbol_info_tick(config['symbol'])

    if not account or not tick:
        return None, None # Falha ao obter informações da conta ou do tick

    # CORREÇÃO: Usando account.equity e account.margin_free em vez de account["..."]
    perc_mf = round(account.margin_free / account.equity, 4) if account.equity else 0

    dados_analise = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_positions": len(my_positions),
        "buy_positions": buy_count,
        "sell_positions": sell_count,
        "total_buy_volume": total_buy_volume,
        "total_sell_volume": total_sell_volume,
        "buy_profit": round(sum_buy_profit, 2),
        "sell_profit": round(sum_sell_profit, 2),
        # CORREÇÃO: Usando a notação de ponto para todos os campos da conta
        "total_profit": account.profit,
        "equity": account.equity, # CAPITAL LIQUIDO
        "balance": account.balance, #SALDO
        "margin_free": account.margin_free,
        "margin_free_perc": perc_mf,
        "current_price": (tick.bid + tick.ask) / 2
    }

    return dados_analise, my_positions