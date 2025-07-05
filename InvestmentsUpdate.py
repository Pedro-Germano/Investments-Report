import pandas as pd
import yfinance as yf
import requests
import pytz
import time
from datetime import datetime

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# Ativos
wallet = pd.DataFrame([
    {"Ticker": "B3SA3.SA", "Quantidade": 50, "Preço Médio": 9.93, "Data de Compra": "2024-12-09"},
    {"Ticker": "BTCI11.SA", "Quantidade": 36, "Preço Médio": 8.11, "Data de Compra": "2024-12-09"},
    {"Ticker": "BTHF11.SA", "Quantidade": 5, "Preço Médio": 8.73, "Data de Compra": "2025-07-01"},
    {"Ticker": "ROXO34.SA", "Quantidade": 41, "Preço Médio": 12.15, "Data de Compra": "2024-12-09"},
])

# Cria novas colunas para os resultados
wallet['Cotação Atual'] = None
wallet['Valor Atual'] = None
wallet['Valor Investido'] = wallet['Quantidade'] * wallet['Preço Médio']
wallet['Lucro/Prejuízo (R$)'] = None
wallet['Rentabilidade Total (%)'] = None
wallet['Rentabilidade Anualizada (%)'] = None

# Função para pegar Cotação Atual de criptomoedas
br_timezone = pytz.timezone("America/Sao_Paulo")
hoje_brasilia = datetime.now(br_timezone)

# Processa cada ativo
for i, row in wallet.iterrows():
    ticker = row['Ticker']
    quantidade = row['Quantidade']
    preco_medio = row['Preço Médio']
    data_compra = pd.to_datetime(row['Data de Compra']).tz_localize('America/Sao_Paulo')

    # Dias em posse
    dias_posse = (hoje_brasilia - data_compra).days
    if dias_posse <= 0:
        dias_posse = 1  # Evita divisão por zero

    try:
        # Tenta pegar com yfinance (ativo tradicional)
        dados = yf.download(ticker, period='1d', interval='1m', progress=False, auto_adjust=True)
        preco_atual = float(dados['Close'].dropna().iloc[-1].squeeze())
    except Exception as e:
        print(f"[AVISO] Não foi possível obter {ticker} via yfinance.")

    valor_atual = quantidade * preco_atual
    valor_investido = quantidade * preco_medio
    lucro = valor_atual - valor_investido
    rent_total = (valor_atual / valor_investido) - 1
    rent_anual = (1 + rent_total) ** (365 / dias_posse) - 1

    wallet.at[i, 'Cotação Atual'] = round(preco_atual, 2)
    wallet.at[i, 'Valor Atual'] = round(valor_atual, 2)
    wallet.at[i, 'Lucro/Prejuízo (R$)'] = round(lucro, 2)
    wallet.at[i, 'Rentabilidade Total (%)'] = round(rent_total * 100, 2)
    wallet.at[i, 'Rentabilidade Anualizada (%)'] = round(rent_anual * 100, 2)

# Exibe resultado
clean_wallet = wallet.copy()
clean_wallet['Ticker'] = clean_wallet["Ticker"].str.replace(".SA", "", regex=False)
clean_wallet[['Ticker', 'Preço Médio', 'Data de Compra', 'Cotação Atual', 'Valor Atual', 'Lucro/Prejuízo (R$)', 'Rentabilidade Total (%)', 'Rentabilidade Anualizada (%)']]

# %%
valor_total = wallet['Valor Atual'].sum()
print(f"💰 Valor total da wallet: R$ {valor_total:,.2f}")

# %%
clean_wallet['Share (%)'] = None
clean_wallet['Valor Atual'] = clean_wallet['Valor Atual'].astype(float)
clean_wallet['Share (%)'] = (clean_wallet['Valor Atual'] / valor_total).round(4)*100

clean_wallet[['Ticker', 'Data de Compra', 'Preço Médio', 'Cotação Atual', 'Valor Atual', 'Lucro/Prejuízo (R$)', 'Rentabilidade Total (%)', 'Rentabilidade Anualizada (%)', 'Share (%)']]

