import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="Swing Predictor Pro", layout="wide")

st.title("🏹 Sistema de Previsão Swing Trade")
st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Painel de Controle")
    ticker = st.text_input("Ticker (ex: PETR4.SA, VALE3.SA, TSLA)", "PETR4.SA").upper()
    periodo = st.selectbox("Período de Análise", ["6mo", "1y", "2y"], index=1)
    analisar = st.button("Executar Análise Preditiva")

# --- FUNÇÃO DE PROCESSAMENTO ---
def processar_dados(ticker, p):
    try:
        # Download dos dados
        df = yf.download(ticker, period=p, interval="1d", progress=False)
        if df.empty:
            return None
        
        # Limpeza de colunas para compatibilidade com yfinance novo
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 1. Média Móvel Institucional (200 períodos)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        
        # 2. TTM Squeeze (Previsão de Explosão de Volatilidade)
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None:
            df = pd.concat([df, sqz], axis=1)
            
        # 3. Fair Value Gaps - FVG (Smart Money)
        # Identifica gaps onde houve forte agressão institucional
        df['FVG_Bull'] = (df['Low'] > df['High'].shift(2)) & (df['Close'].shift(1) > df['Open'].shift(1))
        
        # 4. ATR para Gestão de Risco
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return None

# --- EXECUÇÃO ---
if analisar:
    with st.spinner(f"Analisando confluências para {ticker}..."):
        df = processar_dados(ticker, periodo)
        
        if df is not None:
            ultimo = df.iloc[-1]
            penultimo = df.iloc[-2]
            
            # --- CÁLCULOS DE TRADE ---
            stop_loss = ultimo['Close'] - (ultimo['ATR'] * 2)
            take_profit = ultimo['Close'] + (ultimo['ATR'] * 4)
            tendencia_alta = ultimo['Close'] > ultimo['EMA_200']
            
            # Verificação do Squeeze
            squeeze_soltando = (ultimo['SQZ_ON'] == 0 and penultimo['SQZ_ON'] == 1)
            em_squeeze = (ultimo['SQZ_ON'] == 1)
            fvg_recente = df['FVG_Bull'].tail(5).any()

            # --- EXIBIÇÃO DE MÉTRICAS ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço Atual", f"{ultimo['Close']:.2f}")
            c2.metric("Tendência (EMA 200)", "ALTA" if tendencia_alta else "BAIXA")
            c3.metric("Stop Loss (ATR)", f"{stop_loss:.2f}")
            c4.metric("Alvo Sugerido", f"{take_profit:.2f}")

            # --- GRÁFICO VISUAL (PLOTLY) ---
            fig = go.Figure(data=[go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name="Preço"
            )])
            
            # Adicionar Médias
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='yellow', width=2), name="EMA 200"))
            
            # Linhas de Gestão de Risco
            fig.add_hline(y=stop_loss, line_dash="dash", line_color="red", annotation_text="STOP")
            fig.add_hline(y=take_profit, line_dash="dash", line_color="green", annotation_text="ALVO")

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
            st.plotly_chart(fig, use_container_width=True)

            # --- DIAGNÓSTICO PREDITIVO ---
            st.subheader("🔮 Diagnóstico do Sistema")
            
            if tendencia_alta and squeeze_soltando:
                st.balloons()
                st.success(f"CONFLUÊNCIA MÁXIMA: {ticker} apresenta um sinal clássico de início de Swing Trade. Squeeze rompeu a favor da tendência institucional!")
            
            elif em_squeeze:
                st.info("PACIÊNCIA: O ativo está a acumular energia ('Squeeze'). Aguarde o sinal ficar verde para prever a explosão direcional.")
                
                
            elif fvg_recente:
                st.warning("SMART MONEY: Foram detetados Fair Value Gaps recentes. O preço pode estar a ser impulsionado por grandes instituições.")
                

            else:
                st.write("Sem sinais de entrada imediata. O mercado está em fase de movimentação normal.")

        else:
            st.error("Dados não encontrados. Verifique se o ticker está correto (ex: usar .SA para ações brasileiras).")
else:
    st.info("Selecione um ativo e clique em 'Executar Análise' para ver os sinais preditivos.")