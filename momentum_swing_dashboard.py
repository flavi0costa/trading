import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Ultra Momentum Pro V3", layout="wide")

# ==========================================
# 1. FUNÇÕES CORE (CORRIGIDAS)
# ==========================================

@st.cache_data(ttl=300)
def baixar_dados(ticker, interval="1d", period="2y"):
    # Mudamos 'intervalo' para 'interval' para alinhar com o yfinance e evitar conflitos no cache
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    
    if df.empty: 
        return pd.DataFrame()
    
    # Tratamento de colunas (MultiIndex) para evitar o erro de Scalar/Series
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df.loc[:, ~df.columns.duplicated()]
    return df.dropna(how='all').ffill()

def adicionar_indicadores(df):
    if len(df) < 50: return df
    df = df.copy()
    
    # Médias
    df['EMA9'] = ta.ema(df['Close'], length=9)
    df['EMA21'] = ta.ema(df['Close'], length=21)
    df['EMA50'] = ta.ema(df['Close'], length=50)
    df['SMA200'] = ta.sma(df['Close'], length=200)
    
    # Momento
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    df['RSI_2'] = ta.rsi(df['Close'], length=2)
    
    # Tendência e Volatilidade
    df.ta.adx(append=True)
    df.ta.supertrend(append=True)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    return df

def obter_earnings(ticker):
    try:
        t = yf.Ticker(ticker)
        calendar = t.calendar
        if calendar is not None and not calendar.empty:
            # Pega a data de resultados mais próxima
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

# --- ABA 1: ANALISADOR INDIVIDUAL ---
with tab1:
    with st.expander("💰 Configuração de Gestão de Risco", expanded=True):
        c_risk1, c_risk2 = st.columns(2)
        capital = c_risk1.number_input("Capital Total (€/$)", value=10000.0, step=500.0)
        risco_perc = c_risk2.slider("Risco por Operação (%)", 0.1, 5.0, 1.0)

    col_in1, col_in2 = st.columns([3, 1])
    ticker_input = col_in1.text_input("Ticker para Análise", "NVDA", key="single_ticker").upper().strip()
    btn_analisar = col_in2.button("🚀 Executar Análise Completa", use_container_width=True)

    if btn_analisar:
        with st.spinner("A processar dados..."):
            df_diario = baixar_dados(ticker_input, interval="1d")
            df_semanal = baixar_dados(ticker_input, interval="1wk")
            
            if df_diario.empty:
                st.error("Ticker não encontrado ou sem dados.")
            else:
                df_diario = adicionar_indicadores(df_diario)
                df_semanal = adicionar_indicadores(df_semanal)
                
                d = df_diario.iloc[-1]
                w = df_semanal.iloc[-1]
                
                # Alerta de Earnings
                prox_earnings = obter_earnings(ticker_input)
                alerta_earnings = False
                if prox_earnings:
                    # Garantir que prox_earnings é tratado como data para o cálculo
                    try:
                        dt_earnings = prox_earnings.date() if hasattr(prox_earnings, 'date') else prox_earnings
                        dias_para = (dt_earnings - datetime.now().date()).days
                        if 0 <= dias_para <= 7:
                            st.warning(f"⚠️ EARNINGS em {dias_para} dias ({dt_earnings})!")
                            alerta_earnings = True
                    except: pass

                # Gestão de Risco
                atr = float(d['ATR'])
                preco = float(d['Close'])
                st_col = [c for c in df_diario.columns if c.startswith('SUPERTd')][0]
                st_dir = int(d[st_col])
                
                sl = preco - (1.5 * atr) if st_dir == 1 else preco + (1.5 * atr)
                tp = preco + (3.0 * atr) if st_dir == 1 else preco - (3.0 * atr)
                
                valor_risco = capital * (risco_perc / 100)
                dist_sl = abs(preco - sl)
                num_acoes = int(valor_risco / dist_sl) if dist_sl > 0 else 0

                # Métricas
                st.subheader("🛡️ Plano de Trade & Risco")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Stop Loss", f"${sl:.2f}")
                r2.metric("Take Profit", f"${tp:.2f}")
                r3.success(f"Posição: {num_acoes} ações")
                r4.info(f"Risco: ${valor_risco:.2f}")

                # Gráfico
                fig = make_subplots(rows=1, cols=1)
                df_p = df_diario.tail(100)
                fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Preço"))
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA21'], name="EMA 21", line=dict(color='orange')))
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA50'], name="EMA 50", line=dict(color='magenta')))
                fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="STOP")
                fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                # Checklist
                st.subheader("✅ Verificação Institucional")
                c1, c2, c3 = st.columns(3)
                st_w_col = [c for c in df_semanal.columns if c.startswith('SUPERTd')][0]
                
                with c1:
                    st.write("**Maré (Semanal)**")
                    st.write(f"{'✅' if w[st_w_col] == 1 else '❌'} Tendência Semanal")
                    st.write(f"{'✅' if w['Close'] > w['EMA21'] else '❌'} Semanal > EMA 21")
                with c2:
                    st.write("**Onda (Diário)**")
                    st.write(f"{'✅' if d['RSI_2'] < 20 else '⚪'} RSI 2 Pullback ({d['RSI_2']:.1f})")
                    st.write(f"{'✅' if d['Close'] > d['SMA200'] else '❌'} Acima SMA 200")
                with c3:
                    st.write("**Filtros**")
                    st.write(f"{'❌' if alerta_earnings else '✅'} Sem Earnings Próximos")
                    st.write(f"RSI 14: {d['RSI_14']:.1f}")

# --- ABA 2: SCANNER ---
with tab2:
    st.subheader("Scanner de Pullbacks")
    lista_raw = st.text_area("Lista de Tickers", "NVDA, AAPL, MSFT, TSLA, AMZN, AMD, PLTR, GOOGL").upper()
    if st.button("🔍 Iniciar Varredura"):
        tickers = [t.strip() for t in lista_raw.split(",") if t.strip()]
        res = []
        progress_bar = st.progress(0)
        
        for idx, t in enumerate(tickers):
            progress_bar.progress((idx+1)/len(tickers))
            try:
                dd = baixar_dados(t, interval="1d")
                ww = baixar_dados(t, interval="1wk")
                if dd.empty or ww.empty: continue
                
                dd = adicionar_indicadores(dd)
                ww = adicionar_indicadores(ww)
                
                last_d = dd.iloc[-1]
                last_w = ww.iloc[-1]
                
                std_col = [c for c in dd.columns if c.startswith('SUPERTd')][0]
                stw_col = [c for c in ww.columns if c.startswith('SUPERTd')][0]
                
                status = "Aguardar"
                if last_w[stw_col] == 1:
                    if last_d['RSI_2'] < 15: status = "🔥 COMPRA"
                    elif last_d[std_col] == 1: status = "🟢 Alta"
                
                res.append({"Ativo": t, "Sinal": status, "RSI 2": round(last_d['RSI_2'],1), "Semanal": "Alta" if last_w[stw_col] == 1 else "Baixa"})
            except: continue
        st.table(res)
