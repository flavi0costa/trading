import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Ultra Momentum Dashboard", layout="wide")

# ==========================================
# 1. FUNÇÕES CORE (PROTEGIDAS)
# ==========================================
@st.cache_data(ttl=300)
def baixar_dados(ticker, interval="1d"):
    df = yf.download(ticker, period="2y", interval=interval, progress=False, auto_adjust=True)
    if df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]
    return df.dropna(how='all').ffill()

def obter_earnings_data(ticker):
    try:
        t = yf.Ticker(ticker)
        cal = t.calendar
        if cal is not None and not cal.empty:
            return cal.iloc[0, 0]
    except: return None
    return None

def detectar_candles(df):
    if len(df) < 5: return "Sem dados"
    u = df.iloc[-1]
    p = df.iloc[-2]
    corpo = abs(u['Close'] - u['Open'])
    tamanho = u['High'] - u['Low']
    pavio_inf = min(u['Open'], u['Close']) - u['Low']
    pavio_sup = u['High'] - max(u['Open'], u['Close'])
    
    if pavio_inf > (2 * corpo) and pavio_sup < (0.1 * tamanho): return "🟢 Martelo"
    if u['Close'] > p['Open'] and u['Open'] < p['Close'] and u['Close'] > u['Open'] and p['Close'] < p['Open']: return "🟢 Engolfo Alta"
    if pavio_sup > (2 * corpo) and pavio_inf < (0.1 * tamanho): return "🔴 Shooting Star"
    if corpo < (0.1 * tamanho): return "🟡 Doji"
    return "⚪ Neutro"

def adicionar_indicadores(df):
    if len(df) < 50: return df
    df = df.copy()
    df['EMA9'] = ta.ema(df['Close'], length=9)
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['EMA50'] = ta.ema(df['Close'], length=50)
    df['SMA200'] = ta.sma(df['Close'], length=200)
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    df['RSI_2'] = ta.rsi(df['Close'], length=2)
    df.ta.adx(append=True)
    df.ta.supertrend(append=True)
    df.ta.macd(append=True)
    df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    return df

# ==========================================
# 2. INTERFACE E ABAS
# ==========================================
st.title("🔥 Ultra Momentum Pro")

tab1, tab2 = st.tabs(["📊 Analisador Individual", "🔍 Scanner de Oportunidades"])

with tab1:
    # Sidebar de Risco integrada na UI para não poluir
    with st.sidebar:
        st.header("💰 Gestão de Risco")
        cap_total = st.number_input("Capital Total", value=10000.0)
        risco_p = st.slider("Risco por Trade (%)", 0.5, 5.0, 1.0)
    
    st.subheader("Análise Profunda de um Ativo")
    col_in1, col_in2 = st.columns([3, 1])
    with col_in1:
        ticker_input = st.text_input("Ticker para Análise", "NVDA", key="in_single").upper().strip()
    with col_in2:
        st.write("") 
        btn_analisar = st.button("🚀 Executar Análise", use_container_width=True, key="btn_single")

    if btn_analisar:
        with st.spinner("A analisar..."):
            df = baixar_dados(ticker_input)
            df_w = baixar_dados(ticker_input, interval="1wk") # Dados Semanais para o filtro
            
            if df.empty:
                st.error("Ticker não encontrado.")
            else:
                df = adicionar_indicadores(df)
                df_w = adicionar_indicadores(df_w)
                d = df.iloc[-1]
                w = df_w.iloc[-1]
                
                # --- ALERTA DE EARNINGS ---
                prox_e = obter_earnings_data(ticker_input)
                if prox_e:
                    dias = (prox_e.date() - datetime.now().date()).days
                    if 0 <= dias <= 7:
                        st.warning(f"⚠️ ATENÇÃO: Earnings em {dias} dias ({prox_e.date()}). Risco de volatilidade extrema!")

                # --- MÉTRICAS DE PREÇO ---
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Preço", f"${d['Close']:.2f}")
                m2.metric("RSI (14)", f"{d['RSI_14']:.1f}")
                m3.metric("RSI (2)", f"{d['RSI_2']:.1f}")
                m4.metric("Padrão Candle", detectar_candles(df))

                # --- CALCULADORA DE POSIÇÃO ---
                atr = float(d['ATR'])
                preco = float(d['Close'])
                col_st_dir = [c for c in df.columns if c.startswith('SUPERTd')][0]
                st_dir = int(d[col_st_dir])
                
                sl = preco - (1.5 * atr) if st_dir == 1 else preco + (1.5 * atr)
                tp = preco + (3.0 * atr) if st_dir == 1 else preco - (3.0 * atr)
                
                # Lógica da Calculadora
                valor_em_risco = cap_total * (risco_p / 100)
                distancia_sl = abs(preco - sl)
                num_acoes = int(valor_em_risco / distancia_sl) if distancia_sl > 0 else 0
                
                st.info(f"🛡️ **Gestão:** SL: **${sl:.2f}** | TP: **${tp:.2f}** | Comprar: **{num_acoes}** ações (Risco: ${valor_em_risco:.2f})")

                # --- GRÁFICO (MANTIDO EXATAMENTE IGUAL) ---
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                df_p = df.tail(120)
                fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Preço"), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA9'], name="EMA 9", line=dict(color='cyan', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA21'], name="EMA 21", line=dict(color='orange', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA50'], name="EMA 50", line=dict(color='magenta', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name="SMA 200", line=dict(color='white', width=2)), row=1, col=1)
                colors = ['green' if df_p['Close'][i] >= df_p['Open'][i] else 'red' for i in range(len(df_p))]
                fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name="Volume", marker_color=colors), row=2, col=1)
                fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                # --- CHECKLIST (COM FILTRO SEMANAL) ---
                st.subheader("✅ Verificação de Estratégia")
                c1, c2, c3 = st.columns(3)
                col_stw = [c for c in df_w.columns if c.startswith('SUPERTd')][0]
                
                with c1:
                    st.write(f"{'✅' if d['Close'] > d['EMA21'] else '❌'} Diário > EMA 21")
                    st.write(f"{'✅' if w[col_stw] == 1 else '❌'} Semanal em Alta (Maré)")
                with c2:
                    st.write(f"{'✅' if st_dir == 1 else '❌'} SuperTrend Diário")
                    st.write(f"{'✅' if d.filter(like='ADX').iloc[0] > 25 else '⚠️'} ADX > 25")
                with c3:
                    st.write(f"{'✅' if 30 < d['RSI_14'] < 70 else '⚠️'} RSI 14 Seguro")
                    st.write(f"{'🔥' if d['RSI_2'] < 15 else 'OK'} RSI 2 Pullback")

# (O Scanner da Aba 2 permanece igual ao teu código anterior)
