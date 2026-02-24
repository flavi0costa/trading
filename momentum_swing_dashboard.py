import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Ultra Momentum Pro V3", layout="wide")

# ==========================================
# 1. FUNÇÕES CORE REFORÇADAS
# ==========================================
@st.cache_data(ttl=300)
def baixar_dados(ticker, intervalo="1d", periodo="2y"):
    df = yf.download(ticker, period=period, interval=intervalo, progress=False, auto_adjust=True)
    if df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]
    return df.dropna(how='all').ffill()

def adicionar_indicadores(df):
    if len(df) < 50: return df
    df = df.copy()
    df['EMA9'] = ta.ema(df['Close'], length=9)
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['EMA50'] = ta.ema(df['Close'], length=50)
    df['SMA200'] = ta.sma(df['Close'], length=200)
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    df['RSI_2'] = ta.rsi(df['Close'], length=2)
    df.ta.adx(append=True)
    df.ta.supertrend(append=True)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    return df

def obter_earnings(ticker):
    try:
        t = yf.Ticker(ticker)
        calendar = t.calendar
        if calendar is not None and not calendar.empty:
            # Pega a data mais próxima do calendário de earnings
            prox_data = calendar.iloc[0, 0] 
            return prox_data
    except:
        return None
    return None

# ==========================================
# 2. INTERFACE
# ==========================================
st.title("🔥 Ultra Momentum Pro - Institutional Edition")

tab1, tab2 = st.tabs(["📊 Analisador Individual", "🔍 Scanner de Oportunidades"])

with tab1:
    # Sidebar de Gestão de Risco na Aba 1
    with st.expander("💰 Configuração de Gestão de Risco", expanded=True):
        c_risk1, c_risk2 = st.columns(2)
        capital = c_risk1.number_input("Capital Total (€/$)", value=10000.0, step=500.0)
        risco_perc = c_risk2.slider("Risco por Operação (%)", 0.1, 5.0, 1.0)

    col_in1, col_in2 = st.columns([3, 1])
    ticker_input = col_in1.text_input("Ticker para Análise", "NVDA").upper().strip()
    btn_analisar = col_in2.button("🚀 Executar Análise Completa", use_container_width=True)

    if btn_analisar:
        with st.spinner("A processar dados Diários, Semanais e Earnings..."):
            df_diario = baixar_dados(ticker_input)
            df_semanal = baixar_dados(ticker_input, intervalo="1wk")
            
            if df_diario.empty:
                st.error("Ticker não encontrado.")
            else:
                df_diario = adicionar_indicadores(df_diario)
                df_semanal = adicionar_indicadores(df_semanal)
                d = df_diario.iloc[-1]
                w = df_semanal.iloc[-1] # Dados semanais
                
                # --- ALERTA DE EARNINGS ---
                prox_earnings = obter_earnings(ticker_input)
                alerta_earnings = False
                if prox_earnings:
                    dias_para_earnings = (prox_earnings.date() - datetime.now().date()).days
                    if 0 <= dias_para_earnings <= 7:
                        st.warning(f"⚠️ PERIGO: Resultados (Earnings) em {dias_para_earnings} dias ({prox_earnings.date()}). Alta volatilidade esperada!")
                        alerta_earnings = True

                # --- MÉTRICAS DE RISCO ---
                atr = float(d['ATR'])
                preco = float(d['Close'])
                col_st_dir = [c for c in df_diario.columns if c.startswith('SUPERTd')][0]
                st_dir = int(d[col_st_dir])
                
                sl = preco - (1.5 * atr) if st_dir == 1 else preco + (1.5 * atr)
                tp = preco + (3.0 * atr) if st_dir == 1 else preco - (3.0 * atr)
                
                # Cálculo do Tamanho da Posição
                valor_risco = capital * (risco_perc / 100)
                distancia_sl = abs(preco - sl)
                if distancia_sl > 0:
                    num_acoes = int(valor_risco / distancia_sl)
                    investimento_total = num_acoes * preco
                else:
                    num_acoes = 0
                    investimento_total = 0

                # --- EXIBIÇÃO DE GESTÃO ---
                st.subheader("🛡️ Plano de Trade")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Stop Loss", f"${sl:.2f}")
                r2.metric("Take Profit", f"${tp:.2f}")
                r3.success(f"Comprar: {num_acoes} ações")
                r4.info(f"Total: ${investimento_total:.2f}")

                # --- GRÁFICO ---
                fig = make_subplots(rows=1, cols=1)
                df_p = df_diario.tail(100)
                fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Diário"))
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA21'], name="EMA 21", line=dict(color='orange')))
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA50'], name="EMA 50", line=dict(color='magenta')))
                fig.add_hline(y=sl, line_dash="dash", line_color="red")
                fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                # --- CHECKLIST MULTI-TIMEFRAME ---
                st.subheader("✅ Verificação Institucional")
                c1, c2, c3 = st.columns(3)
                
                # Tendência Semanal
                st_semanal_dir = [c for c in df_semanal.columns if c.startswith('SUPERTd')][0]
                tendencia_semanal_ok = w[st_semanal_dir] == 1
                
                with c1:
                    st.write("**Maré (Semanal)**")
                    st.write(f"{'✅' if tendencia_semanal_ok else '❌'} Tendência Semanal de Alta")
                    st.write(f"{'✅' if w['Close'] > w['EMA21'] else '❌'} Semanal acima EMA 21")
                with c2:
                    st.write("**Onda (Diário)**")
                    st.write(f"{'✅' if d['RSI_2'] < 20 else '⚪'} Pullback Ativo (RSI2)")
                    st.write(f"{'✅' if d['Close'] > d['SMA200'] else '❌'} Acima da Média 200")
                with c3:
                    st.write("**Eventos & Risco**")
                    st.write(f"{'❌' if alerta_earnings else '✅'} Longe de Earnings")
                    st.write(f"Risco: {risco_perc}% (${valor_risco})")

with tab2:
    st.subheader("Scanner Pro")
    st.write("Análise rápida com filtro de tendência Semanal e Diária.")
    lista_tickers = st.text_area("Lista", "NVDA, AAPL, MSFT, TSLA, AMZN, AMD, PLTR").upper()
    if st.button("🔍 Iniciar Varredura"):
        tickers = [t.strip() for t in lista_tickers.split(",") if t.strip()]
        resultados = []
        for t in tickers:
            try:
                df_d = baixar_dados(t)
                df_w = baixar_dados(t, intervalo="1wk")
                if df_d.empty or df_w.empty: continue
                
                df_d = adicionar_indicadores(df_d)
                df_w = adicionar_indicadores(df_w)
                
                d = df_d.iloc[-1]
                w = df_w.iloc[-1]
                
                # Condição de Compra: Semanal de Alta + Diário em Pullback
                st_d_col = [c for c in df_d.columns if c.startswith('SUPERTd')][0]
                st_w_col = [c for c in df_w.columns if c.startswith('SUPERTd')][0]
                
                status = "Aguardar"
                if w[st_w_col] == 1 and d[st_d_col] == 1:
                    if d['RSI_2'] < 15: status = "🔥 COMPRA (Pullback)"
                    else: status = "🟢 Tendência Alta"
                elif w[st_w_col] == -1: status = "🔴 Baixa (Semanal)"

                resultados.append({"Ativo": t, "Sinal": status, "RSI 2": round(d['RSI_2'],1), "Semanal": "Alta" if w[st_w_col] == 1 else "Baixa"})
            except: continue
        st.table(resultados)