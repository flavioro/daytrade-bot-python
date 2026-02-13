from datetime import datetime, timedelta
from .threshold_config import ThresholdConfig

class ThresholdManager:
    def __init__(self, thresholds):
        self.thresholds = sorted(thresholds, key=lambda x: x.max_order)
        self.active_cooldowns = {}  # {threshold_index: expiration_time}
        self.order_counters = {'buy': 0, 'sell': 0}
        self.last_reset_time = datetime.now()
        
    def check_thresholds(self, order_type, current_count):
        """Verifica se algum limite foi atingido e aplica ações"""
        actions = []
        
        for i, threshold in enumerate(self.thresholds):
            if (threshold.order_type == order_type or 
                threshold.order_type == 'both'):
                
                # Verifica se está em cooldown para este threshold
                if i in self.active_cooldowns:
                    if datetime.now() < self.active_cooldowns[i]:
                        continue  # Ainda em cooldown, pula verificação
                    else:
                        del self.active_cooldowns[i]  # Cooldown expirado
                
                # Verifica se atingiu o limite
                if current_count >= threshold.max_order:
                    action = self._apply_threshold_action(threshold, i, current_count)
                    actions.append(action)
                    
                    # Se configurado para reset, zera contador após ação
                    if threshold.cooldown_reset:
                        self.order_counters[order_type] = 0
                        
        return actions
    
    def _apply_threshold_action(self, threshold, threshold_index, current_count):
        """Aplica a ação do threshold e inicia cooldown"""
        
        # Calcula redução (não permite negativo)
        reduction = min(threshold.order_decrease, current_count)
        new_count = current_count - reduction
        
        # Configura cooldown
        cooldown_end = datetime.now() + timedelta(minutes=threshold.time_wait)
        self.active_cooldowns[threshold_index] = cooldown_end
        
        return {
            'threshold_triggered': threshold.max_order,
            'order_type': threshold.order_type,
            'reduction_applied': reduction,
            'new_count': new_count,
            'cooldown_until': cooldown_end,
            'wait_time_minutes': threshold.time_wait
        }        

# Configuração como você definiu
thresholds_config = [
    ThresholdConfig(8, 'buy', 1, 120),
    ThresholdConfig(13, 'buy', 1, 120), 
    ThresholdConfig(18, 'buy', 2, 120),
    ThresholdConfig(10, 'sell', 1, 90),   # Exemplo para sell
]

# manager = ThresholdManager(thresholds_config)

# # Simulação de uso
# def process_order_flow(order_type, current_orders):
#     actions = manager.check_thresholds(order_type, current_orders)
    
#     for action in actions:
#         print(f"⚡ Threshold {action['threshold_triggered']} atingido!")
#         print(f"📉 Reduzindo {action['reduction_applied']} ordem(ns)")
#         print(f"🕒 Cooldown: {action['wait_time_minutes']}min")
#         print(f"🎯 Novas ordens ativas: {action['new_count']}")
        
#     return actions

# # Exemplo de execução
# process_order_flow('buy', 8)  # Dispara primeiro threshold
# process_order_flow('buy', 13) # Dispara segundo threshold (se não estiver em cooldown)

