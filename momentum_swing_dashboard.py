import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pandas_ta as ta
import warnings

# Configurações de página e avisos
warnings.filterwarnings("ignore")
st.set_page_config(page_title="Pro Momentum Dashboard", layout="wide")

# --- FUNÇÕES DE PROCESSAMENTO ---

@st.cache_data(ttl=300)
def baixar_dados(ticker):
    # Pega 2 anos para garantir o cálculo da SMA200
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    
    if df.empty:
        return pd.DataFrame()

    # CORREÇÃO DE ERRO: Achatar colunas multi-index (comum no yfinance novo)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Remove colunas duplicadas e preenche vazios
    df = df.loc[:, ~df.columns.duplicated()]
    return df.dropna(how='all').ffill()

def adicionar_indicadores(df):
    if len(df) < 50: 
        return df
    
    df = df.copy()
    
    # Médias Móveis
    df['EMA9'] = ta.ema(df['Close'], length=9)
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['SMA200'] = ta.sma(df['Close'], length=200)
    
    # Indicadores de Momento e Força
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # Estocástico
    stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=14, d=3, smooth_k=3)
    df = pd.concat([df, stoch], axis=1)
    
    # ADX
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx], axis=1)
    
    # SuperTrend
    strend = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
    df = pd.concat([df, strend], axis=1)
    
    return df

# --- INTERFACE SIDEBAR ---
st.sidebar.header("⚙️ Configurações")
ticker_input = st.sidebar.text_input("Digite o Ticker (ex: NVDA, AAPL, PETR4.SA)", "NVDA").upper().strip()
btn_analisar = st.sidebar.button("🚀 Analisar Agora", use_container_width=True)

# --- CORPO DO DASHBOARD ---
st.title(f"📊 Dashboard de Momentum: {ticker_input}")

if btn_analisar:
    with st.spinner(f"Processando dados de {ticker_input}..."):
        df_raw = baixar_dados(ticker_input)
        
        if df_raw.empty:
            st.error(f"❌ Não foi possível encontrar dados para o ticker: {ticker_input}")
        else:
            # Adiciona indicadores
            df = adicionar_indicadores(df_raw)
            
            # Pega a última linha e converte explicitamente para valores escalares (float)
            # Isso evita o erro de "TypeError" ao formatar as métricas
            dados_atuais = df.iloc[-1]
            
            try:
                preco_atual = float(dados_atuais['Close'])
                rsi_val = float(dados_atuais['RSI'])
                adx_val = float(dados_atuais['ADX_14'])
                st_dir = int(dados_atuais['SUPERTd_10_3.0'])
                stoch_k = float(dados_atuais['STOCHk_14_3_3'])
                sma200 = float(dados_atuais['SMA200']) if not pd.isna(dados_atuais['SMA200']) else preco_atual
                
                # --- EXIBIÇÃO DE MÉTRICAS ---
                m1, m2, m3, m4 = st.columns(4)
                
                m1.metric("Preço Atual", f"${preco_atual:.2f}")
                
                m2.metric("Força da Tendência (ADX)", f"{adx_val:.1f}", 
                          "Forte" if adx_val > 25 else "Fraca",
                          delta_color="normal")
                
                m3.metric("RSI (14)", f"{rsi_val:.1f}", 
                          "Sobrecomprado" if rsi_val > 70 else "Sobrevendido" if rsi_val < 30 else "Neutro")
                
                m4.metric("SuperTrend", "📈 ALTA" if st_dir == 1 else "📉 BAIXA")

                # --- GRÁFICO INTERATIVO ---
                fig = go.Figure()
                
                # Candlesticks (Últimos 120 dias para melhor visualização)
                df_plot = df.tail(120)
                fig.add_trace(go.Candlestick(
                    x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                    low=df_plot['Low'], close=df_plot['Close'], name="Preço"
                ))
                
                # Médias e SuperTrend
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA9'], name="EMA 9", line=dict(color='cyan', width=1.5)))
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name="SMA 200", line=dict(color='white', width=2, dash='dash')))
                
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
                    st.info("**Análise de Tendência**")
                    st.write(f"{'✅' if preco_atual > sma200 else '❌'} Preço acima da SMA 200")
                    st.write(f"{'✅' if st_dir == 1 else '❌'} SuperTrend confirma viés de Alta")
                    st.write(f"{'✅' if adx_val > 25 else '⚠️'} Tendência com força real (ADX > 25)")
                
                with c2:
                    st.info("**Timing de Entrada**")
                    st.write(f"{'✅ OK' if rsi_val < 70 else '⚠️ Esticado'} RSI (Não está em sobrecompra)")
                    st.write(f"{'✅ OK' if stoch_k < 80 else '⚠️ Esticado'} Estocástico (Espaço para subir)")
                    st.write(f"{'✅' if preco_atual > float(dados_atuais['EMA9']) else '❌'} Preço acima da EMA 9 (Momento)")

            except Exception as e:
                st.warning(f"Alguns indicadores ainda estão sendo calculados ou ticker tem dados insuficientes. Erro: {e}")

st.markdown("---")
st.caption("Aviso: Esta ferramenta é automática e baseada em dados históricos. Não constitui recomendação de investimento.")