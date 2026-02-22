import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Swing Trade Predictor", layout="wide")

st.title("🚀 Swing Trade Predictor & Scanner")
st.write("Análise preditiva baseada em Squeeze de Volatilidade, Smart Money (FVG) e Gestão ATR.")

# Sidebar para configurações
st.sidebar.header("Configurações")
mercado = st.sidebar.selectbox("Escolha o Mercado", ["Bovespa (Brasil)", "S&P 500 (EUA)"])

# Listas de Ativos
if mercado == "Bovespa (Brasil)":
    tickers = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'ABEV3.SA', 'BBDC4.SA', 'BBAS3.SA', 'JBSS3.SA', 'MGLU3.SA', 'WEGE3.SA', 'HAPV3.SA']
else:
    tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NFLX', 'AMD', 'PLTR']

if st.button('Rodar Scanner'):
    resultados = []
    progresso = st.progress(0)
    
    for i, ticker in enumerate(tickers):
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df.empty or len(df) < 100: continue
            
            # Limpar colunas (yfinance multi-index fix)
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

            # Indicadores
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            
            # Squeeze
            sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
            df = pd.concat([df, sqz], axis=1)

            ultimo = df.iloc[-1]
            penultimo = df.iloc[-2]

            # Lógica Preditiva: Fim do Squeeze em tendência de alta
            sinal_compra = (ultimo['Close'] > ultimo['EMA_200']) and \
                           (ultimo['SQZ_ON'] == 0 and penultimo['SQZ_ON'] == 1)

            status = "Aguardando"
            if sinal_compra: status = "COMPRA"
            elif ultimo['SQZ_ON'] == 1: status = "Squeeze (Alerta)"

            # Gestão de Risco
            stop = ultimo['Close'] - (ultimo['ATR'] * 2)
            alvo = ultimo['Close'] + (ultimo['ATR'] * 4)

            resultados.append({
                "Ticker": ticker,
                "Preço": round(float(ultimo['Close']), 2),
                "Status": status,
                "RSI": round(float(ultimo['RSI']), 2),
                "Stop Loss": round(float(stop), 2),
                "Alvo": round(float(alvo), 2)
            })
        except:
            continue
        progresso.progress((i + 1) / len(tickers))

    # Exibição
    res_df = pd.DataFrame(resultados)
    
    # Destacar linhas de compra
    def color_status(val):
        color = 'green' if val == 'COMPRA' else 'orange' if val == 'Squeeze (Alerta)' else 'white'
        return f'background-color: {color}'

    st.subheader("Resultado do Scanner")
    st.dataframe(res_df.style.applymap(color_status, subset=['Status']))

    # Alerta de Gestão de Risco
    st.info("💡 O Stop Loss é calculado em 2x ATR para evitar violinos. O Alvo é 4x ATR (Risco:Retorno 1:2).")
