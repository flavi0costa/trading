import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# --- FORÇAR O STREAMLIT A IGNORAR COMPONENTES ANTIGOS ---
st.set_page_config(page_title="Swing Trade Predictor", layout="wide")

st.title("🛡️ Swing Predictor (Versão Estável)")

# Função para buscar dados com tratamento de erro de colunas
def carregar_dados(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: return None
        # Limpeza para evitar erros de Multi-Index do yfinance
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {ticker}: {e}")
        return None

# Interface Simples
ticker_alvo = st.text_input("Digite o Ticker (ex: PETR4.SA ou NVDA):", "AAPL")

if st.button("Analisar"):
    df = carregar_dados(ticker_alvo)
    
    if df is not None:
        # Cálculos Avançados
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # Detetar Squeeze
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        df = pd.concat([df, sqz], axis=1)
        
        ultimo = df.iloc[-1]
        
        # Gestão de Risco
        stop_loss = ultimo['Close'] - (ultimo['ATR'] * 2)
        alvo = ultimo['Close'] + (ultimo['ATR'] * 4)

        # MÉTRICAS EM COLUNAS (Substitui as tabelas nativas que podem pedir Altair)
        col1, col2, col3 = st.columns(3)
        col1.metric("Preço Atual", f"{ultimo['Close']:.2f}")
        col2.metric("Stop Loss (ATR)", f"{stop_loss:.2f}", delta_color="inverse")
        col3.metric("Alvo Sugerido", f"{alvo:.2f}")

        # GRÁFICO PLOTLY (Não usa Altair/Vegalite)
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name="Candlesticks"
        )])
        
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='yellow', width=1.5), name="EMA 200"))
        
        # Linhas de Trade
        fig.add_hline(y=stop_loss, line_dash="dash", line_color="red", annotation_text="STOP")
        fig.add_hline(y=alvo, line_dash="dash", line_color="green", annotation_text="ALVO")

        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
        st.plotly_chart(fig, use_container_width=True)

        # Diagnóstico Preditivo
        if ultimo['SQZ_ON'] == 1:
            st.warning("⚠️ ATENÇÃO: O ativo está em **SQUEEZE**. Prepare-se para um movimento violento em breve.")
        elif ultimo['Close'] > ultimo['EMA_200']:
            st.success("✅ TENDÊNCIA: O ativo está em tendência de alta institucional (Acima da EMA 200).")