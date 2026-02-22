import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Swing Predictor Ultra", layout="wide")

st.title("🏹 Swing Predictor Ultra: Volume & Momentum")

# --- SIDEBAR ---
with st.sidebar:
    ticker = st.text_input("Ticker", "PETR4.SA").upper()
    periodo_vista = st.selectbox("Vista", ["6mo", "1y", "2y"], index=0)
    analisar = st.button("Analisar Confluências Pro")

def processar_dados_pro(ticker, p_vista):
    try:
        # Baixamos histórico longo para cálculos precisos
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 1. TENDÊNCIA E VOLATILIDADE
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # 2. MOMENTUM (MACD)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        
        # 3. VOLUME (OBV)
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        
        # 4. SQUEEZE
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None:
            df = pd.concat([df, sqz], axis=1)
            
        # Filtro de exibição
        mapa = {"6mo": 126, "1y": 252, "2y": 504}
        return df.tail(mapa[p_vista])
    except Exception as e:
        st.error(f"Erro: {e}")
        return None

if analisar:
    df = processar_dados_pro(ticker, periodo_vista)
    
    if df is not None:
        ultimo = df.iloc[-1]
        penultimo = df.iloc[-2]
        
        # Lógica de Sinais
        compra_fvg = (ultimo['Low'] > df['High'].shift(2).iloc[-1])
        vol_confirmado = ultimo['OBV'] > df['OBV'].shift(1).iloc[-1]
        macd_alta = ultimo['MACD_12_26_9'] > ultimo['MACDs_12_26_9']
        
        # --- MÉTRICAS ---
        cols = st.columns(4)
        cols[0].metric("Preço", f"{ultimo['Close']:.2f}")
        cols[1].metric("MACD", "BULL" if macd_alta else "BEAR")
        cols[2].metric("Vol. (OBV)", "Crescente" if vol_confirmado else "Queda")
        cols[3].metric("Squeeze", "Ativo" if ultimo['SQZ_ON'] == 1 else "Liberado")

        # --- GRÁFICO AVANÇADO (SUBPLOTS) ---
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.05, row_heights=[0.7, 0.3])

        # Candle e EMA 200
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                   low=df['Low'], close=df['Close'], name="Preço"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], name="EMA 200", line=dict(color='yellow')), row=1, col=1)
        
        # MACD no segundo gráfico
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="Histograma MACD"), row=2, col=1)

        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=800)
        st.plotly_chart(fig, use_container_width=True)

        # --- DIAGNÓSTICO ---
        st.subheader("📝 Check-list de Confirmação")
        if ultimo['Close'] > ultimo['EMA_200'] and macd_alta and vol_confirmado:
            st.balloons()
            st.success("🎯 **CONFLUÊNCIA TOTAL:** Tendência, Momentum e Volume estão alinhados para ALTA.")
        else:
            st.info("Aguardando alinhamento total de indicadores para um sinal de alta probabilidade.")