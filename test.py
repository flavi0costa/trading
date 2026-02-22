import yfinance as yf
import pandas as pd
import pandas_ta as ta

# Lista de tickers para monitorar (exemplo)
tickers = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "ABEV3.SA", "MGLU3.SA"]

def screening_bot(ticker_list):
    opportunities = []

    for ticker in ticker_list:
        try:
            # 1. Extração de Dados
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            info = stock.info

            if df.empty: continue

            # 2. Cálculo de Indicadores (Technical Analysis)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['SMA_50'] = ta.sma(df['Close'], length=50)
            df['SMA_200'] = ta.sma(df['Close'], length=200)
            
            last_close = df['Close'].iloc[-1]
            last_rsi = df['RSI'].iloc[-1]

            # --- CRITÉRIOS DE FILTRO ---

            # A. Momentum Forte (RSI entre 60 e 70)
            momentum = last_rsi > 60 and last_rsi < 75

            # B. Breakout Técnico (Preço cruza SMA_50 para cima)
            breakout = last_close > df['SMA_50'].iloc[-1] and df['Close'].iloc[-2] <= df['SMA_50'].iloc[-2]

            # C. Undervalued (P/E Ratio abaixo da média histórica - simplificado)
            pe_ratio = info.get('forwardPE', 100)
            undervalued = pe_ratio < 12 and pe_ratio > 0

            # 3. Agregação de Oportunidades
            if momentum or breakout or undervalued:
                opportunities.append({
                    "Ticker": ticker,
                    "Preço": round(last_close, 2),
                    "RSI": round(last_rsi, 2),
                    "P/E": pe_ratio,
                    "Sinal": "Momentum" if momentum else ("Breakout" if breakout else "Value")
                })
        except Exception as e:
            print(f"Erro ao processar {ticker}: {e}")

    return pd.DataFrame(opportunities)

# Execução
print("🔍 Iniciando screening...")
resultado = screening_bot(tickers)
print(resultado)
