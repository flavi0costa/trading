import streamlit as st
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Momentum Precision", layout="wide")

st.title("🧮 Calculadora de Trading (Versão Final)")

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

# Inicialização de colunas
col_esq, col_dir = st.columns(2)

# Inicialização de variáveis para evitar erros no resumo
novo_pm = 0.0
total_q = 0.0

# ==========================================
# 1. MÓDULO: NOVA POSIÇÃO
# ==========================================
with col_esq:
    st.subheader("🚀 Nova Posição")
    with st.container(border=True):
        ticker = st.text_input("Ticker", "NVDA").upper()
        preco_ent = st.number_input("Preço de Entrada", value=10.00, format="%.2f")
        atr_val = st.number_input("ATR", value=1.0000, format="%.4f")
        
        # Cálculos Momentum
        dist_sl = 1.5 * atr_val
        sl = preco_ent - dist_sl
        tp1 = preco_ent + dist_sl
        tp2 = preco_ent + (3.0 * atr_val)
        
        # Percentagem de Distância do Stop
        perc_sl = (dist_sl / preco_ent) * 100 if preco_ent > 0 else 0
        
        # Quantidade (Regra do Risco)
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
# 2. MÓDULO: DCA (AJUSTE DE MÉDIO)
# ==========================================
with col_dir:
    st.subheader("📉 Módulo DCA")
    with st.container(border=True):
        q_atual = st.number_input("Qtd. Atual", value=0.000, format="%.3f")
        p_atual = st.number_input("Preço Médio Atual", value=0.00, format="%.2f")
        
        st.write("---")
        q_nova = st.number_input("Qtd. Nova Compra", value=0.000, format="%.3f")
        p_novo = st.number_input("Preço Nova Compra", value=0.00, format="%.2f")
        
        total_q = q_atual + q_nova
        if total_q > 0:
            novo_pm = ((q_atual * p_atual) + (q_nova * p_novo)) / total_q
            total_inv = total_q * novo_pm
            
            st.divider()
            st.metric("Novo Preço Médio", f"{novo_pm:.2f}")
            st.info(f"Investimento Total Acumulado: {total_inv:.2f}€")

# ==========================================
# 3. RESUMO PARA DIÁRIO (JOURNAL)
# ==========================================
st.divider()
st.subheader("📝 Resumo para Diário de Trader")

# Prepara os textos antes para evitar erros de formatação
pm_texto = f"{novo_pm:.2f}" if total_q > 0 else "N/A"
total_q_texto = f"{total_q:.3f}" if total_q > 0 else "N/A"
data_op = st.date_input("Data da Operação", value=datetime.now())

resumo_journal = f"""=== REGISTO DE TRADE: {ticker} ===
Data: {data_op.strftime('%d/%m/%Y')}
-----------------------------------------
ENTRADA: {preco_ent:.2f} | STOP: {sl:.2f} ({perc_sl:.1f}%)
ALVO 1: {tp1:.2f} | ALVO 2: {tp2:.2f}
QTD: {qtd_f:.3f} | INVESTIDO: {invest_t:.2f}€
RISCO REAL: {valor_risco_fin:.2f}€

AJUSTE DCA (Se feito):
Novo Preço Médio: {pm_texto} | Qtd Total: {total_q_texto}

NOTAS:
[ ] Tendência Alinhada? | [ ] RSI 2 Abaixo de 15?
Sentimento: 
-----------------------------------------"""

st.code(resumo_journal, language="text")
st.caption("Copia o texto acima e guarda no teu histórico de trades.")import streamlit as st
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Momentum Precision", layout="wide")

st.title("🧮 Calculadora de Trading (Versão Final)")

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

# Inicialização de colunas
col_esq, col_dir = st.columns(2)

# Inicialização de variáveis para evitar erros no resumo
novo_pm = 0.0
total_q = 0.0

# ==========================================
# 1. MÓDULO: NOVA POSIÇÃO
# ==========================================
with col_esq:
    st.subheader("🚀 Nova Posição")
    with st.container(border=True):
        ticker = st.text_input("Ticker", "NVDA").upper()
        preco_ent = st.number_input("Preço de Entrada", value=10.00, format="%.2f")
        atr_val = st.number_input("ATR", value=1.0000, format="%.4f")
        
        # Cálculos Momentum
        dist_sl = 1.5 * atr_val
        sl = preco_ent - dist_sl
        tp1 = preco_ent + dist_sl
        tp2 = preco_ent + (3.0 * atr_val)
        
        # Percentagem de Distância do Stop
        perc_sl = (dist_sl / preco_ent) * 100 if preco_ent > 0 else 0
        
        # Quantidade (Regra do Risco)
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
# 2. MÓDULO: DCA (AJUSTE DE MÉDIO)
# ==========================================
with col_dir:
    st.subheader("📉 Módulo DCA")
    with st.container(border=True):
        q_atual = st.number_input("Qtd. Atual", value=0.000, format="%.3f")
        p_atual = st.number_input("Preço Médio Atual", value=0.00, format="%.2f")
        
        st.write("---")
        q_nova = st.number_input("Qtd. Nova Compra", value=0.000, format="%.3f")
        p_novo = st.number_input("Preço Nova Compra", value=0.00, format="%.2f")
        
        total_q = q_atual + q_nova
        if total_q > 0:
            novo_pm = ((q_atual * p_atual) + (q_nova * p_novo)) / total_q
            total_inv = total_q * novo_pm
            
            st.divider()
            st.metric("Novo Preço Médio", f"{novo_pm:.2f}")
            st.info(f"Investimento Total Acumulado: {total_inv:.2f}€")

# ==========================================
# 3. RESUMO PARA DIÁRIO (JOURNAL)
# ==========================================
st.divider()
st.subheader("📝 Resumo para Diário de Trader")

# Prepara os textos antes para evitar erros de formatação
pm_texto = f"{novo_pm:.2f}" if total_q > 0 else "N/A"
total_q_texto = f"{total_q:.3f}" if total_q > 0 else "N/A"
data_op = st.date_input("Data da Operação", value=datetime.now())

resumo_journal = f"""=== REGISTO DE TRADE: {ticker} ===
Data: {data_op.strftime('%d/%m/%Y')}
-----------------------------------------
ENTRADA: {preco_ent:.2f} | STOP: {sl:.2f} ({perc_sl:.1f}%)
ALVO 1: {tp1:.2f} | ALVO 2: {tp2:.2f}
QTD: {qtd_f:.3f} | INVESTIDO: {invest_t:.2f}€
RISCO REAL: {valor_risco_fin:.2f}€

AJUSTE DCA (Se feito):
Novo Preço Médio: {pm_texto} | Qtd Total: {total_q_texto}

NOTAS:
[ ] Tendência Alinhada? | [ ] RSI 2 Abaixo de 15?
Sentimento: 
-----------------------------------------"""

st.code(resumo_journal, language="text")
st.caption("Copia o texto acima e guarda no teu histórico de trades.")
