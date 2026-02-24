import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pandas_ta as ta
import warnings

# Configurações iniciais
warnings.filterwarnings("ignore")
st.set_page_config(page_title="Pro Momentum Dashboard", layout="wide")

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=300)
def baixar_dados(ticker):
    # Pega 2 anos para garantir o cálculo da SMA200
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    return df.dropna(how='all').ffill()

def adicionar_indicadores(df):
    if len(df) < 50: return df
    df = df.copy()
    
    # Médias Móveis
    df['EMA9'] = ta.ema(df['Close'], length=9)
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['SMA200'] = ta.sma(df['Close'], length=200)
    
    # Indicadores de Momento e Força
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=14, d=3, smooth_k=3)
    df = pd.concat([df, stoch], axis=1)
    
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx], axis=1)
    
    # SuperTrend
    strend = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
    df = pd.concat([df, strend], axis=1)
    
    return df

# --- INTERFACE SIDEBAR ---
st.sidebar.header("⚙️ Configurações")
ticker = st.sidebar.text_input("Digite o Ticker (ex: NVDA, AAPL, PETR4.SA)", "NVDA").upper()
btn_analisar = st.sidebar.button("🚀 Analisar Agora", use_container_width=True)

# --- CORPO DO DASHBOARD ---
st.title(f"📊 Análise Técnica: {ticker}")

if btn_analisar:
    with st.spinner(f"Buscando dados de {ticker}..."):
        df_raw = baixar_dados(ticker)
        
        if df_raw.empty:
            st.error("❌ Ticker não encontrado ou sem dados disponíveis.")
        else:
            df = adicionar_indicadores(df_raw)
            dados_atuais = df.iloc[-1]
            
            # --- MÉTRICAS PRINCIPAIS ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Preço Atual", f"${dados_atuais['Close']:.2f}")
            
            adx_val = dados_atuais['ADX_14']
            m2.metric("Força da Tendência (ADX)", f"{adx_val:.1f}", 
                      "Forte" if adx_val > 25 else "Fraca", delta_color="normal")
            
            rsi_val = dados_atuais['RSI']
            m3.metric("RSI (14)", f"{rsi_val:.1f}", 
                      "Sobrecomprado" if rsi_val > 70 else "Sobrevendido" if rsi_val < 30 else "Neutro")
            
            st_dir = dados_atuais['SUPERTd_10_3.0']
            m4.metric("Tendência (SuperTrend)", "📈 ALTA" if st_dir == 1 else "📉 BAIXA")

            # --- GRÁFICO ---
            fig = go.Figure()
            # Candlesticks
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name="Preço"
            ))
            # Médias
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], name="EMA 9", line=dict(color='cyan', width=1.5)))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name="SMA 200", line=dict(color='white', width=2, dash='dash')))
            
            fig.update_layout(
                height=600, 
                template="plotly_dark", 
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- CHECKLIST DE ESTRATÉGIA ---
            st.subheader("💡 Checklist de Swing Trade")
            c1, c2 = st.columns(2)
            
            with c1:
                st.info("**Sinais de Alta**")
                st.write(f"{'✅' if dados_atuais['Close'] > dados_atuais['SMA200'] else '❌'} Acima da média 200 (Tendência Longa)")
                st.write(f"{'✅' if st_dir == 1 else '❌'} SuperTrend confirmando alta")
                st.write(f"{'✅' if adx_val > 25 else '⚠️'} Tendência com força (ADX > 25)")
            
            with c2:
                st.info("**Níveis de Exaustão**")
                st.write(f"{'⚠️ Cuidado' if rsi_val > 70 else '✅ OK'} RSI abaixo de 70 (Não está esticado)")
                st.write(f"{'✅' if dados_atuais['STOCHk_14_3_3'] < 80 else '⚠️'} Estocástico fora da sobrecompra")

st.markdown("---")
st.caption("Aviso: Esta ferramenta é para fins educacionais. Investimentos envolvem risco.")