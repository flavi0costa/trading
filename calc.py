import streamlit as st
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Momentum Precision", layout="wide")

st.title("🧮 Calculadora de Trading (Corrigida)")

# ==========================================
# SIDEBAR: GESTÃO DE BANCA
# ==========================================
with st.sidebar:
    st.header("⚙️ Gestão de Banca")
    capital_total = st.number_input("Banca Total (€)", value=300.0)
    risco_perc = st.slider("Risco por Trade (%)", 0.1, 5.0, 1.0)
    valor_risco_fin = capital_total * (risco_perc / 100)
    
    st.divider()
    st.metric("Risco Máximo (€)", f"{valor_risco_fin:.2f}€")

col_esq, col_dir = st.columns(2)

# Inicialização de variáveis para evitar erros de referência
novo_pm = 0.0
total_q = 0.0

# ==========================================
# 1. NOVA POSIÇÃO
# ==========================================
with col_esq:
    st.subheader("🚀 Nova Posição")
    with st.container(border=True):
        ticker = st.text_input("Ticker", "NVDA").upper()
        preco_ent = st.number_input("Preço de Entrada", value=10.00, format="%.2f")
        atr_val = st.number_input("ATR", value=1.0000, format="%.4f")
        
        # Cálculos Matemáticos
        dist_sl = 1.5 * atr_val
        sl = preco_ent - dist_sl
        tp1 = preco_ent + dist_sl
        tp2 = preco_ent + (3.0 * atr_val)
        
        # % de Distância do Stop (Para contexto visual)
        perc_sl = (dist_sl / preco_ent) * 100 if preco_ent > 0 else 0
        
        if dist_sl > 0:
            qtd_f = valor_risco_fin / dist_sl
        else:
            qtd_f = 0.0
            
        invest_t = qtd_f * preco_ent
        
        st.divider()
        st.error(f"**STOP LOSS: {sl:.2f}** ({perc_sl:.1f}% de queda)")
        st.success(f"**TP1: {tp1:.2f} | TP2: {tp2:.2f}**")
        
        c1, c2 = st.columns(2)
        c1.metric("Qtd. a Comprar", f"{qtd_f:.3f}")
        c2.metric("Investimento", f"{invest_t:.2f}€")

# ==========================================
# 2. MÓDULO DCA
# ==========================================
with col_dir:
    st.subheader("📉 Módulo DCA")
    with st.container(border=True):
        q_atual = st.number_input("Qtd. Atual", value=0.000, format="%.3f")
        p_atual = st.number_input("Preço Médio Atual", value=0.00, format="%.2f")
        q_nova = st.number_input("Qtd. Nova", value=0.000, format="%.3f")
        p_novo = st.number_input("Preço Novo", value=0.00, format="%.2f")
        
        total_q = q_atual + q_nova
        if total_q > 0:
            novo_pm = ((q_atual * p_atual) + (q_nova * p_novo)) / total_q
            total_inv = total_q * novo_pm
            st.divider()
            st.metric("Novo Preço Médio", f"{novo_pm:.2f}")
            st.write(f"Investimento Total: {total_inv:.2f}€")

# ==========================================
# 3. RESUMO (CORREÇÃO DO ERRO DE FORMATAÇÃO)
# ==========================================
st.divider()
st.subheader("📝 Resumo para Diário de Trader")

data_op = st.date_input("Data da Operação", value=datetime.now())

# Preparar os valores antes da f-string para evitar o ValueError
pm_texto = f"{novo_pm:.2f}" if total_q > 0 else "N/A"
total_q_texto = f"{total_q:.3f}" if total_q > 0 else "N/A"

resumo_journal = f"""=== REGISTO DE TRADE: {ticker} ===
Data: {data_op.strftime('%d/%m/%Y')}
-----------------------------------------
Entrada: {preco_ent:.2f} | Stop: {sl:.2f} ({perc_sl:.1f}%)
Alvo 1: {tp1:.2f} | Alvo 2: {tp2:.2f}
Quantidade: {qtd_f:.3f} | Investimento: {invest_t:.2f}€
Risco Financeiro: {valor_risco_fin:.2f}€

DCA/AJUSTE:
Novo PM: {pm_texto} | Qtd Final: {total_q_texto}

NOTAS:
[ ] Tendência OK? [ ] RSI 2 OK?
Sentimento: 
-----------------------------------------"""

