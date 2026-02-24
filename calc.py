import streamlit as st

# Configuração mínima para evitar lentidão
st.set_page_config(page_title="Calculadora Rápida", layout="wide")

st.title("🧮 Calculadora de Risco")

# Layout em colunas simples
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Banca")
    capital = st.number_input("Capital Total", value=10000.0)
    risco_perc = st.number_input("Risco %", value=1.0)

with col2:
    st.subheader("Entrada")
    ticker = st.text_input("Ticker", "NVDA").upper()
    preco_entrada = st.number_input("Preço de Compra", value=150.0)

with col3:
    st.subheader("Volatilidade")
    atr_valor = st.number_input("Valor ATR", value=2.5, format="%.4f")

# Cálculos Matemáticos Diretos
distancia_stop = 1.5 * atr_valor
sl = preco_entrada - distancia_stop
tp1 = preco_entrada + distancia_stop
tp2 = preco_entrada + (3.0 * atr_valor)

valor_risco = capital * (risco_perc / 100)
if distancia_stop > 0:
    qtd = int(valor_risco / distancia_stop)
else:
    qtd = 0

# Resultados
st.markdown("---")
res1, res2, res3 = st.columns(3)

res1.error(f"STOP LOSS: ${sl:.2f}")
res2.success(f"ALVO 1: ${tp1:.2f}")
res3.success(f"ALVO 2: ${tp2:.2f}")

st.metric("Quantidade de Ações", f"{qtd} un")

# Resumo para Copiar
resumo = f"{ticker} | Ent: {preco_entrada:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f} | TP2: {tp2:.2f} | Qtd: {qtd}"
st.text_area("Resumo (Copy/Paste)", resumo)
