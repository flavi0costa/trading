import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import warnings

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Ultra Momentum Dashboard", layout="wide")

# ==========================================
# 1. FUNÇÕES CORE (INTACTAS)
# ==========================================
@st.cache_data(ttl=300)
def baixar_dados(ticker):
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    if df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]
    return df.dropna(how='all').ffill()

def detectar_candles(df):
    if len(df) < 5: return "Sem dados"
    u = df.iloc[-1]
    p = df.iloc[-2]
    corpo = abs(u['Close'] - u['Open'])
    tamanho = u['High'] - u['Low']
    pavio_inf = min(u['Open'], u['Close']) - u['Low']
    pavio_sup = u['High'] - max(u['Open'], u['Close'])
    
    if pavio_inf > (2 * corpo) and pavio_sup < (0.1 * tamanho): return "🟢 Martelo"
    if u['Close'] > p['Open'] and u['Open'] < p['Close'] and u['Close'] > u['Open'] and p['Close'] < p['Open']: return "🟢 Engolfo Alta"
    if pavio_sup > (2 * corpo) and pavio_inf < (0.1 * tamanho): return "🔴 Shooting Star"
    if corpo < (0.1 * tamanho): return "🟡 Doji"
    return "⚪ Neutro"

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
    df.ta.macd(append=True)
    df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    return df

# ==========================================
# 2. INTERFACE E ABAS
# ==========================================
st.title("🔥 Ultra Momentum Pro")
st.sidebar.info("Dashboard atualizado com Scanner Multiativos. O analisador individual mantém a estratégia de RSI Dual e EMA 21/50.")

tab1, tab2 = st.tabs(["📊 Analisador Individual", "🔍 Scanner de Oportunidades"])

# ------------------------------------------
# ABA 1: O SEU CÓDIGO ORIGINAL INTACTO
# ------------------------------------------
with tab1:
    st.subheader("Análise Profunda de um Ativo")
    
    col_in1, col_in2 = st.columns([3, 1])
    with col_in1:
        ticker_input = st.text_input("Ticker para Análise", "NVDA", key="in_single").upper().strip()
    with col_in2:
        st.write("") # Espaçamento
        btn_analisar = st.button("🚀 Executar Análise", use_container_width=True, key="btn_single")

    if btn_analisar:
        with st.spinner("A analisar o ativo..."):
            df = baixar_dados(ticker_input)
            if df.empty:
                st.error("Ticker não encontrado.")
            else:
                df = adicionar_indicadores(df)
                d = df.iloc[-1]
                
                # --- MÉTRICAS ---
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Preço", f"${d['Close']:.2f}")
                m2.metric("RSI (14)", f"{d['RSI_14']:.1f}")
                m3.metric("RSI (2)", f"{d['RSI_2']:.1f}", help="<15 Compra, >85 Venda")
                m4.metric("Padrão Candle", detectar_candles(df))

                # --- RISCO ---
                atr = float(d['ATR'])
                preco = float(d['Close'])
                col_st_dir = [c for c in df.columns if c.startswith('SUPERTd')][0]
                st_dir = int(d[col_st_dir])
                
                sl = preco - (1.5 * atr) if st_dir == 1 else preco + (1.5 * atr)
                tp = preco + (3.0 * atr) if st_dir == 1 else preco - (3.0 * atr)
                
                st.info(f"🛡️ **Gestão de Risco (ATR):** STOP LOSS: **${sl:.2f}** | TAKE PROFIT: **${tp:.2f}** (Rácio 2:1)")

                # --- GRÁFICO ---
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                df_p = df.tail(120)
                
                fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Preço"), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA9'], name="EMA 9", line=dict(color='cyan', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA21'], name="EMA 21", line=dict(color='orange', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA50'], name="EMA 50", line=dict(color='magenta', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name="SMA 200", line=dict(color='white', width=2)), row=1, col=1)
                
                colors = ['green' if df_p['Close'][i] >= df_p['Open'][i] else 'red' for i in range(len(df_p))]
                fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name="Volume", marker_color=colors), row=2, col=1)
                
                fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                # --- CHECKLIST ---
                st.subheader("✅ Verificação de Estratégia")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"{'✅' if d['Close'] > d['EMA21'] else '❌'} Acima da EMA 21")
                    st.write(f"{'✅' if d['EMA21'] > d['EMA50'] else '❌'} Alinhamento EMA 21 > 50")
                with c2:
                    st.write(f"{'✅' if st_dir == 1 else '❌'} SuperTrend (Direção)")
                    st.write(f"{'✅' if d.filter(like='ADX').iloc[0] > 25 else '⚠️'} ADX > 25 (Força)")
                with c3:
                    st.write(f"{'✅' if 30 < d['RSI_14'] < 70 else '⚠️'} RSI 14 Seguro")
                    st.write(f"{'🔥' if d['RSI_2'] < 15 else 'OK'} RSI 2 (Pullback)")