st.code(resumo_journal, language="text")import streamlit as st
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Momentum Precision", layout="wide")

st.title("🧮 Calculadora de Trading (Corrigida)")

# ==========================================
# SIDEBAR: GESTÃO DE BANCA
# ==========================================
with st.sidebar:
    st.header("⚙️ Gestão de Banca")
    capital_total = st.number_input("Banca Total (€)", value=300.0)
    risco_perc = st.slider("Risco por Trade (%)", 0.1, 5.0, 1.0)
    valor_risco_fin = capital_total * (risco_perc / 100)
    
    st.divider()
    st.metric("Risco Máximo (€)", f"{valor_risco_fin:.2f}€")

col_esq, col_dir = st.columns(2)

# Inicialização de variáveis para evitar erros de referência
novo_pm = 0.0
total_q = 0.0

# ==========================================
# 1. NOVA POSIÇÃO
# ==========================================
with col_esq:
    st.subheader("🚀 Nova Posição")
    with st.container(border=True):
        ticker = st.text_input("Ticker", "NVDA").upper()
        preco_ent = st.number_input("Preço de Entrada", value=10.00, format="%.2f")
        atr_val = st.number_input("ATR", value=1.0000, format="%.4f")
        
        # Cálculos Matemáticos
        dist_sl = 1.5 * atr_val
        sl = preco_ent - dist_sl
        tp1 = preco_ent + dist_sl
        tp2 = preco_ent + (3.0 * atr_val)
        
        # % de Distância do Stop (Para contexto visual)
        perc_sl = (dist_sl / preco_ent) * 100 if preco_ent > 0 else 0
        
        if dist_sl > 0:
            qtd_f = valor_risco_fin / dist_sl
        else:
            qtd_f = 0.0
            
        invest_t = qtd_f * preco_ent
        
        st.divider()
        st.error(f"**STOP LOSS: {sl:.2f}** ({perc_sl:.1f}% de queda)")
        st.success(f"**TP1: {tp1:.2f} | TP2: {tp2:.2f}**")
        
        c1, c2 = st.columns(2)
        c1.metric("Qtd. a Comprar", f"{qtd_f:.3f}")
        c2.metric("Investimento", f"{invest_t:.2f}€")

# ==========================================
# 2. MÓDULO DCA
# ==========================================
with col_dir:
    st.subheader("📉 Módulo DCA")
    with st.container(border=True):
        q_atual = st.number_input("Qtd. Atual", value=0.000, format="%.3f")
        p_atual = st.number_input("Preço Médio Atual", value=0.00, format="%.2f")
        q_nova = st.number_input("Qtd. Nova", value=0.000, format="%.3f")
        p_novo = st.number_input("Preço Novo", value=0.00, format="%.2f")
        
        total_q = q_atual + q_nova
        if total_q > 0:
            novo_pm = ((q_atual * p_atual) + (q_nova * p_novo)) / total_q
            total_inv = total_q * novo_pm
            st.divider()
            st.metric("Novo Preço Médio", f"{novo_pm:.2f}")
            st.write(f"Investimento Total: {total_inv:.2f}€")

# ==========================================
# 3. RESUMO (CORREÇÃO DO ERRO DE FORMATAÇÃO)
# ==========================================
st.divider()
st.subheader("📝 Resumo para Diário de Trader")

data_op = st.date_input("Data da Operação", value=datetime.now())

# Preparar os valores antes da f-string para evitar o ValueError
pm_texto = f"{novo_pm:.2f}" if total_q > 0 else "N/A"
total_q_texto = f"{total_q:.3f}" if total_q > 0 else "N/A"

resumo_journal = f"""=== REGISTO DE TRADE: {ticker} ===
Data: {data_op.strftime('%d/%m/%Y')}
-----------------------------------------
Entrada: {preco_ent:.2f} | Stop: {sl:.2f} ({perc_sl:.1f}%)
Alvo 1: {tp1:.2f} | Alvo 2: {tp2:.2f}
Quantidade: {qtd_f:.3f} | Investimento: {invest_t:.2f}€
Risco Financeiro: {valor_risco_fin:.2f}€

DCA/AJUSTE:
Novo PM: {pm_texto} | Qtd Final: {total_q_texto}

NOTAS:
[ ] Tendência OK? [ ] RSI 2 OK?
Sentimento: 
-----------------------------------------"""

st.code(resumo_journal, language="text")