# %%
# Função para rentabilidade de um ativo individual
def calcular_rentabilidade_ativo(ticker, qtd, dias):
    data_inicio = (hoje_brasilia - pd.Timedelta(days=dias)).strftime('%Y-%m-%d')
    try:
        dados = yf.download(ticker, start=data_inicio, progress=False, auto_adjust=True)
        preco_inicio = float(dados['Close'].dropna().iloc[0].squeeze())
        dados = yf.download(ticker, start=hoje_brasilia, progress=False, auto_adjust=True)
        preco_hoje = float(dados['Close'].dropna().iloc[-1].squeeze())
    except Exception:
        print(f"[AVISO] Não foi possível obter {ticker} via yfinance.")

    valor_inicial = preco_inicio * qtd
    valor_final = preco_hoje * qtd
    rentabilidade = (valor_final / valor_inicial - 1) * 100

    return valor_inicial, valor_final, rentabilidade

# Calcula tabela completa de rentabilidades
def calcular_tabela_rentabilidades(wallet):
    br_tz = pytz.timezone("America/Sao_Paulo")
    inicio_do_ano = br_tz.localize(datetime(hoje_brasilia.year, 1, 1))
    
    periodos = {
        "Rent. Diária (%)": 1,
        "Rent. Semanal (%)": 7,
        "Rent. Mensal (%)": 30,
        "Rent. YTD (%)": (hoje_brasilia - inicio_do_ano).days
    }

    resultado = []

    for i, row in wallet.iterrows():
        ticker = row['Ticker']
        qtd = row['Quantidade']
        linha = {"Ticker": ticker}

        for nome_periodo, dias in periodos.items():
            valor_ini, valor_fim, rent = calcular_rentabilidade_ativo(ticker, qtd, dias)
            linha[nome_periodo] = round(rent, 2) if rent is not None else None

        resultado.append(linha)

    df_resultado = pd.DataFrame(resultado)

    # Adiciona linha final com rentabilidade total da carteira ponderada
    total_row = {"Ticker": "TOTAL"}
    for nome_periodo, dias in periodos.items():
        total_ini = 0
        total_fim = 0
        for i, row in wallet.iterrows():
            ticker = row['Ticker']
            qtd = row['Quantidade']
            valor_ini, valor_fim, _ = calcular_rentabilidade_ativo(ticker, qtd, dias)
            if valor_ini is not None:
                total_ini += valor_ini
                total_fim += valor_fim
        rent_total = (total_fim / total_ini - 1) * 100 if total_ini > 0 else None
        total_row[nome_periodo] = round(rent_total, 2) if rent_total is not None else None

    df_resultado = pd.concat([df_resultado, pd.DataFrame([total_row])], ignore_index=True)
    return df_resultado

profitability = calcular_tabela_rentabilidades(wallet)

# Exibe resultado
clean_profitability = profitability.copy()
clean_profitability['Ticker'] = clean_profitability["Ticker"].str.replace(".SA", "", regex=False)
clean_profitability

# %%
from datetime import date

# Função para rentabilidade de benchmark
def calcular_rentabilidade_benchmark(ticker, dias):
    data_inicio = (date.today() - pd.Timedelta(days=dias)).strftime('%Y-%m-%d')
    data_fim = date.today().strftime('%Y-%m-%d')
    try:
        dados = yf.download(ticker, start=data_inicio, progress=False, auto_adjust=True)
        preco_inicio = float(dados['Close'].dropna().iloc[0].squeeze())
        dados = yf.download(ticker, start=data_fim, progress=False, auto_adjust=True)
        preco_hoje = float(dados['Close'].dropna().iloc[-1].squeeze())
        rentabilidade = (preco_hoje / preco_inicio - 1) * 100
        return round(rentabilidade, 2)
    except:
        return None

# Função para CDI aproximado
def calcular_rentabilidade_cdi(dias, taxa_anual=0.15):
    try:
        return round(((1 + taxa_anual) ** (dias / 365) - 1) * 100, 2)
    except:
        return None

