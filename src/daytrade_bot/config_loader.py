from pathlib import Path
import json

# daytrade_bot_vitrine/
# ├── config/
# └── src/daytrade_bot/
ROOT = Path(__file__).resolve().parents[2]  # .../daytrade_bot_vitrine
CONFIG_DIR = ROOT / "config"

def load_json_config(base_name: str) -> dict:
    """
    Procura primeiro por config local (não versionada) e depois pelo sample.
    Ex:
      - config/config_buy.local.json
      - config/config_buy.sample.json
    """
    local = CONFIG_DIR / f"{base_name}.local.json"
    sample = CONFIG_DIR / f"{base_name}.sample.json"

    path = local if local.exists() else sample
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado. Esperado: {local.name} ou {sample.name}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
