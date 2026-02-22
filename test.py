import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração da Página
st.set_page_config(page_title="S&P 500 Predator", layout="wide")

# --- LISTA DAS 50 MAIS LÍQUIDAS (S&P 500) ---
TOP_50_SP500 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'V', 'UNH',
    'JNJ', 'XOM', 'WMT', 'JPM', 'MA', 'PG', 'AVGO', 'ORCL', 'HD', 'CVX',
    'COST', 'ABBV', 'LLY', 'BAC', 'ADBE', 'PEP', 'CSCO', 'TMO', 'CRM', 'WFC',
    'ACN', 'NFLX', 'KO', 'ABT', 'DHR', 'LIN', 'DIS', 'TXN', 'INTC', 'PM',
    'AMD', 'VZ', 'AMAT', 'QCOM', 'PFE', 'IBM', 'UNP', 'GS', 'INTU', 'HON'
]

# --- FUNÇÃO DE CÁLCULO TÉCNICO ---
def get_analysis(df):
    if df is None or len(df) < 200: return None
    
    # Limpeza de colunas
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 1. Indicadores
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    # 2. Squeeze
    sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
    if sqz is not None:
        df = pd.concat([df, sqz], axis=1)
    
    # 3. MACD
    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)
    
    return df

# --- INTERFACE ---
st.title("🏹 S&P 500 Predictive Dashboard")

tab1, tab2 = st.tabs(["🚀 Scanner Automático (Top 50)", "🔍 Análise Manual (Ticker)"])

# ---------------------------------------------------------
# ABA 1: SCANNER AUTOMÁTICO
# ---------------------------------------------------------
with tab1:
    st.header("Varredura das 50 Ações Mais Líquidas")
    if st.button("Executar Scanner"):
        resultados = []
        progresso = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(TOP_50_SP500):
            status.text(f"Analisando {t}...")
            df_raw = yf.download(t, period="1y", interval="1d", progress=False)
            df = get_analysis(df_raw)
            
            if df is not None:
                ultimo = df.iloc[-1]
                penultimo = df.iloc[-2]
                
                # Critérios de Confluência
                acima_200 = ultimo['Close'] > ultimo['EMA_200']
                rompeu_sqz = (ultimo['SQZ_ON'] == 0 and penultimo['SQZ_ON'] == 1)
                em_sqz = (ultimo['SQZ_ON'] == 1)
                macd_bull = ultimo['MACD_12_26_9'] > ultimo['MACDs_12_26_9']
                
                # Filtro: Mostrar apenas quem está em Squeeze ou Rompendo em Tendência de Alta
                if acima_200 and (rompeu_sqz or em_sqz):
                    resultados.append({
                        "Ticker": t,
                        "Preço": round(ultimo['Close'], 2),
                        "Estado": "🔥 ROMPIMENTO" if rompeu_sqz else "🟡 EM SQUEEZE",
                        "MACD": "Alta" if macd_bull else "Baixa",
                        "Alvo (TP)": round(ultimo['Close'] + (ultimo['ATR'] * 4), 2)
                    })
            progresso.progress((i + 1) / len(TOP_50_SP500))
        
        status.empty()
        if resultados:
            res_df = pd.DataFrame(resultados)
            st.dataframe(res_df.style.applymap(
                lambda x: 'background-color: #004d00' if x == '🔥 ROMPIMENTO' else 'background-color: #4d4d00',
                subset=['Estado']
            ), use_container_width=True)
        else:
            st.info("Nenhuma oportunidade clara detetada no Top 50 hoje.")

# ---------------------------------------------------------
# ABA 2: ANÁLISE MANUAL
# ---------------------------------------------------------
with tab2:
    st.header("Análise Detalhada de Ticker")
    user_ticker = st.text_input("Introduza o Ticker (ex: NVDA, PETR4.SA, BTC-USD):", "NVDA").upper()
    
    if st.button("Analisar Ticker"):
        df_raw = yf.download(user_ticker, period="2y", interval="1d", progress=False)
        df = get_analysis(df_raw)
        
        if df is not None:
            # Gráfico de Subplots
            df_plot = df.tail(126) # Últimos 6 meses para visão clara
            ultimo = df_plot.iloc[-1]
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.05, row_heights=[0.7, 0.3])

            # Preço e EMA 200
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], 
                                       low=df_plot['Low'], close=df_plot['Close'], name="Preço"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA_200'], name="EMA 200", line=dict(color='yellow')), row=1, col=1)
            
            # Alvo e Stop baseados em ATR
            stop = ultimo['Close'] - (ultimo['ATR'] * 2)
            alvo = ultimo['Close'] + (ultimo['ATR'] * 4)
            fig.add_hline(y=stop, line_dash="dash", line_color="red", row=1, col=1)
            fig.add_hline(y=alvo, line_dash="dash", line_color="green", row=1, col=1)

            # MACD
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['MACDh_12_26_9'], name="MACD Hist"), row=2, col=1)

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=700)
            st.plotly_chart(fig, use_container_width=True)
            
            # Cards de Diagnóstico
            c1, c2, c3 = st.columns(3)
            c1.metric("Preço Atual", f"{ultimo['Close']:.2f}")
            c2.metric("Stop Loss", f"{stop:.2f}")
            c3.metric("Take Profit", f"{alvo:.2f}")
            
            # Texto Preditivo
            if ultimo['SQZ_ON'] == 1:
                st.warning("⚠️ O ativo está em fase de acumulação (Squeeze). Aguarde o rompimento para confirmar a direção.")
                
            elif ultimo['Close'] > ultimo['EMA_200']:
                st.success("✅ Ativo em tendência de alta institucional. Procure por entradas em correções.")
        else:
            st.error("Erro ao carregar ticker. Verifique se introduziu o nome correto.")