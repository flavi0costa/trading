import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração da Página
st.set_page_config(page_title="Predator Pro: Institutional Edition", layout="wide")

# --- LISTA TOP 50 MAIS LÍQUIDAS ---
TOP_50_SP500 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'V', 'UNH',
    'JNJ', 'XOM', 'WMT', 'JPM', 'MA', 'PG', 'AVGO', 'ORCL', 'HD', 'CVX',
    'COST', 'ABBV', 'LLY', 'BAC', 'ADBE', 'PEP', 'CSCO', 'TMO', 'CRM', 'WFC',
    'ACN', 'NFLX', 'KO', 'ABT', 'DHR', 'LIN', 'DIS', 'TXN', 'INTC', 'PM',
    'AMD', 'VZ', 'AMAT', 'QCOM', 'PFE', 'IBM', 'UNP', 'GS', 'INTU', 'HON'
]

# --- FUNÇÃO DE PROCESSAMENTO TÉCNICO (O Cérebro) ---
def processar_dados_completo(ticker, periodo="2y"):
    try:
        df = yf.download(ticker, period=periodo, interval="1d", progress=False)
        if df.empty or len(df) < 200: return None
        
        # Correção MultiIndex yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 1. Indicadores Base (Antigos)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None: df = pd.concat([df, sqz], axis=1)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        # 2. Indicadores de Fluxo Institucional (Novos)
        # RVOL: Volume atual vs Média de 20 dias (Detector de Dark Pool/Baleias)
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_Avg']
        # MFI: Money Flow Index (Sentimento de Opções/Fluxo de Dinheiro)
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        
        return df
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        return None

# --- INTERFACE ---
st.title("🏹 Predator Pro: Scanner de Confluência e Fluxo")

tab1, tab2 = st.tabs(["🚀 Scanner S&P 500 (Automático)", "🔍 Análise Detalhada (Manual)"])

# ---------------------------------------------------------
# ABA 1: SCANNER AUTOMÁTICO
# ---------------------------------------------------------
with tab1:
    if st.button("Executar Varredura Pro"):
        resultados = []
        progresso = st.progress(0)
        
        for i, t in enumerate(TOP_50_SP500):
            df = processar_dados_completo(t)
            if df is not None:
                u = df.iloc[-1]
                p = df.iloc[-2]
                
                # Lógica: Tendência Alta + Squeeze (Ativo ou Rompendo)
                if u['Close'] > u['EMA_200'] and (u['SQZ_ON'] == 1 or (u['SQZ_ON'] == 0 and p['SQZ_ON'] == 1)):
                    resultados.append({
                        "Ticker": t,
                        "Preço": round(float(u['Close']), 2),
                        "RVOL (Flow)": round(float(u['RVOL']), 2),
                        "MFI (Money)": round(float(u['MFI']), 0),
                        "Estado": "🔥 ROMPEU" if u['SQZ_ON'] == 0 else "🟡 SQUEEZE",
                        "MACD": "Bullish" if u['MACD_12_26_9'] > u['MACDs_12_26_9'] else "Bearish"
                    })
            progresso.progress((i + 1) / len(TOP_50_SP500))
        
        if resultados:
            res_df = pd.DataFrame(resultados)
            st.dataframe(res_df.style.applymap(
                lambda x: 'background-color: #004d00' if x == '🔥 ROMPEU' else 'background-color: #4d4d00',
                subset=['Estado']
            ), use_container_width=True)
        else:
            st.info("Nenhuma confluência institucional encontrada agora.")

# ---------------------------------------------------------
# ABA 2: ANÁLISE MANUAL + FLOW
# ---------------------------------------------------------
with tab2:
    ticker_user = st.text_input("Introduza Ticker (ex: NVDA, AAPL, PETR4.SA)", "NVDA").upper()
    if st.button("Analisar Flow & Gráfico"):
        df = processar_dados_completo(ticker_user)
        if df is not None:
            df_plot = df.tail(126)
            u = df_plot.iloc[-1]
            
            # --- DASHBOARD DE MÉTRICAS ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço", f"{u['Close']:.2f}")
            c2.metric("Relative Volume", f"{u['RVOL']:.2f}x")
            c3.metric("Money Flow (MFI)", f"{u['MFI']:.0f}")
            c4.metric("Tendência", "ALTA" if u['Close'] > u['EMA_200'] else "BAIXA")

            # --- GRÁFICO COM SUBPLOTS ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.03, row_heights=[0.7, 0.3])

            # Candlestick e EMA 200
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], 
                                       low=df_plot['Low'], close=df_plot['Close'], name="Preço"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA_200'], name="EMA 200", line=dict(color='yellow')), row=1, col=1)
            
            # Volume Colorido (Proxy de Flow)
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name="Volume"), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=700)
            st.plotly_chart(fig, use_container_width=True)

            # --- CONCLUSÃO DO FLUXO ---
            st.subheader("🕵️ Veredito Institucional")
            if u['RVOL'] > 1.5 and u['MFI'] > 60:
                st.success(f"💎 **ALERTA DE DINHEIRO PESADO:** Detectado volume anómalo ({u['RVOL']:.2f}x) e pressão de compra institucional.")
                
            elif u['SQZ_ON'] == 1:
                st.warning("⚠️ **SQUEEZE ATIVO:** Volatilidade comprimida. O gráfico está pronto para explodir.")
                
            else:
                st.info("Ativo em movimentação de varejo estável. Sem sinais de 'Unusual Flow' no momento.")

        else:
            st.error("Erro ao carregar ticker ou histórico insuficiente para EMA 200.")