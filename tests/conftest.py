import os
import sys
import types

# Ensure src/ is in PYTHONPATH so "daytrade_bot" can be imported in tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# Mock MetaTrader5 module for Linux CI (MetaTrader5 is Windows-only)
mock_mt5 = types.ModuleType("MetaTrader5")
mock_mt5.ORDER_TYPE_BUY = 0
mock_mt5.ORDER_TYPE_SELL = 1
mock_mt5.TRADE_RETCODE_DONE = 10009
mock_mt5.symbol_info_tick = lambda symbol: None
mock_mt5.positions_get = lambda **kwargs: []
mock_mt5.order_send = lambda **kwargs: None

sys.modules["MetaTrader5"] = mock_mt5
