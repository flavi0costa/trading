import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Predator Pro Ultra: RSI & Bollinger", layout="wide")

# --- LISTA TOP 50 SP500 ---
TOP_50_SP500 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'V', 'UNH',
    'JNJ', 'XOM', 'WMT', 'JPM', 'MA', 'PG', 'AVGO', 'ORCL', 'HD', 'CVX',
    'COST', 'ABBV', 'LLY', 'BAC', 'ADBE', 'PEP', 'CSCO', 'TMO', 'CRM', 'WFC',
    'ACN', 'NFLX', 'KO', 'ABT', 'DHR', 'LIN', 'DIS', 'TXN', 'INTC', 'PM',
    'AMD', 'VZ', 'AMAT', 'QCOM', 'PFE', 'IBM', 'UNP', 'GS', 'INTU', 'HON'
]

# --- SIDEBAR: GESTÃO DE RISCO ---
st.sidebar.header("🛡️ Parâmetros de Trading")
multiplicador_stop = st.sidebar.slider("Multiplicador Stop Loss (ATR)", 1.0, 3.5, 2.0, 0.5)
multiplicador_alvo = st.sidebar.slider("Multiplicador Alvo (ATR)", 2.0, 6.0, 4.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.header("📉 Níveis RSI")
rsi_sobrecompra = st.sidebar.number_input("RSI Sobrecompra", value=70)
rsi_sobrevenda = st.sidebar.number_input("RSI Sobrevenda", value=30)

# --- FUNÇÃO DE CÁLCULO TÉCNICO COMPLETO ---
def processar_dados_completo(ticker):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 200: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Indicadores Base
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Bandas de Bollinger
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        
        # TTM Squeeze
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None: df = pd.concat([df, sqz], axis=1)
        
        # Fluxo Institucional
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_Avg']
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar {ticker}: {e}")
        return None

# --- UI PRINCIPAL ---
st.title("🏹 Predator Pro: Tactical Dashboard")
tab1, tab2 = st.tabs(["🚀 Scanner Top 50 SP500", "🔍 Análise Manual & Gestão"])

# --- ABA 1: SCANNER ---
with tab1:
    if st.button("🚀 Iniciar Varredura"):
        resultados = []
        progresso = st.progress(0)
        for i, t in enumerate(TOP_50_SP500):
            df = processar_dados_completo(t)
            if df is not None:
                u = df.iloc[-1]
                p = df.iloc[-2]
                if u['Close'] > u['EMA_200'] and (u['SQZ_ON'] == 1 or (u['SQZ_ON'] == 0 and p['SQZ_ON'] == 1)):
                    resultados.append({
                        "Ticker": t, "Preço": round(float(u['Close']), 2),
                        "RSI": round(float(u['RSI']), 1),
                        "RVOL": round(float(u['RVOL']), 2),
                        "MFI": round(float(u['MFI']), 0),
                        "Estado": "🔥 ROMPEU" if u['SQZ_ON'] == 0 else "🟡 ACUMULANDO"
                    })
            progresso.progress((i + 1) / len(TOP_50_SP500))
        if resultados:
            st.dataframe(pd.DataFrame(resultados), use_container_width=True)
        else: st.info("Nenhuma oportunidade encontrada.")

# --- ABA 2: MANUAL ---
with tab2:
    ticker_input = st.text_input("Introduza Ticker", "NVDA").upper()
    if st.button("Analisar Flow & Risco"):
        df = processar_dados_completo(ticker_input)
        if df is not None:
            df_plot = df.tail(126)
            u = df_plot.iloc[-1]
            
            stop_calc = float(u['Close'] - (u['ATR'] * multiplicador_stop))
            alvo_calc = float(u['Close'] + (u['ATR'] * multiplicador_alvo))
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço", f"{u['Close']:.2f}")
            c2.metric("RSI (14)", f"{u['RSI']:.1f}")
            c3.metric("Stop Loss", f"{stop_calc:.2f}")
            c4.metric("Alvo Sugerido", f"{alvo_calc:.2f}")

            # Gráfico com Bollinger e RSI
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])

            # Candlestick + Bollinger + EMA 200
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Preço"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BBU_20_2.0'], name="Banda Sup", line=dict(color='gray', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['BBL_20_2.0'], name="Banda Inf", line=dict(color='gray', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA_200'], name="EMA 200", line=dict(color='yellow')), row=1, col=1)
            
            fig.add_hline(y=stop_calc, line_dash="dash", line_color="red", row=1, col=1)
            fig.add_hline(y=alvo_calc, line_dash="dash", line_color="green", row=1, col=1)

            # RSI no segundo gráfico
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=rsi_sobrecompra, line_dash="dot", line_color="red", row=2, col=1)
            fig.add_hline(y=rsi_sobrevenda, line_dash="dot", line_color="green", row=2, col=1)

            # Volume no terceiro
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name="Volume"), row=3, col=1)

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=900)
            st.plotly_chart(fig, use_container_width=True)

            # ALERTAS RSI
            if u['RSI'] > rsi_sobrecompra:
                st.error(f"⚠️ ATENÇÃO: Ativo sobrecomprado (RSI: {u['RSI']:.1f}). Risco de correção alto.")
                
            elif u['RSI'] < rsi_sobrevenda:
                st.success(f"✅ OPORTUNIDADE: Ativo sobrevenda (RSI: {u['RSI']:.1f}). Possível repique técnico.")
                
            
            if u['Close'] > u['BBU_20_2.0']:
                st.warning("Preço acima da Banda de Bollinger Superior. Volatilidade extrema.")
                

        else: st.error("Erro nos dados.")