# Tabela de rentabilidade dos benchmarks
def calcular_tabela_rentabilidades_benchmarks():
    br_tz = pytz.timezone("America/Sao_Paulo")
    inicio_do_ano = br_tz.localize(datetime(hoje_brasilia.year, 1, 1))

    periodos = {
        "Rent. Diária (%)": 1,
        "Rent. Semanal (%)": 7,
        "Rent. Mensal (%)": 30,
        "Rent. YTD (%)": (hoje_brasilia - inicio_do_ano).days
    }

    benchmarks = {
        "CDI": lambda dias: calcular_rentabilidade_cdi(dias),
        "IBOVESPA": lambda dias: calcular_rentabilidade_benchmark("^BVSP", dias),
        "S&P500": lambda dias: calcular_rentabilidade_ativo("IVVB11.SA", 1, dias)
    }

    resultado = []

    for nome, func in benchmarks.items():
        linha = {"Ticker": nome}
        for nome_periodo, dias in periodos.items():
            rent = func(dias)
            if isinstance(rent, tuple): 
                linha[nome_periodo] = round(rent[2], 2)
            else:
                linha[nome_periodo] = round(rent, 2)
        resultado.append(linha)

    return pd.DataFrame(resultado)

# ✅ Calcula e exibe
benchmark_profitability = calcular_tabela_rentabilidades_benchmarks()
benchmark_profitability

# %% [markdown]
# # Send E-mail

# %%
import os
import smtplib
from email.message import EmailMessage

# Tabelas como HTML
html_wallet = clean_wallet[['Ticker', 'Data de Compra', 'Valor Atual', 'Lucro/Prejuízo (R$)', 
                            'Rentabilidade Total (%)', 'Rentabilidade Anualizada (%)', 'Share (%)']].to_html(index=False, border=0, classes='tabela')
html_profit = clean_profitability.to_html(index=False, border=0, classes='tabela')
html_bench = benchmark_profitability.to_html(index=False, border=0, classes='tabela')

# Estilo embutido para e-mail
style = """
<style>
    body {
        font-family: Arial, sans-serif;
        color: #333;
        padding: 10px;
    }
    h2 {
        color: #1a73e8;
        margin-top: 30px;
    }
    table.tabela {
        border-collapse: collapse;
        width: 100%;
        margin-top: 10px;
        margin-bottom: 30px;
    }
    table.tabela th, table.tabela td {
        border: 1px solid #ccc;
        padding: 8px 12px;
        text-align: right;
        font-size: 14px;
    }
    table.tabela th {
        background-color: #f2f2f2;
        color: #333;
        text-align: center;
    }
    table.tabela tr:nth-child(even) {
        background-color: #fafafa;
    }
</style>
"""

# Monta o corpo do e-mail com HTML e estilo
corpo_html = f"""
<html>
  <head>{style}</head>
  <body>
    <h2>📊 Resumo da Carteira</h2>
    {html_wallet}
    <h2>💲 Valor Total Investido</h2>
    <p style="font-size: 16px;"><strong>R$ {valor_total:,.2f}</strong></p>
    <h2>📈 Rentabilidades dos Ativos</h2>
    {html_profit}
    <h2>💸 Rentabilidades dos Benchmarks</h2>
    {html_bench}
  </body>
</html>
"""

def enviar_email_html(destinatario, assunto, corpo_html):
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = "pedro.germano99@gmail.com"
    msg["To"] = destinatario
    msg.set_content("Seu e-mail não suporta HTML.")
    msg.add_alternative(corpo_html, subtype="html")

    usuario = os.getenv("EMAIL_USER")
    senha = os.getenv("EMAIL_PASS")
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(usuario, senha)
        smtp.send_message(msg)

# Envio do e-mail
enviar_email_html(
    destinatario="pedro.germano99@gmail.com",
    assunto="📬 Relatório diário da carteira",
    corpo_html=corpo_html
)

# jupyter nbconvert --to script relatorio_diario.ipynb