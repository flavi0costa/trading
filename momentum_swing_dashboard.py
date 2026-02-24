import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Momentum Swing Dashboard", layout="wide")
st.title("🔥 Momentum Swing Dashboard - US Market")
st.markdown("**VERSÃO FINAL ANTI-SERIES AMBIGUOUS • Funciona com NVDA, WMT, T, LUV**")

@st.cache_data(ttl=300)
def baixar_dados(ticker, weekly_max=False):
    period_w = "max" if weekly_max else "5y"
    df_d = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
    df_w = yf.download(ticker, period=period_w, interval="1wk", progress=False, auto_adjust=True)
    df_d = df_d.dropna(how='all').ffill()
    df_w = df_w.dropna(how='all').ffill()
    return df_d, df_w

def adicionar_indicadores(df):
    if len(df) < 10 or 'Close' not in df.columns:
        return df
    df = df.copy()
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
    df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
    
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['BB_Mid'] = df['Close'].rolling(20).mean()
    df['BB_Std'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
    df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
    
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14, min_periods=1).mean()
    df['Vol_Avg'] = df['Volume'].rolling(20, min_periods=1).mean()
    return df

def detectar_padroes_candle(df):
    if len(df) < 3: return ["⚪ Dados insuficientes"]
    c = df['Close'].iloc[-1]
    o = df['Open'].iloc[-1]
    h = df['High'].iloc[-1]
    l = df['Low'].iloc[-1]
    prev_c = df['Close'].iloc[-2]
    prev_o = df['Open'].iloc[-2]
    body = abs(c - o)
    range_c = h - l
    if range_c == 0: return ["⚪ Candle indefinido"]
    upper_wick = (h - max(o, c)) / range_c
    lower_wick = (min(o, c) - l) / range_c
    body_ratio = body / range_c
    patterns = []
    if body_ratio < 0.1: patterns.append("🔴 Doji")
    if body_ratio > 0.85:
        patterns.append("🟢 Marubozu Bullish" if c > o else "🔴 Marubozu Bearish")
    if lower_wick > 0.6 and upper_wick < 0.15 and body_ratio < 0.35:
        patterns.append("🟢 Hammer" if c > o else "🔴 Hanging Man")
    if upper_wick > 0.6 and lower_wick < 0.15 and body_ratio < 0.35:
        patterns.append("🟢 Inverted Hammer" if c > o else "🔴 Shooting Star")
    return patterns if patterns else ["⚪ Neutro"]

def get_weekly_score(df_w):
    semanas = len(df_w)
    if semanas < 52:
        return 0, f"📉 Muito curto ({semanas} semanas)"
    close = df_w['Close'].iloc[-1]
    sma200 = df_w['SMA200'].iloc[-1] if 'SMA200' in df_w.columns else np.nan
    sma50 = df_w['SMA50'].iloc[-1] if 'SMA50' in df_w.columns else np.nan
    if pd.isna(sma200):
        if pd.notna(sma50):
            score = 1 if close > sma50 else -1
            return score, "🟡 Usando SMA50"
        return 0, "📉 Sem médias"
    if close > sma200:
        score = 2 if pd.notna(sma50) and sma50 > sma200 else 1
        return score, "🟢 Forte Alta"
    else:
        score = -2 if pd.notna(sma50) and sma50 < sma200 else -1
        return score, "🔴 Forte Baixa"

