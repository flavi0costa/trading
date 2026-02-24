import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Momentum Swing Dashboard", layout="wide")
st.title("🔥 Momentum Swing Dashboard - US Market")
st.markdown("**Análise individual + Scanner S&P500 / NASDAQ-100 • 100% estável**")

# ====================== FUNÇÕES ======================
@st.cache_data(ttl=3600)
def baixar_dados(ticker):
    df_d = yf.download(ticker, period="1y", interval="1d", progress=False)
    df_w = yf.download(ticker, period="5y", interval="1wk", progress=False)
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
    if len(df) < 3:
        return ["⚪ Dados insuficientes"]
    row = df.iloc[-1]
    prev = df.iloc[-2]
    body = abs(row['Close'] - row['Open'])
    range_c = row['High'] - row['Low']
    if range_c == 0:
        return ["⚪ Candle indefinido"]
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
    if patterns:
        return patterns
    return ["⚪ Neutro"]

def get_weekly_score(last_w):
    if len(last_w) == 0 or pd.isna(last_w.get('SMA_200')) or pd.isna(last_w.get('Close')):
        return 0, "📉 Histórico curto"
    close = last_w.get('Close')
    sma200 = last_w.get('SMA_200')
    sma50 = last_w.get('SMA_50')
    if close > sma200:
        return (2, "🟢 Forte Alta") if pd.notna(sma50) and sma50 > sma200 else (1, "🟢 Alta")
    else:
        return (-2, "🔴 Forte Baixa") if pd.notna(sma50) and sma50 < sma200 else (-1, "🔴 Baixa")

# ====================== TICKERS ======================
def get_sp500_tickers():
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        for t in tables:
            if 'Symbol' in t.columns:
                return [sym.replace('.', '-') for sym in t['Symbol'].tolist() if sym]
    except:
        pass
    return ["AAPL", "MSFT", "NVDA"]

def get_nasdaq100_tickers():
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/NASDAQ-100")
        for t in tables:
            if 'Ticker' in t.columns:
                return [sym.replace('.', '-') for sym in t['Ticker'].tolist() if sym]
    except:
        pass
    return ["AAPL", "MSFT", "NVDA"]

# ====================== INTERFACE ======================
tab1, tab2 = st.tabs(["📊 Analisador Individual", "🔍 Scanner de Mercado"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Digite o ticker (ex: AAPL, TSLA, NVDA, AMZN)", "AAPL").strip().upper()
    with col2:
        if st.button("🚀 ANALISAR TICKER", type="primary", use_container_width=True):
            with st.spinner(f"Analisando {ticker}..."):
                try:
                    df_daily, df_weekly = baixar_dados(ticker)
                    if df_daily.empty or len(df_daily) < 30:
                        st.error("❌ Ticker sem dados suficientes.")
                        st.stop()

                    df_daily = adicionar_indicadores(df_daily)
                    df_weekly = adicionar_indicadores(df_weekly)
                    last_d = df_daily.iloc[-1]
                    last_w = df_weekly.iloc[-1]

                    w_score, w_trend = get_weekly_score(last_w.to_dict())

                    # === SCORE DIÁRIO SUPER SEGURO ===
                    d_score = 0.0
                    ld = last_d.to_dict()

                    macd_hist = ld.get('MACD_Hist')
                    if isinstance(macd_hist, (int, float)) and pd.notna(macd_hist):
                        macd = ld.get('MACD', 0)
                        signal = ld.get('MACD_Signal', 0)
                        if macd_hist > 0 and macd > signal:
                            d_score += 1.5
                        elif macd_hist < 0 and macd < signal:
                            d_score -= 1.5

                    rsi = ld.get('RSI')
                    if isinstance(rsi, (int, float)) and pd.notna(rsi) and 35 <= rsi <= 55:
                        d_score += 1.0

                    close = ld.get('Close', 0)
                    ema9 = ld.get('EMA9')
                    if isinstance(ema9, (int, float)) and pd.notna(ema9) and close > ema9:
                        d_score += 0.8

                    ema20 = ld.get('EMA20')
                    if isinstance(ema20, (int, float)) and pd.notna(ema20) and close > ema20:
                        d_score += 0.5

                    total_score = w_score + d_score

                    # Sinal
                    if total_score >= 3.5: sinal, action = "🟢 **FORTE COMPRA**", "ENTRADA LONG"
                    elif total_score >= 1.5: sinal, action = "🟡 COMPRA moderada", "ENTRADA LONG"
                    elif total_score <= -3.5: sinal, action = "🔴 **FORTE VENDA**", "ENTRADA SHORT"
                    elif total_score <= -1.5: sinal, action = "🟠 VENDA moderada", "ENTRADA SHORT"
                    else: sinal, action = "⚪ NEUTRO", "Sem entrada"

                    st.subheader("📅 Análise Semanal")
                    st.write(f"**Tendência:** {w_trend} | Score: {w_score}")

                    col_a, col_b, col_c = st.columns(3)
                    with col_a: st.metric("Score Total", f"{total_score:.1f}/6")
                    with col_b: st.metric("Preço Atual", f"${ld.get('Close', 0):.2f}")
                    with col_c: st.metric("RSI", f"{ld.get('RSI', 50):.1f}")

                    st.success(sinal)
                    st.info(f"**Ação recomendada:** {action}")

                    st.write("**Padrão de Candle:**")
                    for p in detectar_padroes_candle(df_daily):
                        st.write("•", p)

                    # Gráfico
                    st.subheader("📈 Gráfico Diário")
                    df_plot = df_daily.tail(180)
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                                                 low=df_plot['Low'], close=df_plot['Close']))
                    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot.get('EMA9'), name="EMA 9", line=dict(color="magenta", width=2)))
                    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot.get('EMA20'), name="EMA 20", line=dict(color="orange", width=2)))
                    fig.update_layout(height=650, template="plotly_dark", xaxis_rangeslider_visible=False,
                                      title=f"{ticker} - Últimos 180 dias")
                    st.plotly_chart(fig, use_container_width=True)

                    # Risco
                    atr = ld.get('ATR', 0)
                    if "LONG" in action:
                        sl = close - 1.5 * atr
                        tp = close + 3.0 * atr
                        st.write(f"**Stop Loss:** ${sl:.2f} | **Take Profit:** ${tp:.2f} (RR 2:1)")
                except Exception as e:
                    st.error(f"Erro ao analisar {ticker}: {str(e)}")
                    st.info("Tente outro ticker ou atualize a página.")

