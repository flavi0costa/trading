import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pandas_ta as ta
import warnings

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Pro Momentum Dashboard", layout="wide")

@st.cache_data(ttl=300)
def baixar_dados(ticker):
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]
    return df.dropna(how='all').ffill()

def adicionar_indicadores(df):
    if len(df) < 50: return df
    df = df.copy()
    
    # Médias
    df['EMA9'] = ta.ema(df['Close'], length=9)
    df['SMA200'] = ta.sma(df['Close'], length=200)
    
    # RSI
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

# --- INTERFACE ---
st.sidebar.header("⚙️ Configurações")
ticker_input = st.sidebar.text_input("Ticker", "NVDA").upper().strip()
btn_analisar = st.sidebar.button("🚀 Analisar Agora", use_container_width=True)

st.title(f"📊 Dashboard: {ticker_input}")

if btn_analisar:
    with st.spinner("Processando..."):
        df = baixar_dados(ticker_input)
        
        if df.empty:
            st.error("Ticker não encontrado.")
        else:
            df = adicionar_indicadores(df)
            dados_atuais = df.iloc[-1]
            
            try:
                # --- BUSCA DINÂMICA DE COLUNAS (O SEGREDO DA CORREÇÃO) ---
                # Procura a coluna do SuperTrend Direction (começa com SUPERTd)
                col_st_dir = [c for c in df.columns if c.startswith('SUPERTd')][0]
                # Procura a coluna do valor do SuperTrend (começa com SUPERT_)
                col_st_val = [c for c in df.columns if c.startswith('SUPERT_') and not c.startswith('SUPERTd')][0]
                # Procura a coluna do ADX
                col_adx = [c for c in df.columns if c.startswith('ADX')][0]
                # Procura a coluna do Estocástico %K
                col_stoch = [c for c in df.columns if c.startswith('STOCHk')][0]

                # Conversão segura
                preco_atual = float(dados_atuais['Close'])
                rsi_val = float(dados_atuais['RSI'])
                adx_val = float(dados_atuais[col_adx])
                st_dir = int(dados_atuais[col_st_dir])
                stoch_k = float(dados_atuais[col_stoch])

                # --- EXIBIÇÃO ---
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Preço", f"${preco_atual:.2f}")
                m2.metric("ADX (Força)", f"{adx_val:.1f}", "Tendência Forte" if adx_val > 25 else "Fraca")
                m3.metric("RSI", f"{rsi_val:.1f}")
                m4.metric("SuperTrend", "📈 ALTA" if st_dir == 1 else "📉 BAIXA")

                # Gráfico
                df_plot = df.tail(120)
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                                             low=df_plot['Low'], close=df_plot['Close'], name="Preço"))
                
                # Linha do SuperTrend no gráfico
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[col_st_val], name="SuperTrend", 
                                         line=dict(color='yellow', width=1, dash='dot')))
                
                fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                # Checklist
                st.subheader("💡 Checklist")
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"{'✅' if st_dir == 1 else '❌'} SuperTrend")
                    st.write(f"{'✅' if adx_val > 25 else '⚠️'} Força (ADX)")
                with c2:
                    st.write(f"{'✅' if rsi_val < 70 else '⚠️'} Não está sobrecomprado")
                    st.write(f"{'✅' if preco_atual > float(dados_atuais['EMA9']) else '❌'} Acima da EMA9")

            except Exception as e:
                st.error(f"Erro ao processar indicadores: {e}")
                st.info("Dica: Tente um ticker com mais histórico (ex: AAPL) ou verifique se o pandas-ta está instalado.")