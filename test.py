import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Predator Pro: Tactical Alpha", layout="wide")

# --- LISTA TOP 50 SP500 ---
TOP_50_SP500 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'V', 'UNH',
    'JNJ', 'XOM', 'WMT', 'JPM', 'MA', 'PG', 'AVGO', 'ORCL', 'HD', 'CVX',
    'COST', 'ABBV', 'LLY', 'BAC', 'ADBE', 'PEP', 'CSCO', 'TMO', 'CRM', 'WFC',
    'ACN', 'NFLX', 'KO', 'ABT', 'DHR', 'LIN', 'DIS', 'TXN', 'INTC', 'PM',
    'AMD', 'VZ', 'AMAT', 'QCOM', 'PFE', 'IBM', 'UNP', 'GS', 'INTU', 'HON'
]

# --- SIDEBAR: CONTROLO DE RISCO ---
st.sidebar.header("🛡️ Gestão de Risco ATR")
multi_stop = st.sidebar.slider("Multiplicador Stop Loss (ATR)", 1.0, 3.5, 2.0, 0.5)
multi_alvo = st.sidebar.slider("Multiplicador Alvo (ATR)", 2.0, 6.0, 4.0, 0.5)
rsi_limite = st.sidebar.slider("RSI Limite (Estabilidade)", 60, 80, 70)

# --- FUNÇÃO DE CÁLCULO CORE ---
def processar_ativo(ticker):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 200: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # AJUSTE: RSI de 21 para menos ruído
        df['RSI'] = ta.rsi(df['Close'], length=21)
        
        bb = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        sqz = ta.squeeze(df['High'], df['Low'], df['Close'])
        if sqz is not None: df = pd.concat([df, sqz], axis=1)
        
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_Avg']
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        
        return df
    except:
        return None

# --- UI PRINCIPAL ---
st.title("🏹 Predator Pro: Tactical Dashboard")
tab1, tab2 = st.tabs(["🚀 Scanner Automático", "🔍 Análise Manual Técnica"])

# --- ABA 1: SCANNER ---
with tab1:
    if st.button("Iniciar Varredura Top 50"):
        resultados = []
        bar = st.progress(0)
        for i, t in enumerate(TOP_50_SP500):
            df = processar_ativo(t)
            if df is not None:
                u = df.iloc[-1]
                p = df.iloc[-2]
                if u['Close'] > u['EMA_200'] and (u['SQZ_ON'] == 1 or (u['SQZ_ON'] == 0 and p['SQZ_ON'] == 1)):
                    resultados.append({
                        "Ticker": t, "Preço": round(float(u['Close']), 2),
                        "RSI (21)": round(float(u['RSI']), 1), "RVOL": round(float(u['RVOL']), 2),
                        "MFI": round(float(u['MFI']), 0),
                        "Estado": "🔥 ROMPEU" if u['SQZ_ON'] == 0 else "🟡 SQUEEZE"
                    })
            bar.progress((i + 1) / len(TOP_50_SP500))
        if resultados: st.dataframe(pd.DataFrame(resultados), use_container_width=True)

# --- ABA 2: ANÁLISE MANUAL ---
with tab2:
    ticker_input = st.text_input("Ticker", "NVDA").upper()
    if st.button("Analisar"):
        df = processar_ativo(ticker_input)
        if df is not None:
            df_p = df.tail(126)
            u = df_p.iloc[-1]
            
            val_stop = float(u['Close'] - (u['ATR'] * multi_stop))
            val_alvo = float(u['Close'] + (u['ATR'] * multi_alvo))
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço Atual", f"{u['Close']:.2f}")
            c2.metric("STOP LOSS", f"{val_stop:.2f}")
            c3.metric("TAKE PROFIT", f"{val_alvo:.2f}")
            c4.metric("MFI (Volume Flow)", f"{u['MFI']:.0f}")

            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
            
            # Preço e Alvos
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Preço"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA_200'], name="EMA 200", line=dict(color='yellow')), row=1, col=1)
            
            col_bbu = [c for c in df_p.columns if c.startswith('BBU')][0]
            col_bbl = [c for c in df_p.columns if c.startswith('BBL')][0]
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p[col_bbu], name="BB Upper", line=dict(color='rgba(173,216,230,0.3)')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p[col_bbl], name="BB Lower", line=dict(color='rgba(173,216,230,0.3)')), row=1, col=1)
            
            fig.add_hline(y=val_stop, line_dash="dash", line_color="red", annotation_text=f"STOP: {val_stop:.2f}", row=1, col=1)
            fig.add_hline(y=val_alvo, line_dash="dash", line_color="green", annotation_text=f"TP: {val_alvo:.2f}", row=1, col=1)

            # RSI 21
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name="RSI (21)", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=rsi_limite, line_dash="dot", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

            # Volume
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name="Volume"), row=3, col=1)

            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # Diagnóstico com Filtro MFI
            if u['RSI'] > rsi_limite and u['MFI'] > 80:
                st.error("⚠️ ALERTA DE EXAUSTÃO: RSI e MFI em níveis críticos. Risco de reversão alto.")
            elif u['SQZ_ON'] == 1:
                st.warning("🟡 SQUEEZE ATIVO: Volatilidade baixa, aguarde o rompimento.")
            elif u['RVOL'] > 1.5:
                st.success(f"🔥 FORÇA CONFIRMADA: Volume {u['RVOL']:.2f}x acima da média.")