with tab2:
    st.subheader("🔍 Scanner Completo")
    market = st.selectbox("Escolha o índice", ["S&P 500 (503 ações)", "NASDAQ-100 (101 ações)"])
    
    if st.button("🚀 EXECUTAR SCANNER COMPLETO", type="primary"):
        with st.spinner("Analisando todos os tickers... (1-4 minutos na primeira vez)"):
            tickers = get_sp500_tickers() if "S&P" in market else get_nasdaq100_tickers()
            results = []
            progress = st.progress(0)
            total = len(tickers)

            for i, t in enumerate(tickers):
                try:
                    df_d, df_w = baixar_dados(t)
                    if len(df_d) < 50: 
                        progress.progress((i+1)/total)
                        continue
                    df_d = adicionar_indicadores(df_d)
                    df_w = adicionar_indicadores(df_w)
                    last_d = df_d.iloc[-1]
                    last_w = df_w.iloc[-1]

                    w_score, w_trend = get_weekly_score(last_w.to_dict())
                    d_score = 0.0
                    ld = last_d.to_dict()

                    macd_hist = ld.get('MACD_Hist')
                    if isinstance(macd_hist, (int, float)) and pd.notna(macd_hist):
                        if macd_hist > 0 and ld.get('MACD', 0) > ld.get('MACD_Signal', 0):
                            d_score += 1.5
                        elif macd_hist < 0 and ld.get('MACD', 0) < ld.get('MACD_Signal', 0):
                            d_score -= 1.5

                    rsi = ld.get('RSI')
                    if isinstance(rsi, (int, float)) and pd.notna(rsi) and 35 <= rsi <= 55:
                        d_score += 1.0

                    close = ld.get('Close', 0)
                    if isinstance(ld.get('EMA9'), (int, float)) and pd.notna(ld.get('EMA9')) and close > ld.get('EMA9'):
                        d_score += 0.8
                    if isinstance(ld.get('EMA20'), (int, float)) and pd.notna(ld.get('EMA20')) and close > ld.get('EMA20'):
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
                        "Preço": round(close, 2),
                        "RSI": round(ld.get('RSI', 50), 1),
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
                st.warning("Nenhum ticker válido encontrado.")

st.caption("⚠️ Apenas ferramenta técnica. Nunca é recomendação de investimento.")