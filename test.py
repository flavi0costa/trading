import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Predator Pro God Mode", layout="wide")

# --- MAPEAMENTO SETORIAL ---
SECTOR_MAP = {
    'AAPL': 'XLK', 'MSFT': 'XLK', 'NVDA': 'XLK', 'AMD': 'XLK', 'ADBE': 'XLK', 'CRM': 'XLK', 'INTC': 'XLK',
    'AMZN': 'XLY', 'TSLA': 'XLY', 'META': 'XLC', 'GOOGL': 'XLC', 'NFLX': 'XLC', 'DIS': 'XLC',
    'JPM': 'XLF', 'BAC': 'XLF', 'GS': 'XLF', 'V': 'XLF', 'MA': 'XLF',
    'XOM': 'XLE', 'CVX': 'XLE', 'PFE': 'XLV', 'UNH': 'XLV', 'JNJ': 'XLV'
}

# --- LISTA TOP SP500 ---
TOP_50_SP500 = list(SECTOR_MAP.keys())

# --- SIDEBAR ---
st.sidebar.header("🛡️ Parâmetros de Trading")
multiplicador_stop = st.sidebar.slider("Multiplicador Stop Loss (ATR)", 1.0, 3.5, 2.0, 0.5)
multiplicador_alvo = st.sidebar.slider("Multiplicador Alvo (ATR)", 2.0, 6.0, 4.0, 0.5)
st.sidebar.markdown("---")
st.sidebar.header("💰 Simulador Profit")
capital_total = st.sidebar.number_input("Capital Disponível ($)", value=10000)
risco_por_trade = st.sidebar.slider("Risco por Trade (%)", 0.5, 5.0, 1.0, 0.5)

# --- FUNÇÃO TÉCNICA AVANÇADA ---
def processar_dados_full(ticker):
    try:
        sector_etf = SECTOR_MAP.get(ticker, 'SPY')
        data = yf.download([ticker, 'SPY', sector_etf], period="2y", interval="1d", progress=False)
        if data.empty: return None
        
        df = data['Close'][[ticker]].rename(columns={ticker: 'Close'})
        for col in ['High', 'Low', 'Open', 'Volume']:
            df[col] = data[col][ticker]
        
        df['SPY_Close'] = data['Close']['SPY']
        df['SECTOR_Close'] = data['Close'][sector_etf]

        # Indicadores Base
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Bandas e Squeeze
        bb = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None: df = pd.concat([df, sqz], axis=1)
        
        # Fluxo
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)

        # 1. Sugestão: Divergência de RSI (Simplificada)
        df['Low_Pivot'] = (df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))
        df['RSI_Higher_Low'] = (df['RSI'] > df['RSI'].shift(1)) & (df['Low_Pivot'])
        
        return df, sector_etf
    except Exception as e:
        return None, None

# --- UI ---
st.title("🏹 Predator Pro: God Mode")
tab1, tab2, tab3 = st.tabs(["🚀 Scanner", "🔍 Análise Manual", "📊 Backtest & Performance"])

# --- ABA 1: SCANNER ---
with tab1:
    if st.button("🚀 Varredura de Elite"):
        resultados = []
        bar = st.progress(0)
        for i, t in enumerate(TOP_50_SP500):
            df, _ = processar_dados_full(t)
            if df is not None:
                u = df.iloc[-1]
                p = df.iloc[-2]
                if u['Close'] > u['EMA_200'] and (u['SQZ_ON'] == 1 or (u['SQZ_ON'] == 0 and p['SQZ_ON'] == 1)):
                    # Força Relativa Setorial (Últimos 10 dias)
                    perf_stock = (u['Close'] / df.iloc[-10]['Close']) - 1
                    perf_sector = (u['SECTOR_Close'] / df.iloc[-10]['SECTOR_Close']) - 1
                    status_setor = "💪 LÍDER" if perf_stock > perf_sector else "🚶 SEGUIDOR"
                    
                    resultados.append({
                        "Ticker": t, "Preço": round(float(u['Close']), 2),
                        "RSI": round(float(u['RSI']), 1), "RVOL": round(float(u['RVOL']), 2),
                        "Setor": status_setor, "Sinal": "🔥 ROMPEU" if u['SQZ_ON'] == 0 else "🟡 SQZ"
                    })
            bar.progress((i + 1) / len(TOP_50_SP500))
        st.dataframe(pd.DataFrame(resultados), use_container_width=True)

# --- ABA 2: MANUAL ---
with tab2:
    ticker_user = st.text_input("Ticker", "NVDA").upper()
    if st.button("Análise Tática"):
        df, s_etf = processar_dados_full(ticker_user)
        if df is not None:
            u = df.iloc[-1]
            col_bbu = [c for c in df.columns if c.startswith('BBU')][0]
            col_bbl = [c for c in df.columns if c.startswith('BBL')][0]
            
            # Simulador Profit
            dist_stop = u['Close'] - (u['Close'] - (u['ATR'] * multiplicador_stop))
            qty = int((capital_total * (risco_por_trade/100)) / dist_stop)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço", f"{u['Close']:.2f}")
            c2.metric("Qtd. Ações", f"{qty}")
            c3.metric("Rácio R:R", f"1:{multiplicador_alvo/multiplicador_stop:.1f}")
            c4.metric("ETF Setorial", s_etf)

            # Gráfico
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2])
            fig.add_trace(go.Candlestick(x=df.index[-100:], open=df['Open'][-100:], high=df['High'][-100:], low=df['Low'][-100:], close=df['Close'][-100:]), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index[-100:], y=df['EMA_200'][-100:], name="EMA 200"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index[-100:], y=df['RSI'][-100:], name="RSI"), row=2, col=1)
            fig.add_trace(go.Bar(x=df.index[-100:], y=df['Volume'][-100:], name="Vol"), row=3, col=1)
            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # 2. Sugestão: Diagnóstico de Divergência
            if u['RSI_Higher_Low']:
                st.success("🎯 DIVERGÊNCIA BULLISH DETECTADA: O RSI está a ganhar força apesar do preço baixo.")

# --- ABA 3: BACKTEST ---
with tab3:
    if ticker_user and 'df' in locals():
        st.subheader(f"📊 Performance da Estratégia (12 Meses): {ticker_user}")
        # Lógica simplificada de backtest: Compra no rompimento do Squeeze se acima da EMA 200
        df['Signal'] = (df['SQZ_ON'] == 0) & (df['SQZ_ON'].shift(1) == 1) & (df['Close'] > df['EMA_200'])
        trades = df[df['Signal'] == True].copy()
        
        if not trades.empty:
            trades['Resultado'] = (df['Close'].shift(-10) / trades['Close']) - 1 # Retorno após 10 dias
            win_rate = (trades['Resultado'] > 0).mean()
            st.write(f"**Taxa de Acerto (Win Rate):** {win_rate*100:.1f}%")
            st.write(f"**Número de Sinais:** {len(trades)}")
            st.line_chart(trades['Resultado'])
        else:
            st.info("Sem sinais suficientes para backtest neste período.")