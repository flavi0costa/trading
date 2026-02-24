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

@st.cache_data(ttl=300)
def baixar_dados(ticker):
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    if df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]
    return df.dropna(how='all').ffill()

def adicionar_indicadores(df):
    if len(df) < 50: return df
    df = df.copy()
    
    # Médias e Tendência
    df['EMA9'] = ta.ema(df['Close'], length=9)
    df['SMA200'] = ta.sma(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # ADX e SuperTrend
    df.ta.adx(append=True)
    df.ta.supertrend(append=True)
    
    # MACD
    df.ta.macd(append=True)
    
    # Bandas de Bollinger
    df.ta.bbands(length=20, std=2, append=True)
    
    # Média de Volume (20 períodos)
    df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
    
    # ATR (Para cálculo de Stop Loss e Take Profit)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    return df

# --- INTERFACE ---
st.sidebar.header("⚙️ Configurações")
ticker_input = st.sidebar.text_input("Ticker", "NVDA").upper().strip()
btn_analisar = st.sidebar.button("🚀 Analisar Agora", use_container_width=True)

st.title(f"📊 Ultra Dashboard: {ticker_input}")

if btn_analisar:
    with st.spinner("A calcular pontos de entrada e saída..."):
        df = baixar_dados(ticker_input)
        
        if df.empty:
            st.error("Ticker não encontrado.")
        else:
            df = adicionar_indicadores(df)
            dados_atuais = df.iloc[-1]
            
            try:
                # Busca Dinâmica de Colunas
                col_st_dir = [c for c in df.columns if c.startswith('SUPERTd')][0]
                col_st_val = [c for c in df.columns if c.startswith('SUPERT_') and not c.startswith('SUPERTd')][0]
                col_adx = [c for c in df.columns if c.startswith('ADX')][0]
                col_macd_hist = [c for c in df.columns if c.startswith('MACDh_')][0]
                
                # Valores Escalares
                preco = float(dados_atuais['Close'])
                vol_atual = float(dados_atuais['Volume'])
                vol_avg = float(dados_atuais['Vol_Avg'])
                adx_val = float(dados_atuais[col_adx])
                st_dir = int(dados_atuais[col_st_dir])
                atr_val = float(dados_atuais['ATR'])

                # --- MÉTRICAS ---
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Preço", f"${preco:.2f}")
                m2.metric("Vol. vs Média", f"{int(vol_atual/1000000)}M", f"{((vol_atual/vol_avg)-1)*100:.1f}%")
                m3.metric("Força (ADX)", f"{adx_val:.1f}")
                m4.metric("SuperTrend", "ALTA" if st_dir == 1 else "BAIXA")

                # --- CÁLCULO DE GESTÃO DE RISCO (Rácio 2:1) ---
                st.subheader("🛡️ Gestão de Risco (Sugerido para Swing Trade)")
                
                if st_dir == 1: # Se tendência for de ALTA
                    stop_loss = preco - (1.5 * atr_val)
                    take_profit = preco + (3.0 * atr_val)
                    tipo_trade = "LONG (Compra)"
                else: # Se tendência for de BAIXA
                    stop_loss = preco + (1.5 * atr_val)
                    take_profit = preco - (3.0 * atr_val)
                    tipo_trade = "SHORT (Venda)"

                r1, r2, r3, r4 = st.columns(4)
                r1.warning(f"**STOP LOSS:** \n\n ${stop_loss:.2f}")
                r2.success(f"**TAKE PROFIT:** \n\n ${take_profit:.2f}")
                r3.info(f"**ALVO %:** \n\n {abs((take_profit/preco)-1)*100:.1f}%")
                r4.metric("Rácio R/R", "2:1")

                # --- GRÁFICO ---
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                df_plot = df.tail(120)
                
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Preço"), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[col_st_val], name="SuperTrend", line=dict(color='yellow', width=1)), row=1, col=1)
                
                # Adicionar Linhas de Stop e Profit no Gráfico
                fig.add_hline(y=stop_loss, line_dash="dash", line_color="red", annotation_text="STOP LOSS", row=1, col=1)
                fig.add_hline(y=take_profit, line_dash="dash", line_color="green", annotation_text="TAKE PROFIT", row=1, col=1)

                colors = ['green' if df_plot['Close'][i] >= df_plot['Open'][i] else 'red' for i in range(len(df_plot))]
                fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name="Volume", marker_color=colors), row=2, col=1)
                
                fig.update_layout(height=650, template="plotly_dark", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

                # --- CHECKLIST EXPANDIDA ---
                st.subheader("✅ Checklist Profissional")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"{'✅' if st_dir == 1 else '❌'} SuperTrend Alta")
                    st.write(f"{'✅' if adx_val > 25 else '⚠️'} Tendência Forte")
                with c2:
                    st.write(f"{'✅' if vol_atual > vol_avg else '⚠️'} Volume de Confirmação")
                    st.write(f"{'✅' if float(dados_atuais[col_macd_hist]) > 0 else '❌'} Momentum Positivo")
                with c3:
                    st.write(f"{'✅' if preco > float(dados_atuais['EMA9']) else '❌'} Acima da EMA 9")
                    st.write(f"{'✅' if preco > float(dados_atuais['SMA200']) else '❌'} Acima da Média 200")

            except Exception as e:
                st.error(f"Erro na análise: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("O Stop Loss é calculado com 1.5x o ATR atual para evitar ser stopado pelo ruído do mercado.")