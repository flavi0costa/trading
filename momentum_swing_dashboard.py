import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(page_title="Momentum Swing Trade Pro", layout="wide")
st.title("📈 Análise Técnica Momentum Swing Trade")
st.markdown("**RSI • MACD • Bollinger • Stochastic • ADX • Volume Profile • SuperTrend • Williams %R • MFI + Padrões de Candle + Dark Pool + Opções**")

# ====================== SIDEBAR ======================
st.sidebar.header("Configurações")
ticker = st.sidebar.text_input("Ticker (ex: PETR4.SA ou AAPL)", "PETR4.SA").upper()
period = st.sidebar.selectbox("Período", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
interval = st.sidebar.selectbox("Intervalo", ["1d", "60m"], index=0)
polygon_key = st.sidebar.text_input("Polygon API Key (opcional - Dark Pool US)", type="password")

# ====================== BAIXAR DADOS ======================
@st.cache_data(ttl=300)
def get_data(ticker, period, interval):
    return yf.download(ticker, period=period, interval=interval, auto_adjust=True)

df = get_data(ticker, period, interval)
if df.empty:
    st.error("❌ Ticker inválido ou sem dados.")
    st.stop()

# ====================== INDICADORES ======================
df['RSI_14'] = ta.rsi(df['Close'], length=14)
macd = ta.macd(df['Close'])
df = pd.concat([df, macd], axis=1)
bb = ta.bbands(df['Close'])
df = pd.concat([df, bb], axis=1)
stoch = ta.stoch(df['High'], df['Low'], df['Close'])
df = pd.concat([df, stoch], axis=1)
adx = ta.adx(df['High'], df['Low'], df['Close'])
df = pd.concat([df, adx], axis=1)
df['WILLR_14'] = ta.willr(df['High'], df['Low'], df['Close'], length=14)
df['MFI_14'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
supertrend = ta.supertrend(df['High'], df['Low'], df['Close'])
df = pd.concat([df, supertrend], axis=1)

df['EMA9'] = ta.ema(df['Close'], length=9)
df['EMA21'] = ta.ema(df['Close'], length=21)
df['EMA200'] = ta.ema(df['Close'], length=200)
df['OBV'] = ta.obv(df['Close'], df['Volume'])
df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

# ====================== VOLUME PROFILE (já corrigido anteriormente) ======================
def volume_profile(df, n_bins=40):
    if df.empty or len(df) < 10:
        return pd.DataFrame(columns=['price_bin', 'Volume', 'price'])
    data = df.dropna(subset=['High', 'Low', 'Volume']).copy()
    if len(data) < 10:
        return pd.DataFrame(columns=['price_bin', 'Volume', 'price'])
    mid_price = ((data['High'] + data['Low']) / 2).astype('float64')
    price_min = float(mid_price.min())
    price_max = float(mid_price.max())
    if price_max - price_min < 1e-6:
        price_max += abs(price_min) * 0.05 + 0.01
    bins = np.linspace(price_min, price_max, n_bins + 1)
    data['price_bin'] = pd.cut(mid_price, bins=bins, include_lowest=True, duplicates='drop')
    vp = (data.groupby('price_bin', observed=True)['Volume']
          .sum()
          .reset_index())
    vp['price'] = vp['price_bin'].apply(lambda x: x.mid if pd.notnull(x) else np.nan)
    vp = vp.dropna(subset=['price']).sort_values('price').reset_index(drop=True)
    return vp

# ====================== PADRÕES DE CANDLE (100% CORRIGIDO) ======================
def detect_patterns(df):
    patterns = {}
    if len(df) < 1:
        return {'Bullish Engulfing': False, 'Hammer': False, 'Doji': False, 'Morning Star': False}
    
    # Bullish Engulfing
    patterns['Bullish Engulfing'] = bool(((df['Close'].shift(1) < df['Open'].shift(1)) & 
                                         (df['Close'] > df['Open']) & 
                                         (df['Open'] < df['Close'].shift(1)) & 
                                         (df['Close'] > df['Open'].shift(1))).iloc[-1])
    
    # Hammer
    body = abs(df['Close'] - df['Open'])
    lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
    patterns['Hammer'] = bool(((lower_shadow > 2 * body) & (body > 0)).iloc[-1])
    
    # Doji
    patterns['Doji'] = bool((abs(df['Close'] - df['Open']) <= 0.1 * (df['High'] - df['Low'])).iloc[-1])
    
    # Morning Star - CORRIGIDO com escalares explícitos
    patterns['Morning Star'] = False
    if len(df) >= 3:
        c1 = df.iloc[-3]
        c2 = df.iloc[-2]
        c3 = df.iloc[-1]
        cond1 = float(c1['Close']) < float(c1['Open'])
        cond2 = abs(float(c2['Close']) - float(c2['Open'])) < 0.3 * (float(c2['High']) - float(c2['Low']))
        cond3 = float(c3['Close']) > float(c3['Open'])
        cond4 = float(c3['Close']) > (float(c1['Open']) + float(c1['Close'])) / 2
        patterns['Morning Star'] = bool(cond1 and cond2 and cond3 and cond4)
    
    return patterns

patterns = detect_patterns(df)

# ====================== LÓGICA DE SINAIS ======================
def generate_signals(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    trend_up = latest['Close'] > latest['EMA200']
    adx_strong = latest['ADX_14'] > 25
    super_bull = latest['SUPERT_10_3.0'] < latest['Close']

    macd_bull = latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] and prev['MACD_12_26_9'] <= prev['MACDs_12_26_9']
    rsi_ok = 45 < latest['RSI_14'] < 75
    stoch_cross = latest['STOCHk_14_3_3'] > latest['STOCHd_14_3_3'] and prev['STOCHk_14_3_3'] <= prev['STOCHd_14_3_3']
    mfi_bull = latest['MFI_14'] > 50

    score = 0
    if trend_up: score += 20
    if adx_strong: score += 15
    if super_bull: score += 20
    if macd_bull: score += 15
    if rsi_ok: score += 10
    if stoch_cross: score += 10
    if mfi_bull: score += 10
    score = min(100, score)

    entry = (score >= 75 and 
             any([patterns['Bullish Engulfing'], patterns['Hammer'], patterns['Morning Star']]) and 
             latest['Volume'] > df['Volume'].rolling(20).mean().iloc[-1])

    stop_loss = latest['SUPERT_10_3.0'] * 0.995 if super_bull else latest['Close'] * 0.96
    risk = latest['Close'] - stop_loss
    tp1 = latest['Close'] + risk * 1.5
    tp2 = latest['Close'] + risk * 2.5

    return {
        'Confluence_Score': score,
        'Sinal_Entrada_LONG': entry,
        'Stop_Loss': stop_loss,
        'TP1': tp1,
        'TP2': tp2,
        'RR': 2.5
    }

signals = generate_signals(df)

# ====================== LAYOUT ======================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Gráfico + Sinais", "📈 Todos os Indicadores", "🔥 Volume Profile", "📞 Opções & Dark Pool", "⚙️ Backtest"])

with tab1:
    st.subheader(f"{ticker} - Momentum Swing Trade")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Confluence Score", f"{signals['Confluence_Score']}%")
    col2.metric("Sinal Entrada LONG", "✅ COMPRA AGRESSIVA" if signals['Sinal_Entrada_LONG'] else "Aguardar")
    col3.metric("Stop Loss", f"R$ {signals['Stop_Loss']:.2f}")
    col4.metric("Take Profit 2", f"R$ {signals['TP2']:.2f}", delta=f"RR 1:{signals['RR']}")

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.5, 0.15, 0.15, 0.2])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="OHLC"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SUPERT_10_3.0'], name="SuperTrend", line=dict(color='purple', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BBL_5_2.0'], name="BB Lower", line=dict(color='gray')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BBU_5_2.0'], name="BB Upper", line=dict(color='gray')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], name="EMA9", line=dict(color='orange')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], name="EMA21", line=dict(color='blue')), row=1, col=1)
    
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='rgba(0,150,255,0.6)'), row=2, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='lime')), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
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
    cols[1].write(f"**Stochastic K**: {df['STOCHk_14_3_3'].iloc[-1]:.1f}")
    cols[1].write(f"**MFI**: {df['MFI_14'].iloc[-1]:.1f}")
    cols[2].write(f"**Williams %R**: {df['WILLR_14'].iloc[-1]:.1f}")
    cols[2].write("**Padrões detectados:**")
    for p, v in patterns.items():
        if v: cols[2].success(p)

