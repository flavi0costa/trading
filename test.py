import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="Swing Predictor Pro", layout="wide")

st.title("🏹 Sistema de Previsão Swing Trade")
st.markdown("---")

# --- INPUT DE TICKER ---
ticker = st.sidebar.text_input("Ticker (ex: PETR4.SA, VALE3.SA, TSLA)", "PETR4.SA").upper()

def calcular_sinais(df):
    # 1. MÉDIAS INSTITUCIONAIS (Tendência)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    
    # 2. TTM SQUEEZE (Previsão de Explosão de Volatilidade)
    # Deteta quando o preço está "comprimido" e pronto para disparar
    sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
    if sqz is not None:
        df = pd.concat([df, sqz], axis=1)

    # 3. FAIR VALUE GAPS - FVG (Rasto do Smart Money)
    # Identifica onde as instituições entraram com muita força
    df['FVG_Bull'] = (df['Low'] > df['High'].shift(2)) & (df['Close'].shift(1) > df['Open'].shift(1))
    
    # 4. GESTÃO DE RISCO ATR
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    return df

if st.sidebar.button("Analisar Sinais Avançados"):
    with st.spinner(f"Analisando confluências para {ticker}..."):
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        
        if not df.empty:
            # Correção de Colunas yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = calcular_sinais(df)
            
            ultimo = df.iloc[-1]
            penultimo = df.iloc[-2]
            
            # --- LÓGICA DE DECISÃO ---
            tendencia_alta = ultimo['Close'] > ultimo['EMA_200']
            squeeze_soltando = (ultimo['SQZ_ON'] == 0 and penultimo['SQZ_ON'] == 1)
            em_squeeze = (ultimo['SQZ_ON'] == 1)
            fvg_recente = df['FVG_Bull'].tail(5).any()

            # --- PAINEL DE SINAIS ---
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.subheader("📊 Estrutura")
                st.write(f"**Tendência EMA 200:** {'✅ ALTA' if tendencia_alta else '❌ BAIXA'}")
                st.write(f"**Smart Money (FVG):** {'🔥 Detetado' if fvg_recente else '⚪ Nenhum recente'}")

            with c2:
                st.subheader("⚡ Volatilidade")
                if squeeze_soltando:
                    st.success("🚀 SINAL: Rompimento de Squeeze!")
                elif em_squeeze:
                    st.warning("🟡 ALERTA: Acumulando energia (Squeeze)")
                else:
                    st.write("⚪ Estável")

            with c3:
                st.subheader("🛡️ Gestão de Risco")
                stop = ultimo['Close'] - (ultimo['ATR'] * 2)
                alvo = ultimo['Close'] + (ultimo['ATR'] * 4)
                st.metric("Preço", f"{ultimo['Close']:.2f}")
                st.write(f"**Stop Loss:** {stop:.2f}")
                st.write(f"**Alvo (TP):** {alvo:.2f}")

            # --- GRÁFICO VISUAL ---
            fig = go.Figure(data=[go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name="Preço")])
            
            # Adicionar Médias e Sinais no Gráfico
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='yellow', width=1.5), name="EMA 200"))
            
            # Desenhar Linhas de Trade
            fig.add_hline(y=stop, line_dash="dash", line_color="red", annotation_text="STOP LOSS")
            fig.add_hline(y=alvo, line_dash="dash", line_color="green", annotation_text="ALVO")

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
            st.plotly_chart(fig, use_container_width=True)

            # --- CONCLUSÃO PREDITIVA ---
            st.markdown("### 🔮 Previsão do Sistema")
            if tendencia_alta and squeeze_soltando:
                st.balloons()
                st.success(f"CONFLUÊNCIA MÁXIMA: {ticker} apresenta um sinal clássico de início de Swing Trade de alta com suporte institucional e explosão de volatilidade.")
            elif em_squeeze:
                st.info("PACIÊNCIA: O ativo está a "apertar". Aguarde o ponto de squeeze ficar verde para entrar na direção da tendência.")
            else:
                st.write("Sem sinais claros de entrada no momento. O sistema procura por reversões ou rompimentos de volatilidade.")

        else:
            st.error("Não foi possível carregar os dados. Verifique o Ticker.")