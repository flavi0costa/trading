import streamlit as st
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Momentum & DCA Precision", layout="wide")

st.title("🧮 Calculadora de Trading (Fracionária + DCA)")
st.caption("Configurada para Banca de 500€ e Estratégia de Momentum")

# ==========================================
# CONFIGURAÇÕES DE BANCA (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("⚙️ Gestão de Banca")
    capital_total = st.number_input("Banca Total (€)", value=500.0)
    risco_perc = st.slider("Risco por Trade (%)", 0.1, 5.0, 1.0)
    valor_risco_fin = capital_total * (risco_perc / 100)
    
    st.divider()
    st.metric("Risco Máximo Permitido", f"{valor_risco_fin:.2f}€")
    st.info("O teu objetivo é nunca perder mais do que o valor acima por trade.")

# Criação de colunas para os dois módulos principais
col_esq, col_dir = st.columns(2)

# Variáveis globais para o resumo final (inicialização)
novo_pm = 0.0
total_q = 0.0

# ==========================================
# 1. MÓDULO: NOVA POSIÇÃO (MOMENTUM)
# ==========================================
with col_esq:
    st.subheader("🚀 Nova Posição")
    with st.container(border=True):
        ticker = st.text_input("Ticker (Ex: NVDA)", "NVDA").upper()
        preco_ent = st.number_input("Preço de Entrada ($/€)", value=100.0, format="%.2f")
        atr_val = st.number_input("Valor ATR (do Dashboard)", value=2.0, format="%.4f")
        
    # Lógica Momentum (1.5x ATR para Stop)
        dist_sl = 1.5 * atr_val
        
        # Garantir que a distância do stop não é zero para evitar divisão por zero
        if dist_sl > 0:
            qtd_f = valor_risco_fin / dist_sl
        else:
            qtd_f = 0.0

        sl = preco_ent - dist_sl
        tp1 = preco_ent + dist_sl
        tp2 = preco_ent + (3.0 * atr_val)
        
        invest_t = qtd_f * preco_ent
        
        # Cálculo de Quantidade Fracionária (3 casas decimais)
        if dist_sl > 0:
            qtd_f = valor_risco_fin / dist_sl
        else:
            qtd_f = 0.0
            
        invest_t = qtd_f * preco_ent
        
        st.divider()
        st.error(f"**STOP LOSS: {sl:.2f}**")
        st.success(f"**TP1 (50%): {tp1:.2f} | TP2 (Final): {tp2:.2f}**")
        
        c_res1, c_res2 = st.columns(2)
        c_res1.metric("Qtd. a Comprar", f"{qtd_f:.3f}")
        
        if invest_t > capital_total:
            c_res2.warning(f"Custo: {invest_t:.2f}€")
            st.error("⚠️ Atenção: Posição excede o teu capital total!")
        else:
            c_res2.metric("Investimento Total", f"{invest_t:.2f}€")

# ==========================================
# 2. MÓDULO: CÁLCULO DE DCA
# ==========================================
with col_dir:
    st.subheader("📉 Ajuste de Preço Médio (DCA)")
    with st.container(border=True):
        st.markdown("**Posição Atual**")
        c_at1, c_at2 = st.columns(2)
        q_atual = c_at1.number_input("Qtd. que já tens", value=0.000, format="%.3f", step=0.001)
        p_atual = c_at2.number_input("Preço Médio Atual", value=0.0, format="%.2f")
        
        st.markdown("**Nova Compra (Reforço)**")
        c_nv1, c_nv2 = st.columns(2)
        q_nova = c_nv1.number_input("Qtd. a adicionar", value=0.000, format="%.3f", step=0.001)
        p_novo = c_nv2.number_input("Preço da nova compra", value=0.0, format="%.2f")
        
        # Lógica DCA
        total_q = q_atual + q_nova
        if total_q > 0:
            novo_pm = ((q_atual * p_atual) + (q_nova * p_novo)) / total_q
            total_inv = total_q * novo_pm
            reducao = ((p_atual - novo_pm) / p_atual * 100) if p_atual > 0 else 0
            
            st.divider()
            st.metric("Novo Preço Médio", f"{novo_pm:.2f}", 
                      delta=f"-{reducao:.2f}%" if reducao > 0 else None)
            
            c_dca1, c_dca2 = st.columns(2)
            c_dca1.write(f"Total Ações: **{total_q:.3f}**")
            c_dca2.write(f"Custo Total: **{total_inv:.2f}€**")
            
            if total_inv > capital_total:
                st.error("⚠️ Posição total excede a banca!")
        else:
            st.info("Insere dados para calcular o novo preço médio.")

# ==========================================
# 3. RESUMO PARA REGISTO (JOURNAL READY)
# ==========================================
st.divider()
st.subheader("📝 Resumo para Diário de Trader")

# Data para o registo
data_trade = st.date_input("Data da Operação", value=datetime.now())

# Construção do texto otimizado para o Journal
resumo_journal = f"""=== REGISTO DE TRADE: {ticker} ===
Data: {data_trade.strftime('%d/%m/%Y')}
-----------------------------------------
DADOS TÉCNICOS:
Entrada Original: ${preco_ent:.2f}
Stop Loss (1.5x ATR): ${sl:.2f}
Alvo 1 (Rácio 1:1): ${tp1:.2f}
Alvo 2 (Rácio 2:1): ${tp2:.2f}
Qtd Sugerida: {qtd_f:.3f} un | Risco Financeiro: {valor_risco_fin:.2f}€

STATUS DCA (Se aplicável):
Novo Preço Médio: {novo_pm:.2f if total_q > 0 else 'N/A'}
Total Ações Acumuladas: {total_q:.3f if total_q > 0 else 'N/A'}

CHECKLIST PRÉ-TRADE:
[ ] Tendência: Preço acima da SMA 200 e EMA 21 > EMA 50?
[ ] Setup: RSI 2 abaixo de 15?
[ ] Volatilidade: ATR atualizado no cálculo?
[ ] Risco: A perda máxima é de apenas {valor_risco_fin:.2f}€?

NOTAS DE EXECUÇÃO:
- Sentimento: 
- Erros cometidos:
- Por que saí do trade:
-----------------------------------------
"""

st.code(resumo_journal, language="text")
st.caption("Clica no ícone de cópia (canto superior direito da caixa) e cola no teu Journal (Telegram/Notion).")
