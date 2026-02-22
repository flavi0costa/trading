import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Predator Pro: Definitive", layout="wide")

# --- LISTA TOP 50 SP500 (Recuperada) ---
TOP_50_SP500 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'V', 'UNH',
    'JNJ', 'XOM', 'WMT', 'JPM', 'MA', 'PG', 'AVGO', 'ORCL', 'HD', 'CVX',
    'COST', 'ABBV', 'LLY', 'BAC', 'ADBE', 'PEP', 'CSCO', 'TMO', 'CRM', 'WFC',
    'ACN', 'NFLX', 'KO', 'ABT', 'DHR', 'LIN', 'DIS', 'TXN', 'INTC', 'PM',
    'AMD', 'VZ', 'AMAT', 'QCOM', 'PFE', 'IBM', 'UNP', 'GS', 'INTU', 'HON'
]

# --- SIDEBAR: GESTÃO DE RISCO ---
st.sidebar.header("🛡️ Gestão de Risco & Parâmetros")
multi_stop = st.sidebar.slider("Multiplicador Stop Loss (ATR)", 1.0, 3.5, 2.0, 0.5)
multi_alvo = st.sidebar.slider("Multiplicador Alvo (ATR)", 2.0, 6.0, 4.0, 0.5)
rsi_limite = st.sidebar.slider("RSI Sobrecompra", 60, 80, 70)

st.sidebar.markdown("---")
st.sidebar.header("💰 Simulador de Profit")
capital_total = st.sidebar.number_input("Capital Disponível ($)", value=10000)
risco_por_trade = st.sidebar.slider("Risco por Trade (%)", 0.5, 5.0, 1.0, 0.5)

# --- FUNÇÃO DE CÁLCULO CORE ---
def calcular_tudo(ticker):
    try:
        # Baixamos Ativo + SPY para correlação/força relativa
        data = yf.download([ticker, 'SPY'], period="2y", interval="1d", progress=False)
        if data.empty: return None
        
        # Tratamento de colunas (Fix para evitar KeyError)
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
        
        # Bollinger
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        
        # Squeeze
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None: df = pd.concat([df, sqz], axis=1)
        
        # Fluxo e Volume
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_Avg']
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        
        # MACD
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        # Divergência de RSI (Simplificada)
        df['Div_Bull'] = (df['Low'] < df['Low'].shift(5)) & (df['RSI'] > df['RSI'].shift(5))

        return df
    except Exception as e:
        return None

# --- UI ---
st.title("🏹 Predator Pro: Definitive Edition")

tab1, tab2 = st.tabs(["🚀 Scanner Automático Top 50", "🔍 Análise Manual & Profit"])

# --- ABA 1: SCANNER ---
with tab1:
    if st.button("Iniciar Varredura Top 50"):
        resultados = []
        bar = st.progress(0)
        for i, t in enumerate(TOP_50_SP500):
            df = calcular_tudo(t)
            if df is not None:
                u = df.iloc[-1]
                p = df.iloc[-2]
                # Regra: Acima da EMA 200 + Squeeze Ativo ou Rompendo
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
            st.info("Nenhum sinal detectado com os critérios atuais.")

# --- ABA 2: ANÁLISE MANUAL & PROFIT ---
with tab2:
    ticker_user = st.text_input("Ticker para Análise", "NVDA").upper()
    if st.button("Analisar"):
        df = calcular_tudo(ticker_user)
        if df is not None:
            df_p = df.tail(126)
            u = df_p.iloc[-1]
            
            # Cálculo de Gestão de Risco
            stop = float(u['Close'] - (u['ATR'] * multi_stop))
            alvo = float(u['Close'] + (u['ATR'] * multi_alvo))
            dist_stop = u['Close'] - stop
            qty = int((capital_total * (risco_por_trade/100)) / dist_stop) if dist_stop > 0 else 0
            
            # Painel de Métricas
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço", f"{u['Close']:.2f}")
            c2.metric("Qtd. Ações Sugerida", f"{qty}")
            c3.metric("Profit Estimado ($)", f"{(qty*(alvo-u['Close'])):.2f}")
            c4.metric("Money Flow (MFI)", f"{u['MFI']:.0f}")

            # Identificar colunas das Bandas de Bollinger
            col_bbu = [c for c in df_p.columns if c.startswith('BBU')][0]
            col_bbl = [c for c in df_p.columns if c.startswith('BBL')][0]

            # Gráfico de 3 níveis (Preço, RSI, Volume)
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
            
            # 1. Preço + EMA + BB + Stop/Alvo
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Preço"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p[col_bbu], name="BB Superior", line=dict(color='rgba(173,216,230,0.4)', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p[col_bbl], name="BB Inferior", line=dict(color='rgba(173,216,230,0.4)', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA_200'], name="EMA 200", line=dict(color='yellow')), row=1, col=1)
            fig.add_hline(y=stop, line_dash="dash", line_color="red", annotation_text="STOP", row=1, col=1)
            fig.add_hline(y=alvo, line_dash="dash", line_color="green", annotation_text="ALVO", row=1, col=1)

            # 2. RSI
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=rsi_limite, line_dash="dot", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

            # 3. Volume
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name="Volume"), row=3, col=1)

            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # --- INSIGHTS ADICIONAIS (As 3 Sugestões) ---
            st.subheader("🎯 Insights de Execução")
            i1, i2, i3 = st.columns(3)
            
            with i1:
                st.write("**Divergência & Fluxo**")
                if u['Div_Bull']: st.success("🎯 Divergência Bullish detetada!")
                if u['RVOL'] > 1.5: st.info(f"RVOL: {u['RVOL']:.2f}x (Fluxo Alto)")
            
            with i2:
                st.write("**Força Relativa (vs SPY)**")
                correl = df['Close'].tail(20).corr(df['SPY_Close'].tail(20))
                st.write(f"Correlação 20d: {correl:.2f}")
                if correl < 0.7: st.success("💪 Alpha: O ativo tem força própria.")

            with i3:
                st.write("**Histórico de Sinais**")
                # Mini-Backtest simples
                df['Sinal_Hist'] = (df['SQZ_ON'] == 0) & (df['SQZ_ON'].shift(1) == 1)
                trades = df[df['Sinal_Hist'] == True]
                if not trades.empty:
                    taxa_sucesso = (df['Close'].shift(-10) > df['Close']).loc[trades.index].mean()
                    st.write(f"Taxa de acerto (10d): {taxa_sucesso:.0%}")
                else:
                    st.write("Sem sinais recentes.")

        else:
            st.error("Erro ao carregar os dados. Verifique o Ticker.")
