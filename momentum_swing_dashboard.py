import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import warnings

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Ultra Momentum Dashboard", layout="wide")

@st.cache_data(ttl=300)
def baixar_dados(ticker):
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    if df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]
    return df.dropna(how='all').ffill()

def detectar_candles(df):
    if len(df) < 5: return "Sem dados"
    u = df.iloc[-1] # Último
    p = df.iloc[-2] # Penúltimo
    corpo = abs(u['Close'] - u['Open'])
    tamanho = u['High'] - u['Low']
    pavio_inf = min(u['Open'], u['Close']) - u['Low']
    pavio_sup = u['High'] - max(u['Open'], u['Close'])
    
    if pavio_inf > (2 * corpo) and pavio_sup < (0.1 * tamanho): return "🟢 Martelo (Rejeição de Fundo)"
    if u['Close'] > p['Open'] and u['Open'] < p['Close'] and u['Close'] > u['Open'] and p['Close'] < p['Open']: return "🟢 Engolfo de Alta"
    if pavio_sup > (2 * corpo) and pavio_inf < (0.1 * tamanho): return "🔴 Shooting Star (Rejeição de Topo)"
    if corpo < (0.1 * tamanho): return "🟡 Doji (Indecisão)"
    return "⚪ Neutro"

def adicionar_indicadores(df):
    if len(df) < 50: return df
    df = df.copy()
    
    # --- MÉDIAS SOLICITADAS ---
    df['EMA9'] = ta.ema(df['Close'], length=9)
    df['EMA21'] = ta.ema(df['Close'], length=21) # Troca da 20 pela 21
    df['EMA50'] = ta.ema(df['Close'], length=50) # Adição da 50
    df['SMA200'] = ta.sma(df['Close'], length=200)
    
    # --- RSI ---
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    df['RSI_2'] = ta.rsi(df['Close'], length=2) # Caso queira analisar pullbacks curtos
    
    # Outros
    df.ta.adx(append=True)
    df.ta.supertrend(append=True)
    df.ta.macd(append=True)
    df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    return df

# --- INTERFACE ---
st.sidebar.header("⚙️ Configuração Técnica")
ticker_input = st.sidebar.text_input("Ticker", "NVDA").upper().strip()
btn_analisar = st.sidebar.button("🚀 Executar Análise", use_container_width=True)

if btn_analisar:
    df = baixar_dados(ticker_input)
    if not df.empty:
        df = adicionar_indicadores(df)
        d = df.iloc[-1]
        
        st.title(f"📊 Dashboard Profissional: {ticker_input}")
        
        # --- LINHA SUPERIOR DE MÉTRICAS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Preço", f"${d['Close']:.2f}")
        m2.metric("RSI (14)", f"{d['RSI_14']:.1f}")
        m3.metric("RSI (2)", f"{d['RSI_2']:.1f}", help="Abaixo de 10 é compra extrema, acima de 90 é venda extrema.")
        m4.metric("Padrão Candle", detectar_candles(df))

        # --- GESTÃO DE RISCO ---
        atr = float(d['ATR'])
        preco = float(d['Close'])
        col_st_dir = [c for c in df.columns if c.startswith('SUPERTd')][0]
        st_dir = int(d[col_st_dir])
        
        sl = preco - (1.5 * atr) if st_dir == 1 else preco + (1.5 * atr)
        tp = preco + (3.0 * atr) if st_dir == 1 else preco - (3.0 * atr)
        
        st.info(f"🛡️ **Gestão de Risco (ATR):** STOP LOSS: **${sl:.2f}** | TAKE PROFIT: **${tp:.2f}** (Rácio 2:1)")

        # --- GRÁFICO ---
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        df_p = df.tail(120)
        
        # Candles e Médias
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Preço"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA9'], name="EMA 9 (Fast)", line=dict(color='cyan', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA21'], name="EMA 21 (Trend)", line=dict(color='orange', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA50'], name="EMA 50 (Med)", line=dict(color='magenta', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name="SMA 200 (Long)", line=dict(color='white', width=2)), row=1, col=1)
        
        # Volume
        colors = ['green' if df_p['Close'][i] >= df_p['Open'][i] else 'red' for i in range(len(df_p))]
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name="Volume", marker_color=colors), row=2, col=1)
        
        fig.update_layout(height=750, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- CHECKLIST EXPANDIDA ---
        st.subheader("✅ Verificação de Estratégia")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write(f"{'✅' if d['Close'] > d['EMA21'] else '❌'} Acima da EMA 21")
            st.write(f"{'✅' if d['EMA21'] > d['EMA50'] else '❌'} Alinhamento EMA 21 > 50")
        with c2:
            st.write(f"{'✅' if st_dir == 1 else '❌'} SuperTrend (Direção)")
            st.write(f"{'✅' if d.filter(like='ADX').iloc[0] > 25 else '⚠️'} ADX > 25 (Força)")
        with c3:
            st.write(f"{'✅' if 30 < d['RSI_14'] < 70 else '⚠️'} RSI 14 em zona segura")
            st.write(f"{'🔥' if d['RSI_2'] < 15 else 'OK'} RSI 2 (Oportunidade Pullback)")

st.sidebar.caption("Configuração Profissional: EMA 9/21/50/200 + RSI Dual")