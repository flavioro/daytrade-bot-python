# Daytrade Bot (Python + MetaTrader 5)

Projeto em Python para monitoramento e execução automatizada de ordens no MetaTrader 5, com controle de margem, logs, export para Excel e regras de gestão configuráveis.

> ⚠️ **Aviso importante:** este projeto é educacional. Não é recomendação de investimento. Operar no mercado financeiro envolve risco e pode gerar perdas.

---

## 🎯 Objetivo

Automatizar a abertura e gerenciamento de posições com base em regras e sinais, incluindo:

- monitoramento contínuo
- controle de margem livre
- hedge / balanceamento
- logs detalhados
- export para Excel (auditoria)

---

## ✅ Features

- Conexão com MetaTrader 5 (MT5)
- Execução de ordens BUY/SELL com regras configuráveis
- Controle de margem livre + alertas de equity
- Reconexão automática em caso de falha
- Logs e rastreabilidade do processo
- Export automático para Excel
- Arquitetura modular (serviços separados por responsabilidade)
- Configurações isoladas em arquivos JSON

---

## 🧠 Tecnologias e Competências

Python • MetaTrader5 • Pandas • pandas-ta • Automação • Gestão de risco (conceitos) • Logs • Data Processing • Export Excel

---

## 🏗️ Estrutura do Projeto

```txt
daytrade_bot/
├── run.py
├── requirements.txt
├── .gitignore
├── config/
│   ├── config_buy.sample.json
│   ├── hedge_state_buy.sample.json
│   ├── account_demo_buy.sample.json
│   ├── account_demo_sell.sample.json
│   ├── account_real_buy.sample.json
│   └── account_real_sell.sample.json
├── scripts/
│   └── run_windows.sample.bat
├── src/
│   └── daytrade_bot/
│       ├── main_manager_fm_buy_sell.py
│       ├── mt5_order.py
│       └── ...
└── tests/
    └── ...
```

---

## ⚠️ Primeira execução: sempre em conta DEMO

Antes de rodar em conta real, rode o bot em **DEMO** para validar:

- conexão com MT5
- símbolo e permissões
- parâmetros (TP/SL/volume)
- intervalos e regras
- export de Excel
- estabilidade do loop

---

## ▶️ Como executar (Windows)

### 1) Clone o projeto
```bash
git clone <URL_DO_SEU_REPO>
cd daytrade_bot
```

### 2) Crie e ative o ambiente virtual
```bash
python -m venv venv
venv\Scripts\activate
```

### 3) Instale dependências
```bash
pip install -r requirements.txt
```

📌 Dependências principais (resumo):
- `MetaTrader5` (integração com MT5)
- `pandas` (tratamento de dados)
- `pandas-ta` (indicadores técnicos)
- `openpyxl` (export para Excel)

### 4) Instale e configure o MetaTrader 5
- Instale o terminal MT5 no Windows
- Faça login na sua corretora (DEMO primeiro)

---

## 🔐 Configuração (sem expor credenciais)

### 1) Crie os arquivos `.local.json`

Copie os arquivos sample e crie os arquivos locais (não versionados):

- `config/config_buy.local.json`
- `config/hedge_state_buy.local.json`
- `config/account_demo_buy.local.json`

> Os arquivos `.local.json` estão no `.gitignore` e **não sobem** para o GitHub.

---

## ▶️ Rodando o bot

### Rodar BUY (DEMO)
```bash
python run.py
```

> Por padrão, o `run.py` executa o modo BUY.

---

## 🧪 Testes

```bash
pytest
```

---


---

## 📸 Demonstração (prints e evidências)

> Coloque seus prints na pasta `img/` para o GitHub renderizar automaticamente no README.

### Execução em loop + logs (Spyder / console)
![Execução no Spyder](img/Captura%20de%20Tela%20%2837%29.png)

> Dica: se preferir, renomeie o arquivo para `img/spyder_execucao.png` e troque o link acima para ficar mais “limpo”.

### Exemplo de arquivo gerado (Excel)
O bot gera planilhas para auditoria/monitoramento em `results/` (ex.: `results/demo_monitor_positions_<SYMBOL>_<BUY|SELL>_<DATA>.xlsx`).

### Trecho real de log (exemplo)
```txt
13:24:05 [INFO] Sinal para trend é: UP, True == UP
13:24:05 [INFO] Posições: 1 (B: 1, S: 0) | Lucro Total: -0.42 | Equity: 1013.58 | Margem Livre: 97.53%
13:25:05 [INFO] Sinal para trend é: UP, True == UP
13:25:05 [INFO] Posições: 1 (B: 1, S: 0) | Lucro Total: 0.98 | Equity: 1014.98 | Margem Livre: 97.53%
13:25:05 [INFO] Salvando dados no arquivo Excel: results/demo_monitor_positions_XAUUSD_BUY_2026-02-13.xlsx
13:26:05 [INFO] Sinal para trend é: UP, True == UP
13:26:05 [INFO] Posições: 1 (B: 1, S: 0) | Lucro Total: 6.07 | Equity: 1020.07 | Margem Livre: 97.55%
13:27:05 [INFO] Sinal para trend é: UP, True == UP
13:27:05 [INFO] Posições: 0 (B: 0, S: 0) | Lucro Total: 0.00 | Equity: 1027.98 | Margem Livre: 100.00%
13:27:05 [INFO] Salvando dados no arquivo Excel: results/demo_monitor_positions_XAUUSD_BUY_2026-02-13.xlsx
13:28:05 [INFO] Sinal para trend é: UP, True == UP
13:28:05 [INFO] Posições: 0 (B: 0, S: 0) | Lucro Total: 0.00 | Equity: 1027.98 | Margem Livre: 100.00%
```

## 👤 Autor

Flavio Rodrigues  
LinkedIn: https://www.linkedin.com/in/flaviorobertorodrigues/  
GitHub: https://github.com/flavioro
