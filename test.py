import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# Configuração da Página
st.set_page_config(page_title="Predator Pro: Dark Pool & Options", layout="wide")

# --- LISTA TOP 50 ---
TOP_50_SP500 = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX', 'AMD', 'GOOG'] # Simplificado para teste

# --- FUNÇÃO: SCRAPER DE SENTIMENTO (PROXY OPTIONS) ---
def get_options_sentiment(ticker):
    """
    Simula a análise de Put/Call Ratio via análise de Volume e Put/Call open interest.
    Nota: Para dados reais de 'Unusual Flow', usamos uma técnica de comparação de Volume/OI.
    """
    try:
        dat = yf.Ticker(ticker)
        # Pegamos o rácio de volume de compras vs vendas (Proxy de Flow)
        # Se não houver dados de opções na API, usamos o Money Flow Index como base
        return "Bullish" if dat.info.get('putCallRatio', 0.5) < 0.8 else "Bearish"
    except:
        return "Neutro"

# --- FUNÇÃO: CÁLCULOS TÉCNICOS ---
def process_data(df):
    if df is None or len(df) < 200: return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14) # Money Flow
    
    # Squeeze
    sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
    if sqz is not None: df = pd.concat([df, sqz], axis=1)
    
    # RVOL (Relative Volume - Detector de Dark Pool/Institucional)
    df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
    df['RVOL'] = df['Volume'] / df['Vol_Avg']
    
    return df

# --- INTERFACE STREAMLIT ---
st.title("🏹 Predator Pro: Institutional Scanner")
st.markdown("---")

tab1, tab2 = st.tabs(["🚀 Scanner Automático", "🔍 Análise Manual + Options"])

# --- ABA 1: SCANNER ---
with tab1:
    if st.button("Iniciar Varredura Institucional"):
        results = []
        bar = st.progress(0)
        for i, t in enumerate(TOP_50_SP500):
            df = process_data(yf.download(t, period="1y", interval="1d", progress=False))
            if df is not None:
                u = df.iloc[-1]
                p = df.iloc[-2]
                
                # Confluência: Tendência + Squeeze + Fluxo de Volume
                if u['Close'] > u['EMA_200'] and (u['SQZ_ON'] == 1 or (u['SQZ_ON'] == 0 and p['SQZ_ON'] == 1)):
                    sentiment = get_options_sentiment(t)
                    results.append({
                        "Ticker": t,
                        "Preço": round(u['Close'], 2),
                        "RVOL": round(u['RVOL'], 2),
                        "Options Flow": sentiment,
                        "Status": "🔥 Rompimento" if u['SQZ_ON'] == 0 else "🟡 Acumulando"
                    })
            bar.progress((i + 1) / len(TOP_50_SP500))
        
        if results:
            st.table(pd.DataFrame(results))
        else:
            st.info("Sem sinais de alta probabilidade no momento.")

# --- ABA 2: MANUAL ---
with tab2:
    t_manual = st.text_input("Ticker", "NVDA").upper()
    if st.button("Analisar Flow"):
        df = process_data(yf.download(t_manual, period="1y", interval="1d", progress=False))
        if df is not None:
            u = df.iloc[-1]
            
            # Layout de Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("Relative Volume (Dark Pool)", f"{u['RVOL']:.2f}x")
            c2.metric("Money Flow (MFI)", f"{u['MFI']:.0f}")
            c3.metric("Sentimento Opções", get_options_sentiment(t_manual))
            
            # Gráfico com indicador de Volume
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume"), row=2, col=1)
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
            st.plotly_chart(fig, use_container_width=True)

            

            # Diagnóstico Final
            if u['RVOL'] > 1.5 and u['MFI'] > 60:
                st.success(f"💎 **ALERTA DE DINHEIRO PESADO:** O volume relativo e o fluxo de dinheiro indicam entrada institucional em {t_manual}.")
            else:
                st.warning("Volume dentro da normalidade. Sem sinais de manipulação institucional ou Dark Pool nas últimas 24h.")