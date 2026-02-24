import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Swing Trade Analyzer", layout="wide")
st.title("🔥 Analisador Swing Trade Profissional")
st.markdown("**Ticker + Multi-timeframe + Padrões de Candles + EMA9**")

# ====================== FUNÇÕES ======================
@st.cache_data(ttl=300)
def baixar_dados(ticker):
    df_d = yf.download(ticker, period="1y", interval="1d", progress=False)
    df_w = yf.download(ticker, period="5y", interval="1wk", progress=False)
    return df_d, df_w

def adicionar_indicadores(df):
    df = df.copy()
    df['EMA9']  = df['Close'].ewm(span=9,  adjust=False).mean()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200']= df['Close'].rolling(200).mean()
    
    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Bollinger
    df['BB_Mid'] = df['Close'].rolling(20).mean()
    df['BB_Std'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
    df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
    
    # ATR
    tr = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift()).abs(),
        (df['Low']  - df['Close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    return df

def detectar_padroes_candle(df):
    if len(df) < 3:
        return ["Dados insuficientes"]
    
    row = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    
    body = abs(row['Close'] - row['Open'])
    range_c = row['High'] - row['Low']
    if range_c == 0:
        return ["Candle indefinido"]
    
    upper_wick = (row['High'] - max(row['Open'], row['Close'])) / range_c
    lower_wick = (min(row['Open'], row['Close']) - row['Low']) / range_c
    body_ratio = body / range_c
    
    patterns = []
    
    # Doji
    if body_ratio < 0.1:
        patterns.append("🔴 Doji – Indecisão forte")
    
    # Marubozu
    if body_ratio > 0.85:
        if row['Close'] > row['Open']:
            patterns.append("🟢 Marubozu Bullish – Forte alta")
        else:
            patterns.append("🔴 Marubozu Bearish – Forte baixa")
    
    # Hammer / Hanging Man
    if lower_wick > 0.6 and upper_wick < 0.15 and body_ratio < 0.35:
        if row['Close'] > row['Open']:
            patterns.append("🟢 Hammer Bullish – Reversão de baixa")
        else:
            patterns.append("🔴 Hanging Man – Cuidado (reversão de alta)")
    
    # Shooting Star / Inverted Hammer
    if upper_wick > 0.6 and lower_wick < 0.15 and body_ratio < 0.35:
        if row['Close'] > row['Open']:
            patterns.append("🟢 Inverted Hammer – Reversão de baixa")
        else:
            patterns.append("🔴 Shooting Star – Reversão de alta")
    
    # Engulfing
    prev_body = abs(prev['Close'] - prev['Open'])
    if (row['Close'] > row['Open'] and prev['Close'] < prev['Open'] and
        row['Open'] < prev['Close'] and row['Close'] > prev['Open'] and body > prev_body):
        patterns.append("🟢 Bullish Engulfing – Forte sinal de alta")
    elif (row['Close'] < row['Open'] and prev['Close'] > prev['Open'] and
          row['Open'] > prev['Close'] and row['Close'] < prev['Open'] and body > prev_body):
        patterns.append("🔴 Bearish Engulfing – Forte sinal de baixa")
    
    if not patterns:
        patterns.append("⚪ Padrão neutro / sem sinal claro")
    
    return patterns

# ====================== INTERFACE ======================
col1, col2 = st.columns([3, 1])
with col1:
    ticker = st.text_input("Digite o ticker (ex: PETR4.SA, AAPL, VALE3.SA)", "PETR4.SA").strip().upper()
with col2:
    analisar = st.button("🚀 ANALISAR", type="primary", use_container_width=True)

if analisar:
    with st.spinner(f"Baixando dados e analisando {ticker}..."):
        df_daily, df_weekly = baixar_dados(ticker)
        
        if df_daily.empty:
            st.error("❌ Ticker inválido ou sem dados.")
            st.stop()
        
        df_daily = adicionar_indicadores(df_daily)
        df_weekly = adicionar_indicadores(df_weekly)
        
        last_d = df_daily.iloc[-1]
        last_w = df_weekly.iloc[-1]
        
        # ====================== ANÁLISE SEMANAL ======================
        st.subheader("📅 Análise Semanal (Tendência Primária)")
        if last_w['Close'] > last_w['SMA_200']:
            w_trend = "🟢 Forte Alta" if last_w['SMA_50'] > last_w['SMA_200'] else "🟢 Alta"
            w_score = 2 if last_w['SMA_50'] > last_w['SMA_200'] else 1
        else:
            w_trend = "🔴 Forte Baixa" if last_w['SMA_50'] < last_w['SMA_200'] else "🔴 Baixa"
            w_score = -2 if last_w['SMA_50'] < last_w['SMA_200'] else -1
        
        st.write(f"**Tendência Semanal:** {w_trend}")
        st.write(f"RSI Semanal: **{last_w['RSI']:.1f}**")
        st.write(f"Preço: **{last_w['Close']:.2f}** | SMA50: {last_w['SMA_50']:.2f} | SMA200: {last_w['SMA_200']:.2f}")
        
        # ====================== ANÁLISE DIÁRIA ======================
        st.subheader("📊 Análise Diária + EMA9 + Padrões de Candles")
        
        # Score
        score = w_score
        if last_d['MACD_Hist'] > 0 and last_d['MACD'] > last_d['MACD_Signal']:
            score += 1.5
        elif last_d['MACD_Hist'] < 0 and last_d['MACD'] < last_d['MACD_Signal']:
            score -= 1.5
        if 35 <= last_d['RSI'] <= 55:
            score += 1
        if last_d['Close'] > last_d['EMA9']:
            score += 0.8
        else:
            score -= 0.8
        if last_d['Close'] > last_d['EMA20']:
            score += 0.5
        
        if score >= 3.5:
            sinal = "🟢 **FORTE COMPRA** – Alinhamento excelente"
            action = "ENTRADA LONG"
        elif score >= 1.5:
            sinal = "🟡 COMPRA moderada"
            action = "ENTRADA LONG"
        elif score <= -3.5:
            sinal = "🔴 **FORTE VENDA**"
            action = "ENTRADA SHORT"
        elif score <= -1.5:
            sinal = "🟠 VENDA moderada"
            action = "ENTRADA SHORT"
        else:
            sinal = "⚪ NEUTRO – Aguarde"
            action = "Sem entrada"
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Score Total", f"{score:.1f}/6", delta=None)
        with col_b:
            st.metric("Preço Atual", f"R$ {last_d['Close']:.2f}")
        with col_c:
            st.metric("RSI Diário", f"{last_d['RSI']:.1f}")
        
        st.success(sinal)
        st.info(f"**Ação recomendada:** {action}")
        
        # Padrões de candles
        padroes = detectar_padroes_candle(df_daily)
        st.write("**Leitura de Candles (último candle):**")
        for p in padroes:
            st.write(f"• {p}")
        
        # ====================== GRÁFICO ======================
        st.subheader("📈 Gráfico Diário Interativo")
        
        df_plot = df_daily.tail(180).copy()  # últimos 6 meses
        
        fig = go.Figure()
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df_plot.index,
            open=df_plot['Open'],
            high=df_plot['High'],
            low=df_plot['Low'],
            close=df_plot['Close'],
            name="Candles"
        ))
        
        # EMAs
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA9'],  name="EMA 9",  line=dict(color="magenta", width=2)))
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA20'], name="EMA 20", line=dict(color="orange", width=2)))
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA50'], name="EMA 50", line=dict(color="blue", width=2)))
        
        # Bollinger
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BB_Upper'], name="BB Upper", line=dict(color="gray", dash="dash")))
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BB_Lower'], name="BB Lower", line=dict(color="gray", dash="dash")))
        
        fig.update_layout(
            height=650,
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            title=f"{ticker} - Últimos 180 dias"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # ====================== GESTÃO DE RISCO ======================
        atr = last_d['ATR']
        current = last_d['Close']
        
        if "LONG" in action:
            sl = current - 1.5 * atr
            tp = current + 3.0 * atr
        elif "SHORT" in action:
            sl = current + 1.5 * atr
            tp = current - 3.0 * atr
        else:
            sl = tp = None
        
        st.subheader("🎯 Gestão de Risco Sugerida")
        if sl and tp:
            st.write(f"**Entrada:** Atual ou pullback na EMA9")
            st.write(f"**Stop Loss:** {sl:.2f}  ({((current-sl)/current*100 if 'LONG' in action else (sl-current)/current*100):.1f}% risco)")
            st.write(f"**Take Profit:** {tp:.2f}  (RR ≈ 2:1)")
        
        st.caption("⚠️ Isso é apenas uma ferramenta técnica. Nunca é recomendação de investimento. Gerencie seu risco.")

# Rodapé
st.markdown("---")
st.markdown("Feito com ❤️ para swing traders • Atualiza a cada 5 minutos")