import streamlit as st

st.set_page_config(page_title="Calculadora Momentum Pro", layout="centered")

# --- GUIA RÁPIDO ---
with st.expander("📖 Checklist Pré-Trade", expanded=False):
    st.markdown("""
    1. **Tendência:** Acima da EMA 50 e Semanal em alta?
    2. **Trigger:** RSI 2 abaixo de 15?
    3. **Espaço:** O Alvo (TP2) tem caminho livre ou há uma resistência próxima?
    """)

st.title("🧮 Calculadora de Posição & Risco")

with st.sidebar:
    st.header("⚙️ Gestão de Banca")
    capital = st.number_input("Capital Total (€/$)", min_value=0.0, value=10000.0, step=500.0)
    risco_perc = st.slider("Risco na Banca (%)", 0.1, 5.0, 1.0)
    st.divider()
    st.caption("Estratégia: 1.5x ATR para Stop | Saídas 50/50")

# --- ENTRADAS ---
col_in1, col_in2 = st.columns(2)
with col_in1:
    st.subheader("📍 Ativo")
    ticker = st.text_input("Ticker", "NVDA").upper().strip()
    preco_entrada = st.number_input("Preço de Entrada ($)", min_value=0.0, value=150.0, format="%.2f")

with col_in2:
    st.subheader("📏 Volatilidade")
    atr_valor = st.number_input("Valor do ATR", min_value=0.0, value=2.5, format="%.4f")

# --- LÓGICA ---
distancia_stop = 1.5 * atr_valor
sl = preco_entrada - distancia_stop
tp1 = preco_entrada + distancia_stop 
tp2 = preco_entrada + (3.0 * atr_valor)

# % de queda até o Stop
queda_admissivel = (distancia_stop / preco_entrada) * 100

valor_risco_fin = capital * (risco_perc / 100)
qtd_total = int(valor_risco_fin / distancia_stop) if distancia_stop > 0 else 0
investimento = qtd_total * preco_entrada

# --- EXIBIÇÃO ---
st.divider()
res1, res2 = st.columns(2)

with res1:
    st.markdown("### 🛡️ Gestão de Risco")
    st.error(f"**STOP LOSS:** `${sl:.2f}`")
    st.metric("Ações Totais", f"{qtd_total} un")
    st.metric("Queda Admissível", f"-{queda_admissivel:.2f}%")

with res2:
    st.markdown("### 🎯 Alvos")
    st.success(f"**TP 1 (50%):** `${tp1:.2f}`")
    st.success(f"**TP 2 (Final):** `${tp2:.2f}`")
    st.write(f"Investimento: **${investimento:.2f}**")

# --- RESUMO PARA REGISTO ---
st.subheader("📝 Resumo para Copiar")
resumo = f"BUY {ticker} @ {preco_entrada:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f} | TP2: {tp2:.2f} | QTY: {qtd_total}"
st.code(resumo, language="text")

if (investimento / capital) > 0.30:
    st.warning("⚠️ **EXPOSIÇÃO ALTA:** Esta posição usa mais de 30% da tua banca.")