# ------------------------------------------
# ABA 2: O NOVO SCANNER ADICIONADO
# ------------------------------------------
with tab2:
    st.subheader("Scanner Automático de Pullbacks")
    st.write("Procura ativos em forte tendência de alta (SuperTrend + ADX > 25 + Acima EMA21) que estejam a fazer um recuo tático (RSI 2 < 15).")
    
    lista_tickers = st.text_area("Lista de Tickers (separados por vírgula)", 
                                 "NVDA, AAPL, MSFT, TSLA, META, GOOGL, AMZN, AMD, PLTR, COIN").upper().strip()
    
    btn_scan = st.button("🔍 Executar Scanner", type="primary", use_container_width=True)
    
    if btn_scan:
        tickers = [t.strip() for t in lista_tickers.split(",") if t.strip()]
        
        if not tickers:
            st.warning("Insira pelo menos um ticker.")
        else:
            resultados = []
            barra_progresso = st.progress(0)
            
            for i, t in enumerate(tickers):
                # Atualiza a barra de progresso
                barra_progresso.progress((i + 1) / len(tickers), text=f"A analisar {t}...")
                
                try:
                    df_scan = baixar_dados(t)
                    if df_scan.empty: continue
                    
                    df_scan = adicionar_indicadores(df_scan)
                    if len(df_scan) < 50: continue
                    
                    d_scan = df_scan.iloc[-1]
                    
                    # Colunas Dinâmicas
                    col_st = [c for c in df_scan.columns if c.startswith('SUPERTd')][0]
                    col_adx = [c for c in df_scan.columns if c.startswith('ADX')][0]
                    
                    # Lógica de Classificação
                    sinal = "⚪ Neutro"
                    
                    if d_scan[col_st] == 1 and d_scan['Close'] > d_scan['EMA50']:
                        if d_scan['RSI_2'] < 15:
                            sinal = "🔥 PULLBACK (Comprar)"
                        elif d_scan[col_adx] > 25:
                            sinal = "🟢 Forte Alta (Aguardar)"
                        else:
                            sinal = "🟡 Alta s/ Força"
                    elif d_scan[col_st] == -1:
                        if d_scan['RSI_2'] > 85:
                            sinal = "💥 SOBRECOMPRA (Vender)"
                        else:
                            sinal = "🔴 Baixa"
                    
                    resultados.append({
                        "Ativo": t,
                        "Preço": f"${d_scan['Close']:.2f}",
                        "Sinal": sinal,
                        "RSI 2": round(d_scan['RSI_2'], 1),
                        "RSI 14": round(d_scan['RSI_14'], 1),
                        "ADX": round(d_scan[col_adx], 1),
                        "Acima SMA 200": "✅" if d_scan['Close'] > d_scan['SMA200'] else "❌",
                        "Candle": detectar_candles(df_scan)
                    })
                    
                except Exception as e:
                    # Ignora erros isolados num único ativo para não quebrar o scanner
                    continue
            
            barra_progresso.empty() # Remove a barra ao terminar
            
            if resultados:
                df_res = pd.DataFrame(resultados)
                # Ordena para mostrar os sinais de Pullback primeiro
                df_res = df_res.sort_values(by="Sinal", ascending=False)
                
                st.success(f"Análise concluída em {len(resultados)} ativos.")
                st.dataframe(df_res, use_container_width=True, hide_index=True)
            else:
                st.error("Nenhum dado válido pôde ser extraído dos tickers fornecidos.")