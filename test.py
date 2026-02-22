import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Swing Predictor Pro", layout="wide")

# Estilo CSS para remover erros visuais e melhorar o visual
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    stDataFrame { width: 100%; }
    </style>
    """, unsafe_allow_index=True)

st.title("📈 Swing Trade Predictor: Smart Money & Squeeze")
st.write("Este dashboard analisa confluências de Smart Money, Volatilidade e Médias Institucionais.")

# --- SIDEBAR ---
st.sidebar.header("Painel de Controle")
mercado = st.sidebar.selectbox("Selecione o Mercado", ["Bovespa (Brasil)", "S&P 500 (EUA)"])
periodo = st.sidebar.slider("Meses de histórico para análise", 6, 24, 12)

if mercado == "Bovespa (Brasil)":
    tickers = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'ABEV3.SA', 'WEGE3.SA', 'MGLU3.SA', 'JBSS3.SA', 'RENT3.SA']
else:
    tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NFLX', 'AMD', 'PLTR']

# --- FUNÇÃO DE ANÁLISE ---
def get_analysis(ticker):
    df = yf.download(ticker, period=f"{periodo}mo", interval="1d", progress=False)
    if df.empty or len(df) < 50: return None
    
    # Limpeza de colunas (correção para novas versões do yfinance)
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # 1. Médias e RSI
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # 2. Gestão de Risco (ATR)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    # 3. TTM Squeeze (Previsão de Explosão)
    sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
    if sqz is not None:
        df = pd.concat([df, sqz], axis=1)
    
    return df

# --- EXECUÇÃO ---
if st.sidebar.button('🚀 Rodar Scanner de Oportunidades'):
    resultados = []
    
    with st.spinner('Analisando o mercado...'):
        for ticker in tickers:
            df = get_analysis(ticker)
            if df is None: continue
            
            ultimo = df.iloc[-1]
            penultimo = df.iloc[-2]
            
            # Lógica Preditiva
            # Estar acima da EMA 200 + Squeeze acabou de soltar (ponto verde)
            sinal_compra = (ultimo['Close'] > ultimo['EMA_200']) and \
                           (ultimo['SQZ_ON'] == 0 and penultimo['SQZ_ON'] == 1)
            
            # Alerta de Squeeze (prestes a explodir)
            em_squeeze = (ultimo['SQZ_ON'] == 1)
            
            status = "COMPRA" if sinal_compra else ("Squeeze (Alerta)" if em_squeeze else "Neutro")
            
            # Cálculos de Saída
            stop = ultimo['Close'] - (ultimo['ATR'] * 2)
            alvo = ultimo['Close'] + (ultimo['ATR'] * 4)
            
            resultados.append({
                "Ticker": ticker,
                "Preço": round(float(ultimo['Close']), 2),
                "Status": status,
                "RSI": round(float(ultimo['RSI']), 2),
                "Stop Loss": round(float(stop), 2),
                "Alvo": round(float(alvo), 2),
                "Data": df.index[-1].strftime('%Y-%m-%d')
            })

    # Mostrar Tabela
    if resultados:
        res_df = pd.DataFrame(resultados)
        
        def color_status(val):
            if val == 'COMPRA': return 'background-color: #006400'
            if val == 'Squeeze (Alerta)': return 'background-color: #8B8000'
            return ''

        st.subheader("📋 Resultados do Scanner")
        st.dataframe(res_df.style.applymap(color_status, subset=['Status']), use_container_width=True)

        # Gráfico para o primeiro Ticker com sinal de compra
        compra_list = res_df[res_df['Status'] == 'COMPRA']['Ticker'].tolist()
        if compra_list:
            st.success(f"🔥 Sinais de Compra detetados em: {', '.join(compra_list)}")
            selecionado = st.selectbox("Selecione para ver o gráfico detalhado:", compra_list)
            
            df_plot = get_analysis(selecionado)
            
            # Plotly Candlestick
            fig = go.Figure(data=[go.Candlestick(
                x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                low=df_plot['Low'], close=df_plot['Close'], name="Preço"
            )])
            
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA_200'], line=dict(color='yellow', width=2), name="EMA 200 (Institucional)"))
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA_20'], line=dict(color='cyan', width=1), name="EMA 20"))
            
            # Adicionar Linhas de Stop e Alvo
            row = res_df[res_df['Ticker'] == selecionado].iloc[0]
            fig.add_hline(y=row['Stop Loss'], line_dash="dash", line_color="red", annotation_text="STOP LOSS")
            fig.add_hline(y=row['Alvo'], line_dash="dash", line_color="green", annotation_text="ALVO")
            
            fig.update_layout(title=f"Configuração de Trade: {selecionado}", template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum sinal de 'COMPRA' imediato. Fique atento às ações em 'Squeeze'.")
    else:
        st.error("Não foi possível obter dados. Verifique a conexão.")

else:
    st.info("Clique no botão à esquerda para iniciar o scanner.")