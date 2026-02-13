import pandas_ta as ta
import pandas as pd

def add_indicators(df, config):
    # --------------------------------------------------------------------------
    # 3️⃣ Calcular indicadores com pandas-ta
    # --------------------------------------------------------------------------
    
    if not config.get('indicators_ema_adx_active', False):
        return
    
    ema_period = config.get("ema_period", 20)
    adx_period = config.get("adx_period", 14)

    df[f"EMA_{ema_period}"] = ta.ema(df["close"], length=ema_period)
    df[f"ADX_{adx_period}"] = ta.adx(df["high"], df["low"], df["close"], length=adx_period)["ADX_" + str(adx_period)]

    # --------------------------------------------------------------------------
    # 4️⃣ Gerar colunas de interpretação
    # --------------------------------------------------------------------------
    df["trend_signal"] = df.apply(
        lambda row: "UP" if row["close"] > row[f"EMA_{ema_period}"] else "DOWN",
        axis=1,
    )

    def classify_trend_strength(adx):
        if pd.isna(adx):
            return "UNKNOWN"
        elif adx > 25:
            return "STRONG"
        elif adx < 20:
            return "WEAK"
        else:
            return "SIDEWAYS"

    df["trend_strength"] = df[f"ADX_{adx_period}"].apply(classify_trend_strength)
