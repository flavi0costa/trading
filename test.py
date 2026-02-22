import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Predator Pro: Full Control", layout="wide")

# --- MAPEAMENTO SETORIAL ---
SECTOR_MAP = {
    'AAPL': 'XLK', 'MSFT': 'XLK', 'NVDA': 'XLK', 'AMD': 'XLK', 'ADBE': 'XLK', 'CRM': 'XLK',
    'AMZN': 'XLY', 'TSLA': 'XLY', 'META': 'XLC', 'GOOGL': 'XLC', 'NFLX': 'XLC',
    'JPM': 'XLF', 'BAC': 'XLF', 'V': 'XLF', 'MA': 'XLF', 'XOM': 'XLE', 'CVX': 'XLE',
    'PFE': 'XLV', 'UNH': 'XLV', 'JNJ': 'XLV', 'PETR4.SA': 'EWZ', 'VALE3.SA': 'EWZ'
}

# --- SIDEBAR: GESTÃO DE RISCO E PARÂMETROS ---
st.sidebar.header("🛡️ Gestão de Risco & Parâmetros")
multi_stop = st.sidebar.slider("Multiplicador Stop (ATR)", 1.0, 3.5, 2.0, 0.5)
multi_alvo = st.sidebar.slider("Multiplicador Alvo (ATR)", 2.0, 6.0, 4.0, 0.5)
rsi_limit = st.sidebar.slider("RSI Sobrecompra", 60, 80, 70)

st.sidebar.markdown("---")
st.sidebar.header("💰 Simulador de Posição")
capital = st.sidebar.number_input("Capital Total ($)", value=10000)
risco_perc = st.sidebar.slider("Risco por Trade (%)", 0.5, 5.0, 1.0, 0.5)

# --- FUNÇÃO TÉCNICA CORE ---
def fetch_and_calculate(ticker):
    try:
        s_etf = SECTOR_MAP.get(ticker, 'SPY')
        data = yf.download([ticker, 'SPY', s_etf], period="2y", interval="1d", progress=False)
        if data.empty: return None, None
        
        df = data['Close'][[ticker]].rename(columns={ticker: 'Close'})
        for c in ['High', 'Low', 'Open', 'Volume']: df[c] = data[c][ticker]
        df['SPY_Close'] = data['Close']['SPY']
        df['SETOR_Close'] = data['Close'][s_etf]

        # Indicadores Clássicos
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Bollinger & Squeeze
        bb = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None: df = pd.concat([df, sqz], axis=1)
        
        # Volume & Momentum
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        # Divergência RSI
        df['Low_Pivot'] = (df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))
        df['Div_Bull'] = (df['RSI'] > df['RSI'].shift(2)) & (df['Low'] < df['Low'].shift(2)) & (df['Low_Pivot'])

        return df, s_etf
    except: return None, None

# --- UI PRINCIPAL ---
st.title("🏹 Predator Pro Ultimate Dashboard")
tab1, tab2, tab3 = st.tabs(["🚀 Scanner Setorial", "🔍 Análise Manual Full", "📊 Performance Histórica"])

# --- ABA 2: ANÁLISE MANUAL (RESTAURADA E COMPLETA) ---
with tab2:
    t_manual = st.text_input("Ticker para Análise Total", "NVDA").upper()
    if st.button("Executar Análise 360º"):
        df, s_etf = fetch_and_calculate(t_manual)
        if df is not None:
            df_p = df.tail(126)
            u = df_p.iloc[-1]
            
            # 1. Cálculos de Gestão
            stop = float(u['Close'] - (u['ATR'] * multi_stop))
            alvo = float(u['Close'] + (u['ATR'] * multi_alvo))
            qty = int((capital * (risco_perc/100)) / (u['Close'] - stop)) if (u['Close']-stop)>0 else 0
            
            # 2. Métricas de Topo
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Preço Atual", f"{u['Close']:.2f}")
            c2.metric("Stop Loss", f"{stop:.2f}", delta_color="inverse")
            c3.metric("Alvo (TP)", f"{alvo:.2f}")
            c4.metric("Qtd. Sugerida", f"{qty} un")
            c5.metric("Money Flow", f"{u['MFI']:.0f}")

            # 3. Gráfico de Subplots (Preço, RSI, Volume/MACD)
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.3])
            
            # Vela + Bollinger + EMA 200 + Stop/Alvo
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Preço"), row=1, col=1)
            bbu_col = [c for c in df_p.columns if c.startswith('BBU')][0]
            bbl_col = [c for c in df_p.columns if c.startswith('BBL')][0]
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p[bbu_col], name="BB Sup", line=dict(color='rgba(173,216,230,0.2)')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p[bbl_col], name="BB Inf", line=dict(color='rgba(173,216,230,0.2)')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA_200'], name="EMA 200", line=dict(color='yellow')), row=1, col=1)
            fig.add_hline(y=stop, line_dash="dash", line_color="red", row=1, col=1)
            fig.add_hline(y=alvo, line_dash="dash", line_color="green", row=1, col=1)

            # RSI + Níveis
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=rsi_limit, line_dash="dot", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

            # Histograma MACD + RVOL
            fig.add_trace(go.Bar(x=df_p.index, y=df_p.iloc[:, df_p.columns.get_loc('MACDh_12_26_9')], name="MACD Hist"), row=3, col=1)
            
            fig.update_layout(template="plotly_dark", height=900, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # 4. Diagnóstico Detalhado
            st.subheader("🏁 Diagnóstico Predator Pro")
            d1, d2, d3 = st.columns(3)
            with d1:
                st.write("**📡 Sinais de Momentum**")
                if u['SQZ_ON'] == 1: st.warning("SQUEEZE: Volatilidade Comprimida")
                if u['Div_Bull']: st.success("🎯 DIVERGÊNCIA BULLISH DETECTADA!")
                
            with d2:
                st.write("**🏢 Força Setorial**")
                perf_s = (u['Close']/df.iloc[-20]['Close'])-1
                perf_e = (u['SETOR_Close']/df.iloc[-20]['SETOR_Close'])-1
                st.write(f"Ativo (20d): {perf_s:.2%}")
                st.write(f"Setor {s_etf}: {perf_e:.2%}")
            with d3:
                st.write("**💰 Fluxo Institucional**")
                if u['RVOL'] > 1.5: st.success(f"Volume Relativo: {u['RVOL']:.2f}x (Alto)")
                else: st.write(f"Volume Relativo: {u['RVOL']:.2f}x")
                

# --- ABA 1 & 3 MANTIDAS COM A MESMA LÓGICA DO "GOD MODE" ---