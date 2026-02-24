import streamlit as st

st.set_page_config(page_title="Calculadora Momentum Single Page", layout="wide")

# ==========================================
# 1. TOPO: TÍTULO E GUIA RÁPIDO
# ==========================================
st.title("🧮 Calculadora de Risco Momentum")
st.info("💡 **Checklist:** EMA 21 > 50? | RSI 2 < 15? | Semanal em Alta?")

# ==========================================
# 2. INPUTS (ORGANIZADOS EM COLUNAS LARGAS)
# ==========================================
with st.container():
    c_in1, c_in2, c_in3, c_in4 = st.columns(4)
    
    with c_in1:
        ticker = st.text_input("Ticker", "NVDA").upper().strip()
    with c_in2:
        capital = st.number_input("Capital (€/$)", value=10000.0, step=500.0)
    with c_in3:
        preco_entrada = st.number_input("Entrada ($)", value=150.0, format="%.2f")
    with c_in4:
        atr_valor = st.number_input("Valor ATR", value=2.5, format="%.4f")

# ==========================================
# 3. LÓGICA DE CÁLCULO
# ==========================================
risco_perc = st.sidebar.slider("Risco na Banca (%)", 0.1, 5.0, 1.0) # Único item na sidebar para limpar o centro

distancia_stop = 1.5 * atr_valor
sl = preco_entrada - distancia_stop
tp1 = preco_entrada + distancia_stop # Rácio 1:1 para parcial
tp2 = preco_entrada + (3.0 * atr_valor) # Rácio 1:2 final

valor_risco_fin = capital * (risco_perc / 100)
qtd_total = int(valor_risco_fin / distancia_stop) if distancia_stop > 0 else 0
investimento = qtd_total * preco_entrada
queda_perc = (distancia_stop / preco_entrada) * 100 if preco_entrada > 0 else 0

# ==========================================
# 4. PAINEL DE RESULTADOS (VISÃO TOTAL)
# ==========================================
st.divider()

col_res1, col_res2, col_res3 = st.columns([1, 1, 1.5])

with col_res1:
    st.subheader("🛡️ Proteção")
    st.error(f"**STOP LOSS: ${sl:.2f}**")
    st.write(f"Distância: **-{queda_perc:.2f}%**")
    st.write(f"Risco: **${valor_risco_fin:.2f}**")

with col_res2:
    st.subheader("🎯 Alvos")
    st.success(f"**TP 1 (50%): ${tp1:.2f}**")
    st.success(f"**TP 2 (Final): ${tp2:.2f}**")
    st.write(f"Investimento: **${investimento:.2f}**")

with col_res3:
    st.subheader("📋 Resumo & Lote")
    st.metric("Quantidade Total", f"{qtd_total} un")
    
    # Gerador de Resumo para Diário
    resumo_txt = f"BUY {ticker} @ {preco_entrada:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f} | TP2: {tp2:.2f} | QTY: {qtd_total}"
    st.code(resumo_txt, language="text")

# ==========================================
# 5. RODAPÉ DE SEGURANÇA
# ==========================================
st.divider()
if investimento > capital:
    st.error(f"⚠️ Alerta: Esta operação exige mais capital do que tens disponível (${investimento:.2f} > ${capital:.2f}).")
else:
    exposicao = (investimento / capital) * 100
    st.caption(f"Exposição desta posição: {exposicao:.1f}% do capital total.")