with tab3:
    st.subheader("🔥 Volume Profile")
    try:
        vp = volume_profile(df)
        if vp.empty or len(vp) < 3:
            st.warning("Não foi possível gerar Volume Profile.")
        else:
            fig_vp = go.Figure()
            fig_vp.add_trace(go.Bar(x=vp['Volume'], y=vp['price'], orientation='h', name="Volume", marker_color='rgba(0,180,255,0.7)'))
            fig_vp.add_trace(go.Scatter(x=[0, vp['Volume'].max()*1.05], y=[df['Close'].iloc[-1]]*2, mode="lines", name="Preço Atual", line=dict(color="red", width=3, dash="dash")))
            fig_vp.update_layout(height=650, title="Volume Profile + Preço Atual", yaxis_title="Preço", xaxis_title="Volume Negociado")
            st.plotly_chart(fig_vp, use_container_width=True)
            poc = vp.loc[vp['Volume'].idxmax(), 'price']
            st.success(f"**POC (Point of Control):** R$ {poc:.2f}")
    except Exception as e:
        st.error(f"Erro Volume Profile: {e}")

with tab4:
    st.subheader("📞 Opções & Dark Pool")
    try:
        stock = yf.Ticker(ticker)
        if stock.options:
            opts = stock.option_chain(stock.options[0])
            st.write("**Calls com maior volume**")
            st.dataframe(opts.calls.nlargest(10, 'volume')[['strike', 'lastPrice', 'volume', 'openInterest', 'impliedVolatility']])
    except:
        st.info("Opções não disponíveis.")

    if polygon_key and not ticker.endswith('.SA'):
        try:
            from polygon import RESTClient
            client = RESTClient(polygon_key)
            trades = list(client.get_trades(ticker, limit=500))
            dark = [t for t in trades if hasattr(t, 'exchange') and str(t.exchange) in ['4', 'D', 'T']]
            if dark:
                dark_df = pd.DataFrame([{'price': t.price, 'size': t.size, 'timestamp': pd.to_datetime(t.timestamp, unit='ns')} for t in dark[:20]])
                st.dataframe(dark_df)
                st.success(f"✅ {len(dark)} trades em Dark Pool!")
        except Exception as e:
            st.error(f"Erro Polygon: {e}")
    elif not ticker.endswith('.SA'):
        st.info("Insira sua chave Polygon para Dark Pool.")

with tab5:
    st.subheader("⚙️ Backtest Simples")
    df_back = df.copy()
    df_back['Signal'] = (df_back['SUPERT_10_3.0'] < df_back['Close']) & (df_back['RSI_14'] > 50) & (df_back['MACD_12_26_9'] > df_back['MACDs_12_26_9'])
    df_back['Return'] = df_back['Close'].pct_change()
    df_back['Strategy'] = df_back['Signal'].shift(1) * df_back['Return']
    total_return = (1 + df_back['Strategy']).cumprod().iloc[-1] - 1
    bh_return = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
    st.metric("Retorno Estratégia", f"{total_return*100:.1f}%", delta=f"Buy & Hold: {bh_return*100:.1f}%")
    st.line_chart((1 + df_back[['Return', 'Strategy']]).cumprod())

st.caption("✅ Todos os erros corrigidos • Use com gerenciamento de risco • Não é recomendação")
