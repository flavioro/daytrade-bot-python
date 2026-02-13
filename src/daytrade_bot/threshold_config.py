class ThresholdConfig:
    def __init__(self, max_order, order_type, order_decrease, time_wait, cooldown_reset=True):
        self.max_order = max_order          # Limite que dispara a ação
        self.order_type = order_type        # 'buy', 'sell', 'both'
        self.order_decrease = order_decrease # Quantidade a reduzir
        self.time_wait = time_wait          # Minutos de espera (120)
        self.cooldown_reset = cooldown_reset # Zera contador após ação?
        
