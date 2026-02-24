import streamlit as st

st.set_page_config(page_title="Momentum & DCA Calc", layout="wide")

st.title("🧮 Calculadora de Trading: Momentum & DCA")

# ==========================================
# 1. CALCULADORA DE RISCO (NOVA POSIÇÃO)
# ==========================================
st.subheader("🚀 Nova Posição (Estratégia Momentum)")
with st.container():
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        ticker = st.text_input("Ticker", "NVDA").upper()
    with c2:
        capital = st.number_input("Capital Total ($)", value=10000.0)
    with c3:
        risco_p = st.number_input("Risco (%)", value=1.0)
    with c4:
        ent_preco = st.number_input("Preço Entrada", value=150.0)
    with c5:
        atr = st.number_input("Valor ATR", value=2.5, format="%.4f")

# Cálculos Momentum
dist_sl = 1.5 * atr
sl_m = ent_preco - dist_sl
tp1_m = ent_preco + dist_sl
tp2_m = ent_preco + (3.0 * atr)
v_risco = capital * (risco_p / 100)
qtd = int(v_risco / dist_sl) if dist_sl > 0 else 0

# Exibição Rápida Momentum
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.error(f"Stop Loss: **${sl_m:.2f}**")
col_m2.success(f"TP1 (50%): **${tp1_m:.2f}** | TP2: **${tp2_m:.2f}**")
col_m3.info(f"Quantidade: **{qtd} un**")

st.divider()

# ==========================================
# 2. CÁLCULO DE DCA (MÉDIA DE CUSTO)
# ==========================================
st.subheader("📉 Calculadora de DCA (Dollar Cost Averaging)")
st.caption("Usa isto para calcular o novo preço médio ao adicionar mais ações a uma posição existente.")

with st.container():
    dca1, dca2 = st.columns(2)
    
    with dca1:
        st.markdown("**Posição Atual**")
        atual_qtd = st.number_input("Qtd. que já possuis", value=10, min_value=0)
        atual_preco = st.number_input("Preço Médio Atual", value=160.0)
        
    with dca2:
        st.markdown("**Nova Compra**")
        nova_qtd = st.number_input("Qtd. a comprar agora", value=5, min_value=0)
        novo_preco = st.number_input("Preço da nova compra", value=145.0)

# Lógica DCA
total_acoes = atual_qtd + nova_qtd
if total_acoes > 0:
    novo_preco_medio = ((atual_qtd * atual_preco) + (nova_qtd * novo_preco)) / total_acoes
    investimento_total = total_acoes * novo_preco_medio
    reducao_perc = ((atual_preco - novo_preco_medio) / atual_preco) * 100 if atual_preco > 0 else 0
else:
    total_acoes = 0
    novo_preco_medio = 0
    investimento_total = 0
    reducao_perc = 0

# Exibição Resultados DCA
st.markdown("### 📊 Resultado do DCA")
res_dca1, res_dca2, res_dca3 = st.columns(3)

with res_dca1:
    st.metric("Novo Preço Médio", f"${novo_preco_medio:.2f}", 
              delta=f"-{reducao_perc:.2f}%" if reducao_perc > 0 else None, delta_color="normal")

with res_dca2:
    st.metric("Total de Ações", f"{total_acoes} un")

with res_dca3:
    st.metric("Investimento Total", f"${investimento_total:.2f}")

# ==========================================
# 3. RESUMO PARA NOTAS
# ==========================================
st.divider()
st.subheader("📝 Resumo para Registo")
resumo_final = f"{ticker} | Novo Preço Médio: {novo_preco_medio:.2f} | Total Ações: {total_acoes}"
st.code(resumo_final, language="text")