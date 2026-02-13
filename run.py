import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from daytrade_bot.main_manager_fm_buy_sell import main

if __name__ == "__main__":
    # Por padrão, rodar BUY (conta demo)
    main(type_order="BUY")
