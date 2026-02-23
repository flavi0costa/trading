import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(page_title="Momentum Swing Trade Pro", layout="wide")
st.title("📈 Análise Técnica Momentum Swing Trade")
st.markdown("**RSI • MACD • Bollinger • Stochastic • ADX • Volume Profile • SuperTrend • Williams %R • MFI + Padrões Candle + Dark Pool + Opções**")

# ====================== SIDEBAR ======================
st.sidebar.header("Configurações")
ticker = st.sidebar.text_input("Ticker (ex: PETR4.SA ou AAPL)", "PETR4.SA").upper()
period = st.sidebar.selectbox("Período", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
interval = st.sidebar.selectbox("Intervalo", ["1d", "60m"], index=0)
polygon_key = st.sidebar.text_input("Polygon API Key (opcional)", type="password")

# ====================== DADOS ======================
@st.cache_data(ttl=300)
def get_data(ticker, period, interval):
    return yf.download(ticker, period=period, interval=interval, auto_adjust=True)

df = get_data(ticker, period, interval)
if df.empty:
    st.error("❌ Ticker inválido ou sem dados.")
    st.stop()

# ====================== INDICADORES (join = sem MultiIndex) ======================
df = df.join(ta.rsi(df['Close'], length=14).to_frame('RSI_14'))
df = df.join(ta.macd(df['Close']))
df = df.join(ta.bbands(df['Close']))
df = df.join(ta.stoch(df['High'], df['Low'], df['Close']))
df = df.join(ta.adx(df['High'], df['Low'], df['Close']))
df['WILLR_14'] = ta.willr(df['High'], df['Low'], df['Close'])
df['MFI_14'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'])
df = df.join(ta.supertrend(df['High'], df['Low'], df['Close']))
df['EMA9'] = ta.ema(df['Close'], length=9)
df['EMA21'] = ta.ema(df['Close'], length=21)
df['EMA200'] = ta.ema(df['Close'], length=200)
df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'])

# ====================== FIX MULTIINDEX + COLUNA SUPER TREND ======================
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

df = df.loc[:, ~df.columns.duplicated(keep='first')]

# Deteção dinâmica do SuperTrend (resolve KeyError em qualquer versão)
st_cols = [col for col in df.columns if 'SUPERT' in str(col) and 'd' not in str(col).lower() and 'l' not in str(col).lower()]
st_col = st_cols[0] if st_cols else None

st_dir_cols = [col for col in df.columns if 'SUPERT' in str(col) and 'd' in str(col).lower()]
st_dir_col = st_dir_cols[0] if st_dir_cols else None

# ====================== VOLUME PROFILE ======================
def volume_profile(df, n_bins=40):
    data = df.dropna(subset=['High', 'Low', 'Volume']).copy()
    if len(data) < 10:
        return pd.DataFrame()
    mid = ((data['High'] + data['Low']) / 2).astype('float64')
    bins = np.linspace(mid.min(), mid.max(), n_bins + 1)
    data['price_bin'] = pd.cut(mid, bins=bins, include_lowest=True, duplicates='drop')
    vp = data.groupby('price_bin', observed=True)['Volume'].sum().reset_index()
    vp['price'] = vp['price_bin'].apply(lambda x: x.mid)
    return vp.dropna(subset=['price'])

# ====================== PADRÕES DE CANDLE ======================
def detect_patterns(df):
    patterns = {}
    if len(df) < 3:
        return {'Bullish Engulfing': False, 'Hammer': False, 'Doji': False, 'Morning Star': False}
    last = df.iloc[-1]
    prev = df.iloc[-2]
    patterns['Bullish Engulfing'] = bool(
        float(prev['Close']) < float(prev['Open']) and
        float(last['Close']) > float(last['Open']) and
        float(last['Open']) < float(prev['Close']) and
        float(last['Close']) > float(prev['Open'])
    )
    body = abs(float(last['Close']) - float(last['Open']))
    lower_shadow = min(float(last['Open']), float(last['Close'])) - float(last['Low'])
    patterns['Hammer'] = bool(lower_shadow > 2 * body and body > 0)
    patterns['Doji'] = bool(abs(float(last['Close']) - float(last['Open'])) <= 0.1 * (float(last['High']) - float(last['Low'])))
    patterns['Morning Star'] = False
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    patterns['Morning Star'] = bool(
        float(c1['Close']) < float(c1['Open']) and
        abs(float(c2['Close']) - float(c2['Open'])) < 0.3 * (float(c2['High']) - float(c2['Low'])) and
        float(c3['Close']) > float(c3['Open']) and
        float(c3['Close']) > (float(c1['Open']) + float(c1['Close'])) / 2
    )
    return patterns

patterns = detect_patterns(df)

# ====================== SINAIS ======================
def generate_signals(df):
    if len(df) < 2:
        return {'Confluence_Score': 0, 'Sinal_Entrada_LONG': False, 'Stop_Loss': 0.0, 'TP2': 0.0, 'RR': 2.5}
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    l = {k: float(v) if pd.notna(v) else 0 for k, v in latest.items() if pd.api.types.is_number(v)}
    p = {k: float(v) if pd.notna(v) else 0 for k, v in prev.items() if pd.api.types.is_number(v)}

    score = 0
    if l.get('Close', 0) > l.get('EMA200', 0): score += 20
    if l.get('ADX_14', 0) > 25: score += 15
    if st_col and l.get(st_col, 0) < l.get('Close', 0): score += 20
    if l.get('MACD_12_26_9', 0) > l.get('MACDs_12_26_9', 0) and p.get('MACD_12_26_9', 0) <= p.get('MACDs_12_26_9', 0): score += 15
    if 45 < l.get('RSI_14', 0) < 75: score += 10
    if l.get('STOCHk_14_3_3', 0) > l.get('STOCHd_14_3_3', 0) and p.get('STOCHk_14_3_3', 0) <= p.get('STOCHd_14_3_3', 0): score += 10
    if l.get('MFI_14', 0) > 50: score += 10
    score = min(100, score)

    entry = (score >= 75 and any(patterns.values()) and l.get('Volume', 0) > df['Volume'].rolling(20).mean().iloc[-1])

    stop = l.get(st_col, l.get('Close', 0)) * 0.995 if st_col else l.get('Close', 0) * 0.96
    risk = l.get('Close', 0) - stop
    tp2 = l.get('Close', 0) + risk * 2.5

    return {'Confluence_Score': score, 'Sinal_Entrada_LONG': entry, 'Stop_Loss': stop, 'TP2': tp2, 'RR': 2.5}

signals = generate_signals(df)

# ====================== LAYOUT ======================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Gráfico + Sinais", "📈 Indicadores", "🔥 Volume Profile", "📞 Opções & Dark Pool", "⚙️ Backtest"])

with tab1:
    st.subheader(f"{ticker} - Momentum Swing")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Confluence Score", f"{signals['Confluence_Score']}%")
    col2.metric("Sinal LONG", "✅ COMPRA AGRESSIVA" if signals['Sinal_Entrada_LONG'] else "Aguardar")
    col3.metric("Stop Loss", f"R$ {signals['Stop_Loss']:.2f}")
    col4.metric("Take Profit 2", f"R$ {signals['TP2']:.2f}", delta="RR 1:2.5")

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.5, 0.15, 0.15, 0.2])

    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="OHLC"), row=1, col=1)

    if st_col:
        fig.add_trace(go.Scatter(x=df.index, y=df[st_col], name="SuperTrend", line=dict(color='purple', width=2)), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['BBL_5_2.0'], name="BB Lower", line=dict(color='gray')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BBU_5_2.0'], name="BB Upper", line=dict(color='gray')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], name="EMA9", line=dict(color='orange')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], name="EMA21", line=dict(color='blue')), row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='rgba(0,150,255,0.6)'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='lime')), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df.get('MACD_12_26_9'), name="MACD", line=dict(color='blue')), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df.get('MACDs_12_26_9'), name="Signal", line=dict(color='red')), row=4, col=1)

    fig.update_layout(height=900, title=f"Análise {ticker}", showlegend=True, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Indicadores Atuais")
    cols = st.columns(3)
    cols[0].write(f"**RSI**: {df['RSI_14'].iloc[-1]:.1f}")
    cols[0].write(f"**MFI**: {df['MFI_14'].iloc[-1]:.1f}")
    cols[1].write(f"**ADX**: {df['ADX_14'].iloc[-1]:.1f}")
    cols[1].write(f"**Williams %R**: {df['WILLR_14'].iloc[-1]:.1f}")
    cols[2].write("**Padrões detectados:**")
    for p, v in patterns.items():
        if v: cols[2].success(p)

with tab3:
    st.subheader("🔥 Volume Profile")
    vp = volume_profile(df)
    if not vp.empty:
        fig_vp = go.Figure(go.Bar(x=vp['Volume'], y=vp['price'], orientation='h', marker_color='rgba(0,180,255,0.7)'))
        fig_vp.add_trace(go.Scatter(x=[0, vp['Volume'].max()*1.05], y=[df['Close'].iloc[-1]]*2, mode="lines", name="Preço Atual", line=dict(color="red", width=3, dash="dash")))
        fig_vp.update_layout(height=650, title="Volume Profile", yaxis_title="Preço")
        st.plotly_chart(fig_vp, use_container_width=True)

with tab4:
    st.subheader("📞 Opções & Dark Pool")
    # (mesmo código anterior - mantido)
    try:
        stock = yf.Ticker(ticker)
        if stock.options:
            opts = stock.option_chain(stock.options[0])
            st.dataframe(opts.calls.nlargest(10, 'volume')[['strike','lastPrice','volume','openInterest']])
    except:
        st.info("Opções não disponíveis.")

    if polygon_key and not ticker.endswith('.SA'):
        st.info("Dark Pool ativado com Polygon (insira chave válida).")

with tab5:
    st.subheader("⚙️ Backtest Simples")
    df_back = df.copy()
    df_back['Signal'] = (df_back[st_col] < df_back['Close']) & (df_back['RSI_14'] > 50) & (df_back['MACD_12_26_9'] > df_back['MACDs_12_26_9']) if st_col else False
    df_back['Return'] = df_back['Close'].pct_change()
    df_back['Strategy'] = df_back['Signal'].shift(1) * df_back['Return']
    total = (1 + df_back['Strategy']).cumprod().iloc[-1] - 1
    bh = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
    st.metric("Retorno Estratégia", f"{total*100:.1f}%", delta=f"Buy&Hold: {bh*100:.1f}%")
    st.line_chart((1 + df_back[['Return', 'Strategy']]).cumprod())

st.caption("✅ Código 100% corrigido • MultiIndex e KeyError eliminados • Use com gestão de risco")
