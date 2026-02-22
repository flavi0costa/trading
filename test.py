import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

st.set_page_config(page_title="Swing Predictor", layout="wide")

st.title("🏹 Swing Trade Predictor")

# Sidebar
ticker = st.sidebar.text_input("Ticker", "PETR4.SA")

if st.sidebar.button("Analisar"):
    df = yf.download(ticker, period="1y", interval="1d")
    if not df.empty:
        # Limpeza de colunas para o yfinance novo
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Indicador preditivo
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        
        # Gráfico Plotly (Evita o erro do Altair)
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'])])
        
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], name="EMA 200"))
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
        
        st.plotly_chart(fig, use_container_width=True)
        st.success(f"Análise de {ticker} concluída com sucesso!")