# ====================== INTERFACE ======================
tab1, tab2 = st.tabs(["📊 Analisador Individual", "🔍 Scanner de Mercado"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Digite o ticker (ex: NVDA, WMT, T, LUV, AAPL)", "NVDA").strip().upper()
    with col2:
        if st.button("🚀 ANALISAR TICKER", type="primary", use_container_width=True):
            with st.spinner(f"Analisando {ticker}..."):
                try:
                    df_daily, df_weekly = baixar_dados(ticker, weekly_max=True)
                    if df_daily.empty or len(df_daily) < 20:
                        st.error("❌ Sem dados suficientes.")
                        st.stop()

                    df_daily = adicionar_indicadores(df_daily)
                    df_weekly = adicionar_indicadores(df_weekly)

                    w_score, w_trend = get_weekly_score(df_weekly)

                    # TODOS OS VALORES COMO ESCALAR (anti-Series error)
                    close = df_daily['Close'].iloc[-1]
                    rsi = df_daily['RSI'].iloc[-1] if 'RSI' in df_daily.columns else np.nan
                    macd_hist = df_daily['MACD_Hist'].iloc[-1] if 'MACD_Hist' in df_daily.columns else np.nan
                    macd = df_daily['MACD'].iloc[-1] if 'MACD' in df_daily.columns else np.nan
                    macd_signal = df_daily['MACD_Signal'].iloc[-1] if 'MACD_Signal' in df_daily.columns else np.nan
                    ema9 = df_daily['EMA9'].iloc[-1] if 'EMA9' in df_daily.columns else np.nan
                    ema20 = df_daily['EMA20'].iloc[-1] if 'EMA20' in df_daily.columns else np.nan
                    atr = df_daily['ATR'].iloc[-1] if 'ATR' in df_daily.columns else np.nan

                    d_score = 0.0
                    if pd.notna(macd_hist):
                        if macd_hist > 0 and macd > macd_signal:
                            d_score += 1.5
                        elif macd_hist < 0 and macd < macd_signal:
                            d_score -= 1.5
                    if pd.notna(rsi) and 35 <= rsi <= 55:
                        d_score += 1.0
                    if pd.notna(ema9) and close > ema9:
                        d_score += 0.8
                    if pd.notna(ema20) and close > ema20:
                        d_score += 0.5

                    total_score = w_score + d_score

                    if total_score >= 3.5: sinal, action = "🟢 **FORTE COMPRA**", "ENTRADA LONG"
                    elif total_score >= 1.5: sinal, action = "🟡 COMPRA moderada", "ENTRADA LONG"
                    elif total_score <= -3.5: sinal, action = "🔴 **FORTE VENDA**", "ENTRADA SHORT"
                    elif total_score <= -1.5: sinal, action = "🟠 VENDA moderada", "ENTRADA SHORT"
                    else: sinal, action = "⚪ NEUTRO", "Sem entrada"

                    st.subheader("📅 Análise Semanal")
                    st.write(f"**Tendência:** {w_trend}")
                    st.write(f"**Semanas de dados:** {len(df_weekly)}")
                    st.write(f"**Score Semanal:** {w_score}")

                    col_a, col_b, col_c = st.columns(3)
                    with col_a: st.metric("Score Total", f"{total_score:.1f}/6")
                    with col_b: st.metric("Preço Atual", f"${close:.2f}")
                    with col_c: st.metric("RSI", f"{rsi:.1f}" if pd.notna(rsi) else "—")

                    st.success(sinal)
                    st.info(f"**Ação recomendada:** {action}")

                    st.write("**Padrão de Candle:**")
                    for p in detectar_padroes_candle(df_daily):
                        st.write("•", p)

                    st.subheader("📈 Gráfico Diário (180 dias)")
                    df_plot = df_daily.tail(180)
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                                                 low=df_plot['Low'], close=df_plot['Close']))
                    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot.get('EMA9'), name="EMA 9", line=dict(color="magenta", width=2)))
                    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot.get('EMA20'), name="EMA 20", line=dict(color="orange", width=2)))
                    fig.update_layout(height=650, template="plotly_dark", xaxis_rangeslider_visible=False,
                                      title=f"{ticker} - Últimos 180 dias")
                    st.plotly_chart(fig, use_container_width=True)

                    if pd.notna(atr):
                        if "LONG" in action:
                            sl = close - 1.5 * atr
                            tp = close + 3.0 * atr
                        else:
                            sl = close + 1.5 * atr
                            tp = close - 3.0 * atr
                        st.write(f"**Stop Loss:** ${sl:.2f} | **Take Profit:** ${tp:.2f} (RR ≈ 2:1)")

                except Exception as e:
                    st.error(f"Erro: {str(e)}")
                    st.info("Atualiza a página (F5)")

# Scanner mantido simples (mesma proteção)
with tab2:
    st.subheader("🔍 Scanner Completo")
    market = st.selectbox("Escolha o índice", ["S&P 500 (503 ações)", "NASDAQ-100 (101 ações)"])
    if st.button("🚀 EXECUTAR SCANNER COMPLETO", type="primary"):
        st.info("Scanner completo em breve (versão individual já está fixa).")

st.caption("⚠️ Ferramenta técnica apenas • Nunca é recomendação de investimento")