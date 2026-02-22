import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Predator Pro: Definitive Edition", layout="wide")

# --- LISTA TOP 50 SP500 ---
TOP_50_SP500 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'V', 'UNH',
    'JNJ', 'XOM', 'WMT', 'JPM', 'MA', 'PG', 'AVGO', 'ORCL', 'HD', 'CVX',
    'COST', 'ABBV', 'LLY', 'BAC', 'ADBE', 'PEP', 'CSCO', 'TMO', 'CRM', 'WFC',
    'ACN', 'NFLX', 'KO', 'ABT', 'DHR', 'LIN', 'DIS', 'TXN', 'INTC', 'PM',
    'AMD', 'VZ', 'AMAT', 'QCOM', 'PFE', 'IBM', 'UNP', 'GS', 'INTU', 'HON'
]

# --- SIDEBAR (Sempre visível) ---
st.sidebar.header("🛡️ Gestão de Risco & Parâmetros")
multi_stop = st.sidebar.slider("Multiplicador Stop Loss (ATR)", 1.0, 3.5, 2.0, 0.5)
multi_alvo = st.sidebar.slider("Multiplicador Alvo (ATR)", 2.0, 6.0, 4.0, 0.5)
rsi_limite = st.sidebar.slider("RSI Sobrecompra", 60, 80, 70)

st.sidebar.markdown("---")
st.sidebar.header("💰 Simulador de Profit")
capital_total = st.sidebar.number_input("Capital Disponível ($)", value=10000)
risco_por_trade = st.sidebar.slider("Risco por Trade (%)", 0.5, 5.0, 1.0, 0.5)

# --- FUNÇÃO DE CÁLCULO CORE (Garante que nada se perde) ---
def calcular_tudo(ticker):
    try:
        # Baixamos o Ativo + SPY (para força relativa)
        data = yf.download([ticker, 'SPY'], period="2y", interval="1d", progress=False)
        if data.empty: return None
        
        # Isolamos o Ticker (Fix para o erro de colunas do yfinance)
        df = data['Close'][[ticker]].rename(columns={ticker: 'Close'})
        df['High'] = data['High'][ticker]
        df['Low'] = data['Low'][ticker]
        df['Open'] = data['Open'][ticker]
        df['Volume'] = data['Volume'][ticker]
        df['SPY_Close'] = data['Close']['SPY']

        # 1. Indicadores Base
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 2. Bandas de Bollinger e Squeeze
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None: df = pd.concat([df, sqz], axis=1)
        
        # 3. Fluxo e Momentum
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_Avg']
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        # 4. Divergência (Nova Função)
        df['Div_Bull'] = (df['Low'] < df['Low'].shift(5)) & (df['RSI'] > df['RSI'].shift(5))

        return df
    except Exception as e:
        return None

# --- INTERFACE ---
st.title("🏹 Predator Pro Ultimate")

tab1, tab2 = st.tabs(["🚀 Scanner Automático Top 50", "🔍 Análise Manual & Profit"])

# --- ABA 1: SCANNER (Como estava antes) ---
with tab1:
    if st.button("Iniciar Varredura S&P 500"):
        resultados = []
        bar = st.progress(0)
        for i, t in enumerate(TOP_50_SP500):
            df = calcular_tudo(t)
            if df is not None:
                u = df.iloc[-1]
                p = df.iloc[-2]
                # Filtro de Compra: Tendência + Squeeze
                if u['Close'] > u['EMA_200'] and (u['SQZ_ON'] == 1 or (u['SQZ_ON'] == 0 and p['SQZ_ON'] == 1)):
                    resultados.append({
                        "Ticker": t, "Preço": round(float(u['Close']), 2),
                        "RSI": round(float(u['RSI']), 1), "RVOL": round(float(u['RVOL']), 2),
                        "Sinal": "🔥 ROMPEU" if u['SQZ_ON'] == 0 else "🟡 SQUEEZE"
                    })
            bar.progress((i + 1) / len(TOP_50_SP500))
        if resultados:
            st.dataframe(pd.DataFrame(resultados), use_container_width=True)
        else:
            st.info("Nenhum sinal detectado agora.")

# --- ABA 2: ANÁLISE MANUAL (Recuperada e Melhorada) ---
with tab2:
    ticker_user = st.text_input("Introduza Ticker", "NVDA").upper()
    if st.button("Analisar Ativo"):
        df = calcular_tudo(ticker_user)
        if df is not None:
            df_plot = df.tail(126)
            u = df_plot.iloc[-1]
            
            # Gestão de Risco
            stop = float(u['Close'] - (u['ATR'] * multi_stop))
            alvo = float(u['Close'] + (u['ATR'] * multi_alvo))
            qty = int((capital_total * (risco_por_trade/100)) / (u['Close'] - stop)) if (u['Close']-stop)>0 else 0
            
            # Métricas
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço", f"{u['Close']:.2f}")
            c2.metric("Quantidade", f"{qty} un")
            c3.metric("Profit Potencial", f"${(qty*(alvo-u['Close'])):.2f}")
            c4.metric("Money Flow", f"{u['MFI']:.0f}")

            # Identificar Colunas BB
            col_bbu = [c for c in df_plot.columns if c.startswith('BBU')][0]
            col_bbl = [c for c in df_plot.columns if c.startswith('BBL')][0]

            # Gráfico Full
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
            
            # Row 1: Preço + BB + EMA + Alvos
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Preço"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[col_bbu], name="BB Upper", line=dict(color='rgba(173,216,230,0.3)')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[col_bbl], name="BB Lower", line=dict(color='rgba(173,216,230,0.3)')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA_200'], name="EMA 200", line=dict(color='yellow')), row=1, col=1)
            fig.add_hline(y=stop, line_dash="dash", line_color="red", row=1, col=1)
            fig.add_hline(y=alvo, line_dash="dash", line_color="green", row=1, col=1)

            # Row 2: RSI
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=rsi_limite, line_dash="dot", line_color="red", row=2, col=1)

            # Row 3: Volume & MACD Hist
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name="Volume"), row=3, col=1)

            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # Diagnóstico das 3 Novas Sugestões
            st.subheader("🎯 Insights Avançados")
            d1, d2, d3 = st.columns(3)
            
            with d1:
                st.write("**Divergência RSI**")
                if u['Div_Bull']: st.success("🎯 Bullish Divergence!")
                else: st.write("Sem divergência clara.")
                [attachment_0](attachment)

            with d2:
                st.write("**Força Relativa (vs SPY)**")
                corr = df['Close'].tail(20).corr(df['SPY_Close'].tail(20))
                st.write(f"Correlação: {corr:.2f}")
                if corr < 0.7: st.success("💪 Força Própria (Alpha)")

            with d3:
                st.write("**Mini-Backtest (Últimos Sinais)**")
                df['Sinal_Hist'] = (df['SQZ_ON'] == 0) & (df['SQZ_ON'].shift(1) == 1)
                acertos = len(df[(df['Sinal_Hist'] == True) & (df['Close'].shift(-10) > df['Close'])])
                total = len(df[df['Sinal_Hist'] == True])
                st.write(f"Sinais Rompidos: {total}")
                st.write(f"Sucesso (10 dias): {acertos/total:.0%}" if total > 0 else "N/A")

        else: st.error("Erro ao carregar ticker.")
