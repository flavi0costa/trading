import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Predator Pro Ultra: Tactical Edition", layout="wide")

# --- LISTA TOP 50 SP500 ---
TOP_50_SP500 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'V', 'UNH',
    'JNJ', 'XOM', 'WMT', 'JPM', 'MA', 'PG', 'AVGO', 'ORCL', 'HD', 'CVX',
    'COST', 'ABBV', 'LLY', 'BAC', 'ADBE', 'PEP', 'CSCO', 'TMO', 'CRM', 'WFC',
    'ACN', 'NFLX', 'KO', 'ABT', 'DHR', 'LIN', 'DIS', 'TXN', 'INTC', 'PM',
    'AMD', 'VZ', 'AMAT', 'QCOM', 'PFE', 'IBM', 'UNP', 'GS', 'INTU', 'HON'
]

# --- SIDEBAR: PARÂMETROS ---
st.sidebar.header("🛡️ Gestão de Risco & RSI")
multiplicador_stop = st.sidebar.slider("Multiplicador Stop Loss (ATR)", 1.0, 3.5, 2.0, 0.5)
multiplicador_alvo = st.sidebar.slider("Multiplicador Alvo (ATR)", 2.0, 6.0, 4.0, 0.5)
rsi_limite = st.sidebar.slider("RSI Sobrecompra", 60, 80, 70)

# --- FUNÇÃO TÉCNICA ROBUSTA ---
def processar_dados_completo(ticker):
    try:
        # Baixa ativo + SPY para comparação de força
        data = yf.download([ticker, 'SPY'], period="2y", interval="1d", progress=False)
        
        if data.empty: return None
        
        # Ajuste para o novo formato do yfinance
        df = data['Close'][[ticker]].rename(columns={ticker: 'Close'})
        df['High'] = data['High'][ticker]
        df['Low'] = data['Low'][ticker]
        df['Open'] = data['Open'][ticker]
        df['Volume'] = data['Volume'][ticker]
        df['SPY_Close'] = data['Close']['SPY']

        # Indicadores Base
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Bandas de Bollinger (Captura dinâmica de nomes)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        
        # TTM Squeeze
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None: df = pd.concat([df, sqz], axis=1)
        
        # Fluxo Institucional
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_Avg']
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
        return None

# --- UI ---
st.title("🏹 Predator Pro: Full Tactical Dashboard")
tab1, tab2 = st.tabs(["🚀 Scanner Top 50", "🔍 Análise Manual + Força Relativa"])

# --- ABA 1: SCANNER ---
with tab1:
    if st.button("🚀 Executar Varredura"):
        resultados = []
        bar = st.progress(0)
        for i, t in enumerate(TOP_50_SP500):
            df = processar_dados_completo(t)
            if df is not None:
                u = df.iloc[-1]
                p = df.iloc[-2]
                if u['Close'] > u['EMA_200'] and (u['SQZ_ON'] == 1 or (u['SQZ_ON'] == 0 and p['SQZ_ON'] == 1)):
                    resultados.append({
                        "Ticker": t, "Preço": round(float(u['Close']), 2),
                        "RSI": round(float(u['RSI']), 1), "RVOL": round(float(u['RVOL']), 2),
                        "Estado": "🔥 ROMPEU" if u['SQZ_ON'] == 0 else "🟡 SQUEEZE"
                    })
            bar.progress((i + 1) / len(TOP_50_SP500))
        if resultados: st.dataframe(pd.DataFrame(resultados), use_container_width=True)
        else: st.info("Nenhum sinal detectado.")

# --- ABA 2: MANUAL ---
with tab2:
    ticker_user = st.text_input("Ticker", "NVDA").upper()
    if st.button("Analisar"):
        df = processar_dados_completo(ticker_user)
        if df is not None:
            df_plot = df.tail(126)
            u = df_plot.iloc[-1]
            
            # Identificar colunas das Bandas (Fix para o KeyError)
            col_bbu = [c for c in df_plot.columns if c.startswith('BBU')][0]
            col_bbl = [c for c in df_plot.columns if c.startswith('BBL')][0]
            
            stop = float(u['Close'] - (u['ATR'] * multiplicador_stop))
            alvo = float(u['Close'] + (u['ATR'] * multiplicador_alvo))
            
            # Métricas
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço", f"{u['Close']:.2f}")
            c2.metric("RSI", f"{u['RSI']:.1f}")
            c3.metric("Stop ATR", f"{stop:.2f}")
            c4.metric("Alvo ATR", f"{alvo:.2f}")

            # Subplots
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])

            # Gráfico Principal
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[col_bbu], name="BB Upper", line=dict(color='rgba(173, 216, 230, 0.4)', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[col_bbl], name="BB Lower", line=dict(color='rgba(173, 216, 230, 0.4)', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA_200'], name="EMA 200", line=dict(color='yellow')), row=1, col=1)
            
            fig.add_hline(y=stop, line_dash="dash", line_color="red", row=1, col=1)
            fig.add_hline(y=alvo, line_dash="dash", line_color="green", row=1, col=1)

            # RSI
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=rsi_limite, line_dash="dot", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

            # Volume
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name="Volume"), row=3, col=1)

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=850)
            st.plotly_chart(fig, use_container_width=True)

            # DIAGNÓSTICO
            st.subheader("🏁 Veredito Predator")
            correlacao = df['Close'].tail(20).corr(df['SPY_Close'].tail(20))
            
            c_res1, c_res2 = st.columns(2)
            with c_res1:
                if correlacao > 0.8: st.info(f"🔗 Correlação Alta com S&P 500 ({correlacao:.2f})")
                else: st.success(f"💪 Força Relativa: O ativo move-se independente do mercado ({correlacao:.2f})")
                
            
            with c_res2:
                if u['RSI'] > rsi_limite: st.warning("⚠️ SOBRECOMPRADO: RSI alto, aguarde recuo.")
                elif u['RSI'] < 35: st.success("🟢 SOBREVENDIDO: Potencial ponto de entrada por exaustão.")
                

        else: st.error("Erro ao carregar dados.")