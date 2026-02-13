#excel_writer
import pandas as pd
import os
from datetime import datetime

def gerar_nome_excel(symbol, export_folder, type_order='BUY', add_name=None):
    os.makedirs(export_folder, exist_ok=True)
    data = datetime.now().strftime("%Y-%m-%d")
    return f"{export_folder}/{add_name}_monitor_positions_{symbol}_{type_order}_{data}.xlsx" if add_name else f"{export_folder}/monitor_positions_{symbol}_{type_order}_{data}.xlsx"
     

def salvar_em_excel(dados, caminho):
    df = pd.DataFrame([dados])
    
    if not os.path.exists(caminho):
        df.to_excel(caminho, index=False)
    else:
        with pd.ExcelWriter(caminho, mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
            book = writer.book
            sheet = book.active
            startrow = sheet.max_row
            df.to_excel(writer, index=False, header=False, startrow=startrow)
