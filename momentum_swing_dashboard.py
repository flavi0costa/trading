import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Momentum Swing Dashboard", layout="wide")
st.title("🔥 Momentum Swing Dashboard - US Market")
st.markdown("**VERSÃO DEFINITIVA • Erro 'truth value of a Series' ELIMINADO**")

# ====================== FUNÇÕES ======================
@st.cache_data(ttl=3600)
def baixar_dados(ticker, weekly_max=False):
    df_d = yf.download(ticker, period="1y", interval="1d", progress=False)
    period_w = "max" if weekly_max else "5y"
    df_w = yf.download(ticker, period=period_w, interval="1wk", progress=False)
    return df_d, df_w

def adicionar_indicadores(df):
    if len(df) < 10:
        return df
    df = df.copy()
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    
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
    
    tr = pd.concat([df['High']-df['Low'], 
                    (df['High']-df['Close'].shift()).abs(), 
                    (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    return df

def detectar_padroes_candle(df):
    if len(df) < 3: return ["⚪ Dados insuficientes"]
    row = df.iloc[-1]
    prev = df.iloc[-2]
    body = abs(row['Close'] - row['Open'])
    range_c = row['High'] - row['Low']
    if range_c == 0: return ["⚪ Candle indefinido"]
    upper_wick = (row['High'] - max(row['Open'], row['Close'])) / range_c
    lower_wick = (min(row['Open'], row['Close']) - row['Low']) / range_c
    body_ratio = body / range_c
    patterns = []
    if body_ratio < 0.1: patterns.append("🔴 Doji")
    if body_ratio > 0.85:
        patterns.append("🟢 Marubozu Bullish" if row['Close'] > row['Open'] else "🔴 Marubozu Bearish")
    if lower_wick > 0.6 and upper_wick < 0.15 and body_ratio < 0.35:
        patterns.append("🟢 Hammer" if row['Close'] > row['Open'] else "🔴 Hanging Man")
    if upper_wick > 0.6 and lower_wick < 0.15 and body_ratio < 0.35:
        patterns.append("🟢 Inverted Hammer" if row['Close'] > row['Open'] else "🔴 Shooting Star")
    return patterns if patterns else ["⚪ Neutro"]

def get_weekly_score(df_w, last_w_dict):
    semanas = len(df_w)
    if semanas < 52:
        return 0, f"📉 Muito curto ({semanas} semanas)"
    
    close = last_w_dict.get('Close', np.nan)
    sma200 = last_w_dict.get('SMA_200', np.nan)
    sma50 = last_w_dict.get('SMA_50', np.nan)
    
    if pd.isna(sma200):
        if pd.notna(sma50):
            score = 1 if close > sma50 else -1
            return score, "🟡 SMA200 indisponível (usando SMA50)"
        return 0, "📉 Sem médias longas"
    
    if close > sma200:
        score = 2 if pd.notna(sma50) and sma50 > sma200 else 1
        return score, "🟢 Forte Alta"
    else:
        score = -2 if pd.notna(sma50) and sma50 < sma200 else -1
        return score, "🔴 Forte Baixa"

# ====================== TICKERS ======================
def get_sp500_tickers():
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        for t in tables:
            if 'Symbol' in t.columns:
                return [sym.replace('.', '-') for sym in t['Symbol'].tolist() if sym]
    except: pass
    return ["AAPL", "MSFT", "NVDA"]

def get_nasdaq100_tickers():
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/NASDAQ-100")
        for t in tables:
            if 'Ticker' in t.columns:
                return [sym.replace('.', '-') for sym in t['Ticker'].tolist() if sym]
    except: pass
    return ["AAPL", "MSFT", "NVDA"]

# ====================== INTERFACE ======================
tab1, tab2 = st.tabs(["📊 Analisador Individual", "🔍 Scanner de Mercado"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Digite o ticker (ex: T, WMT, LUV, AAPL, NVDA)", "WMT").strip().upper()
    with col2:
        if st.button("🚀 ANALISAR TICKER", type="primary", use_container_width=True):
            with st.spinner(f"Analisando {ticker}..."):
                try:
                    df_daily, df_weekly = baixar_dados(ticker, weekly_max=True)
                    
                    if df_daily.empty or len(df_daily) < 30:
                        st.error("❌ Ticker sem dados suficientes.")
                        st.stop()

                    df_daily = adicionar_indicadores(df_daily)
                    df_weekly = adicionar_indicadores(df_weekly)
                    
                    last_d = df_daily.iloc[-1]
                    last_w = df_weekly.iloc[-1]
                    last_d_dict = last_d.to_dict()      # ← FORÇA ESCALAR
                    last_w_dict = last_w.to_dict()      # ← FORÇA ESCALAR

                    w_score, w_trend = get_weekly_score(df_weekly, last_w_dict)

                    # SCORE DIÁRIO 100% SEGURO
                    d_score = 0.0
                    close = last_d_dict.get('Close', np.nan)
                    rsi = last_d_dict.get('RSI', np.nan)
                    macd_hist = last_d_dict.get('MACD_Hist', np.nan)
                    macd = last_d_dict.get('MACD', np.nan)
                    macd_signal = last_d_dict.get('MACD_Signal', np.nan)
                    ema9 = last_d_dict.get('EMA9', np.nan)
                    ema20 = last_d_dict.get('EMA20', np.nan)
                    atr = last_d_dict.get('ATR', np.nan)

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
                    with col_b: st.metric("Preço Atual", f"${close:.2f}" if pd.notna(close) else "—")
                    with col_c: st.metric("RSI", f"{rsi:.1f}" if pd.notna(rsi) else "—")

                    st.success(sinal)
                    st.info(f"**Ação recomendada:** {action}")

                    st.write("**Padrão de Candle (último dia):**")
                    for p in detectar_padroes_candle(df_daily):
                        st.write("•", p)

                    st.subheader("📈 Gráfico Diário (180 dias)")
                    df_plot = df_daily.tail(180)
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                                                 low=df_plot['Low'], close=df_plot['Close']))
                    if 'EMA9' in df_plot.columns:
                        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA9'], name="EMA 9", line=dict(color="magenta", width=2)))
                    if 'EMA20' in df_plot.columns:
                        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA20'], name="EMA 20", line=dict(color="orange", width=2)))
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
                    st.error(f"Erro inesperado: {str(e)}")
                    st.info("Atualiza a página ou tenta outro ticker.")

# ====================== SCANNER (igual com to_dict) ======================
with tab2:
    st.subheader("🔍 Scanner Completo")
    market = st.selectbox("Escolha o índice", ["S&P 500 (503 ações)", "NASDAQ-100 (101 ações)"])
    
    if st.button("🚀 EXECUTAR SCANNER COMPLETO", type="primary"):
        with st.spinner("Analisando todos os tickers..."):
            tickers = get_sp500_tickers() if "S&P" in market else get_nasdaq100_tickers()
            results = []
            progress = st.progress(0)
            total = len(tickers)

            for i, t in enumerate(tickers):
                try:
                    df_d, df_w = baixar_dados(t, weekly_max=False)
                    if len(df_d) < 50:
                        progress.progress((i+1)/total)
                        continue
                    df_d = adicionar_indicadores(df_d)
                    df_w = adicionar_indicadores(df_w)
                    last_d = df_d.iloc[-1]
                    last_w = df_w.iloc[-1]
                    last_d_dict = last_d.to_dict()
                    last_w_dict = last_w.to_dict()

                    w_score, w_trend = get_weekly_score(df_w, last_w_dict)
                    
                    d_score = 0.0
                    close = last_d_dict.get('Close', np.nan)
                    rsi = last_d_dict.get('RSI', np.nan)
                    macd_hist = last_d_dict.get('MACD_Hist', np.nan)
                    macd = last_d_dict.get('MACD', np.nan)
                    macd_signal = last_d_dict.get('MACD_Signal', np.nan)
                    ema9 = last_d_dict.get('EMA9', np.nan)
                    ema20 = last_d_dict.get('EMA20', np.nan)

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
                    if total_score >= 3.5: sinal = "🟢 FORTE LONG"
                    elif total_score >= 1.5: sinal = "🟡 LONG"
                    elif total_score <= -3.5: sinal = "🔴 FORTE SHORT"
                    elif total_score <= -1.5: sinal = "🟠 SHORT"
                    else: sinal = "⚪ NEUTRO"

                    results.append({
                        "Ticker": t,
                        "Score": round(total_score, 1),
                        "Sinal": sinal,
                        "Preço": round(close, 2) if pd.notna(close) else 0,
                        "RSI": round(rsi, 1) if pd.notna(rsi) else 50,
                        "Tendência Semanal": w_trend,
                        "Candle": detectar_padroes_candle(df_d)[0][:30]
                    })
                except:
                    pass
                progress.progress((i+1)/total)

            if results:
                df_res = pd.DataFrame(results).sort_values("Score", ascending=False)
                st.success(f"✅ {len(results)} tickers analisados!")
                st.dataframe(df_res, use_container_width=True, height=800)
                st.download_button("📥 Baixar CSV", df_res.to_csv(index=False), f"scanner_{market.split()[0]}.csv")
            else:
                st.warning("Nenhum ticker retornou dados válidos.")

st.caption("⚠️ Ferramenta técnica apenas • Nunca é recomendação de investimento")