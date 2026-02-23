import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Momentum Swing Trade Pro", layout="wide")
st.title("📈 Análise Técnica Momentum Swing Trade")
st.markdown("**Todos os indicadores + Dark Pool + Opções + Lógica de Entrada/Saída**")

# ====================== SIDEBAR ======================
st.sidebar.header("Configurações")
ticker = st.sidebar.text_input("Ticker (ex: PETR4.SA ou AAPL)", "PETR4.SA").upper()
period = st.sidebar.selectbox("Período", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
interval = st.sidebar.selectbox("Intervalo", ["1d", "60m"], index=0)

# Chave Polygon (opcional para Dark Pool + US)
polygon_key = st.sidebar.text_input("Polygon API Key (opcional - grátis em polygon.io)", type="password")

# ====================== BAIXAR DADOS ======================
@st.cache_data(ttl=300)
def get_data(ticker, period, interval):
    return yf.download(ticker, period=period, interval=interval, auto_adjust=True)

df = get_data(ticker, period, interval)
if df.empty:
    st.error("Ticker inválido ou sem dados.")
    st.stop()

# ====================== CÁLCULO DE INDICADORES ======================
df['RSI'] = ta.rsi(df['Close'], length=14)
macd = ta.macd(df['Close'])
df = pd.concat([df, macd], axis=1)
bb = ta.bbands(df['Close'])
df = pd.concat([df, bb], axis=1)
stoch = ta.stoch(df['High'], df['Low'], df['Close'])
df = pd.concat([df, stoch], axis=1)
adx = ta.adx(df['High'], df['Low'], df['Close'])
df = pd.concat([df, adx], axis=1)
df['WILLR'] = ta.willr(df['High'], df['Low'], df['Close'])
df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'])
supertrend = ta.supertrend(df['High'], df['Low'], df['Close'])
df = pd.concat([df, supertrend], axis=1)
df['EMA9'] = ta.ema(df['Close'], length=9)
df['EMA21'] = ta.ema(df['Close'], length=21)
df['EMA200'] = ta.ema(df['Close'], length=200)
df['OBV'] = ta.obv(df['Close'], df['Volume'])
df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

# ====================== VOLUME PROFILE ======================
def volume_profile(df, n_bins=40):
    price_min, price_max = df['Low'].min(), df['High'].max()
    bins = np.linspace(price_min, price_max, n_bins)
    df['price_bin'] = pd.cut((df['High'] + df['Low']) / 2, bins=bins, include_lowest=True)
    vp = df.groupby('price_bin')['Volume'].sum().reset_index()
    vp['price'] = vp['price_bin'].apply(lambda x: x.mid)
    return vp

vp = volume_profile(df)

# ====================== PADRÕES DE CANDLE (simples e eficazes) ======================
def detect_patterns(df):
    patterns = {}
    # Bullish Engulfing
    patterns['Bullish Engulfing'] = ((df['Close'].shift(1) < df['Open'].shift(1)) & 
                                    (df['Close'] > df['Open']) & 
                                    (df['Open'] < df['Close'].shift(1)) & 
                                    (df['Close'] > df['Open'].shift(1))).iloc[-1]
    # Hammer
    body = abs(df['Close'] - df['Open'])
    lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
    patterns['Hammer'] = ((lower_shadow > 2 * body) & (body > 0)).iloc[-1]
    # Doji
    patterns['Doji'] = (abs(df['Close'] - df['Open']) <= 0.1 * (df['High'] - df['Low'])).iloc[-1]
    # Morning Star (últimos 3 candles)
    if len(df) >= 3:
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        patterns['Morning Star'] = ((c1['Close'] < c1['Open']) and 
                                    (abs(c2['Close'] - c2['Open']) < 0.3*(c2['High']-c2['Low'])) and 
                                    (c3['Close'] > c3['Open']) and (c3['Close'] > (c1['Open']+c1['Close'])/2))
    else:
        patterns['Morning Star'] = False
    return patterns

patterns = detect_patterns(df)

# ====================== LÓGICA DE SINAIS MOMENTUM SWING ======================
def generate_signals(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Filtros de tendência forte
    trend_up = latest['Close'] > latest['EMA200']
    adx_strong = latest['ADX_14'] > 25
    super_bull = latest['SUPERT_10_3.0'] < latest['Close']  # SuperTrend verde

    # Momentum
    macd_bull = latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] and prev['MACD_12_26_9'] <= prev['MACDs_12_26_9']
    rsi_ok = 45 < latest['RSI_14'] < 75
    stoch_cross = latest['STOCHk_14_3_3'] > latest['STOCHd_14_3_3'] and prev['STOCHk_14_3_3'] <= prev['STOCHd_14_3_3']
    mfi_bull = latest['MFI_14'] > 50

    # Confluence Score
    score = 0
    if trend_up: score += 20
    if adx_strong: score += 15
    if super_bull: score += 20
    if macd_bull: score += 15
    if rsi_ok: score += 10
    if stoch_cross: score += 10
    if mfi_bull: score += 10
    score = min(100, score)

    # Entrada LONG
    entry = (score >= 75 and 
             any([patterns['Bullish Engulfing'], patterns['Hammer'], patterns['Morning Star']]) and 
             latest['Volume'] > df['Volume'].rolling(20).mean().iloc[-1])

    # Saída / Stop
    stop_loss = latest['SUPERT_10_3.0'] * 0.995 if super_bull else latest['Close'] * 0.96
    risk = latest['Close'] - stop_loss
    take_profit1 = latest['Close'] + risk * 1.5   # 1:1.5
    take_profit2 = latest['Close'] + risk * 2.5   # 1:2.5

    return {
        'Confluence_Score': score,
        'Sinal_Entrada_LONG': entry,
        'Stop_Loss': stop_loss,
        'TP1': take_profit1,
        'TP2': take_profit2,
        'RR': round(2.5, 1)
    }

signals = generate_signals(df)

# ====================== LAYOUT DO APP ======================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Gráfico + Sinais", "📈 Todos os Indicadores", "🔥 Volume Profile", "📞 Opções & Dark Pool", "⚙️ Backtest Simples"])

with tab1:
    st.subheader(f"{ticker} - Momentum Swing Trade")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Confluence Score", f"{signals['Confluence_Score']}%", delta=None)
    col2.metric("Sinal Entrada LONG", "✅ COMPRA AGRESSIVA" if signals['Sinal_Entrada_LONG'] else "Aguardar", 
                delta="Forte" if signals['Sinal_Entrada_LONG'] else None)
    col3.metric("Stop Loss", f"R$ {signals['Stop_Loss']:.2f}")
    col4.metric("Take Profit 2", f"R$ {signals['TP2']:.2f}", delta=f"RR 1:{signals['RR']}")

    # Gráfico principal
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.02, row_heights=[0.5, 0.15, 0.15, 0.2])

    # Candle + overlays
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'], name="OHLC"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SUPERT_10_3.0'], name="SuperTrend", line=dict(color='purple', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BBL_5_2.0'], name="BB Lower", line=dict(color='gray')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BBU_5_2.0'], name="BB Upper", line=dict(color='gray')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], name="EMA9", line=dict(color='orange')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], name="EMA21", line=dict(color='blue')), row=1, col=1)

    # Volume
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='rgba(0,150,255,0.6)'), row=2, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='lime')), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    # MACD
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], name="MACD", line=dict(color='blue')), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], name="Signal", line=dict(color='red')), row=4, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="Histogram", marker_color=np.where(df['MACDh_12_26_9']>0, 'green', 'red')), row=4, col=1)

    fig.update_layout(height=900, title=f"Análise Técnica {ticker}", showlegend=True, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Todos os Indicadores")
    cols = st.columns(3)
    cols[0].write(f"**RSI**: {df['RSI_14'].iloc[-1]:.1f}")
    cols[0].write(f"**MACD**: {df['MACD_12_26_9'].iloc[-1]:.3f}")
    cols[0].write(f"**SuperTrend**: {'Bullish 🟢' if df['SUPERTd_10_3.0'].iloc[-1]==1 else 'Bearish 🔴'}")
    cols[1].write(f"**ADX**: {df['ADX_14'].iloc[-1]:.1f} {'Forte' if df['ADX_14'].iloc[-1]>25 else 'Fraco'}")
    cols[1].write(f"**Stochastic**: {df['STOCHk_14_3_3'].iloc[-1]:.1f}")
    cols[1].write(f"**MFI**: {df['MFI_14'].iloc[-1]:.1f}")
    cols[2].write(f"**Williams %R**: {df['WILLR_14'].iloc[-1]:.1f}")
    cols[2].write("**Padrões detectados hoje:**")
    for p, v in patterns.items():
        if v: cols[2].success(p)

with tab3:
    st.subheader("Volume Profile (últimos 3 meses)")
    fig_vp = go.Figure()
    fig_vp.add_trace(go.Bar(x=vp['Volume'], y=vp['price'], orientation='h', name="Volume"))
    fig_vp.add_trace(go.Scatter(x=[0, vp['Volume'].max()], y=[df['Close'].iloc[-1]]*2, mode="lines", name="Preço Atual", line=dict(color="red", dash="dash")))
    fig_vp.update_layout(height=600, title="Volume Profile + POC aproximado", yaxis_title="Preço")
    st.plotly_chart(fig_vp, use_container_width=True)

with tab4:
    st.subheader("📞 Opções & Dark Pool")
    
    # Opções (yfinance)
    try:
        stock = yf.Ticker(ticker)
        opts = stock.option_chain(stock.options[0]) if stock.options else None
        if opts:
            calls = opts.calls
            st.write("**Calls com maior volume (Unusual Activity)**")
            st.dataframe(calls.nlargest(10, 'volume')[['strike', 'lastPrice', 'volume', 'openInterest', 'impliedVolatility']])
    except:
        st.info("Opções não disponíveis ou ticker BR (use Polygon para US).")

    # Dark Pool (Polygon)
    if polygon_key and not ticker.endswith('.SA'):
        st.write("**Dark Pool - Últimas trades grandes (Polygon)**")
        try:
            from polygon import RESTClient
            client = RESTClient(polygon_key)
            trades = client.get_trades(ticker, limit=500)
            dark = [t for t in trades if hasattr(t, 'exchange') and t.exchange in [4, 'D', 'T']]  # dark pool codes
            if dark:
                dark_df = pd.DataFrame([{'price': t.price, 'size': t.size, 'timestamp': t.timestamp} for t in dark[:20]])
                st.dataframe(dark_df)
                st.success(f"✅ {len(dark)} trades em Dark Pool detectados!")
            else:
                st.info("Nenhum trade dark pool recente.")
        except Exception as e:
            st.error(f"Erro Polygon: {e}")
    else:
        st.info("🔑 Insira sua chave Polygon (grátis) para ver Dark Pool de ações US.")

with tab5:
    st.subheader("⚙️ Backtest Simples (últimos 6 meses)")
    df_back = df.copy()
    df_back['Signal'] = (df_back['SUPERT_10_3.0'] < df_back['Close']) & (df_back['RSI_14'] > 50) & (df_back['MACD_12_26_9'] > df_back['MACDs_12_26_9'])
    df_back['Return'] = df_back['Close'].pct_change()
    df_back['Strategy'] = df_back['Signal'].shift(1) * df_back['Return']
    total_return = (1 + df_back['Strategy']).cumprod().iloc[-1] - 1
    st.metric("Retorno Estratégia", f"{total_return*100:.1f}%", delta=f"Buy & Hold: {((df['Close'].iloc[-1]/df['Close'].iloc[0])-1)*100:.1f}%")
    st.line_chart((1 + df_back[['Return', 'Strategy']]).cumprod())

st.caption("Desenvolvido para Momentum Swing Trade • Use com gerenciamento de risco • Não é recomendação de investimento")
