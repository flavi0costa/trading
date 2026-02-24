import streamlit as st
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Momentum Precision 500", layout="wide")

st.title("🧮 Calculadora Precision (Banca 500€)")
st.caption("Ações Fracionárias | Rácio 2:1 | Gestão de Volatilidade")

# ==========================================
# CONFIGURAÇÕES DE BANCA (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("⚙️ Gestão de Banca")
    capital_total = st.number_input("Banca Total (€)", value=500.0)
    risco_perc = st.slider("Risco por Trade (%)", 0.1, 5.0, 1.0)
    valor_risco_fin = capital_total * (risco_perc / 100)
    
    st.divider()
    st.metric("Risco Máximo (Loss)", f"{valor_risco_fin:.2f}€")
    st.info(f"Se bater no Stop, perdes exatamente {valor_risco_fin:.2f}€.")

# Colunas principais
col_esq, col_dir = st.columns(2)

# Inicialização de variáveis
novo_pm = 0.0
total_q = 0.0

# ==========================================
# 1. MÓDULO: NOVA POSIÇÃO
# ==========================================
with col_esq:
    st.subheader("🚀 Nova Posição")
    with st.container(border=True):
        ticker = st.text_input("Ticker", "NVDA").upper()
        preco_ent = st.number_input("Preço de Entrada", value=10.0, format="%.2f")
        atr_val = st.number_input("Valor ATR", value=1.15, format="%.4f")
        
        # Lógica de Distâncias
        dist_sl = 1.5 * atr_val
        dist_tp2 = 3.0 * atr_val
        
        sl = preco_ent - dist_sl
        tp1 = preco_ent + dist_sl
        tp2 = preco_ent + dist_tp2
        
        # % de Distância
        perc_sl = (dist_sl / preco_ent) * 100
        
        # Cálculo de Quantidade e Lucro
        if dist_sl > 0:
            qtd_f = valor_risco_fin / dist_sl
            lucro_final = qtd_f * dist_tp2
        else:
            qtd_f = 0.0
            lucro_final = 0.0
            
        invest_t = qtd_f * preco_ent
        
        st.divider()
        m1, m2 = st.columns(2)
        m1.error(f"Stop: {sl:.2f} ({perc_sl:.1f}%)")
        m2.success(f"Alvo Final: {tp2:.2f}")
        
        st.metric("Qtd. Fracionária", f"{qtd_f:.3f} un")
        
        # Nova métrica de Lucro Estimado
        st.metric("Lucro Estimado (TP2)", f"+{lucro_final:.2f}€", delta="Rácio 2:1")
        
        if invest_t > capital_total:
            st.warning(f"Custo total ({invest_t:.2f}€) excede a banca!")

# ==========================================
# 2. MÓDULO: DCA
# ==========================================
with col_dir:
    st.subheader("📉 Módulo DCA")
    with st.container(border=True):
        st.markdown("**Posição Atual**")
        q_atual = st.number_input("Qtd. Atual", value=0.000, format="%.3f")
        p_atual = st.number_input("Preço Médio Atual", value=0.0, format="%.2f")
        
        st.markdown("**Reforço**")
        q_nova = st.number_input("Nova Qtd", value=0.000, format="%.3f")
        p_novo = st.number_input("Preço Novo", value=0.0, format="%.2f")
        
        total_q = q_atual + q_nova
        if total_q > 0:
            novo_pm = ((q_atual * p_atual) + (q_nova * p_novo)) / total_q
            st.divider()
            st.metric("Novo Preço Médio", f"{novo_pm:.2f}")
            st.write(f"Investimento Total: {total_q * novo_pm:.2f}€")

# ==========================================
# 3. RESUMO JOURNAL
# ==========================================
st.divider()
st.subheader("📝 Journal Template")
resumo_j = f"""=== TRADE: {ticker} ===
Entrada: {preco_ent:.2f} | SL: {sl:.2f} ({perc_sl:.1f}%) | TP2: {tp2:.2f}
Qtd: {qtd_f:.3f} | Risco: {valor_risco_fin:.2f}€ | Lucro Alvo: {lucro_final:.2f}€
---
CHECKLIST: [ ] RSI2 < 15 | [ ] Preço > SMA200 | [ ] Sentimento: 
"""
st.code(resumo_j)
