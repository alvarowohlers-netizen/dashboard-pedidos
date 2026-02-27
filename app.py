import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="📊 Dashboard de Pedidos",
    page_icon="📦",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF6B6B;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 5px solid #FF6B6B;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #333;
    }
    .metric-label {
        font-size: 1rem;
        color: #666;
    }
    .refresh-box {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #4ECDC4;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# TÍTULO
# ============================================================================
st.markdown('<h1 class="main-header">📊 DASHBOARD DE PEDIDOS ABERTOS</h1>', unsafe_allow_html=True)

# ============================================================================
# CLASSIFICAÇÃO DOS STATUS
# ============================================================================
CLASSIFICACAO_STATUS = {
    "ALTERAÇÃO DE TRANSPORTADORA": "EXPEDIÇÃO",
    "CANCELAMENTO DE NF": "EXPEDIÇÃO", 
    "CONFERENCIA COM ERRO": "EXPEDIÇÃO",
    "CONFERENCIA OK": "EXPEDIÇÃO",
    "EMISSAO DE NOTA FISCAL": "EXPEDIÇÃO",
    "EXCLUSAO DE VOLUME NA CARGA": "EXPEDIÇÃO",
    "FECHAMENTO DE GAIOLA": "EXPEDIÇÃO",
    "FINALIZACAO DE VOLUMES": "EXPEDIÇÃO",
    "INCLUSAO DE VOLUME NA CARGA": "EXPEDIÇÃO",
    "NOTA FISCAL ACEITA": "EXPEDIÇÃO",
    "REABERTURA DE VOLUMES": "EXPEDIÇÃO",
    "EXCLUSAO DE ONDA DE COLETA": "ABERTOS",
    "FIM DE PICKING": "ABERTOS",
    "INCLUSAO EM ONDA DE COLETA": "ABERTOS",
    "INCLUSAO EM PROGRAMA DE COLETA": "ABERTOS", 
    "INICIO DE CONFERENCIA": "ABERTOS",
    "INICIO DE PICKING": "ABERTOS",
    "NAO ROMANEADO": "ABERTOS",
    "PEDIDO NAO CONFORMIDADE": "ABERTOS",
    "PICKING LIBERADO": "ABERTOS",
    "RECEBIMENTO DO HOST": "ABERTOS"
}

# ============================================================================
# FUNÇÃO PARA CONSULTAR API
# ============================================================================
@st.cache_data(ttl=0)  # SEM CACHE! Sempre busca novo
def consultar_api_pedidos():
    api_url = "https://api-dw.bseller.com.br/webquery/execute/ZBIQ0104"
    token = "5A9D7B5EAC2E7478E05324F3A8C0D448"
    
    payload = {
        "parametros": {
            "P_ID_PLANTA": "PETMG",
            "P_ID_CANAL": None,
            "P_START_ROW": 1,
            "P_PAGE_SIZE": 5000
        }
    }
    
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return {"sucesso": True, "dados": data, "registros": len(data)}
    except:
        pass
    
    return {"sucesso": False, "dados": None}

# ============================================================================
# CONTROLE DE ATUALIZAÇÃO
# ============================================================================

# Inicializar o contador
if 'contador' not in st.session_state:
    st.session_state.contador = 0

# Mostrar caixa de atualização
st.markdown("### ⏰ CONTROLE DE ATUALIZAÇÃO AUTOMÁTICA")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Botão para atualizar manual
    if st.button("🔄 ATUALIZAR MANUAL", type="primary"):
        st.cache_data.clear()
        st.session_state.contador += 1
        st.rerun()

with col2:
    # Mostrar contador de atualizações
    st.markdown(f"<div class='refresh-box'><h3>🔄 {st.session_state.contador}</h3><p>Atualizações</p></div>", unsafe_allow_html=True)

with col3:
    # Timer visível
    timer_placeholder = st.empty()

with col4:
    # Status da API
    api_status = st.empty()

# ============================================================================
# TIMER COM JAVASCRIPT PURO (FORÇA RECARREGAMENTO)
# ============================================================================

# Timer de 60 segundos (1 minuto)
st.components.v1.html("""
<div id="timer" style="text-align: center; font-size: 24px; font-weight: bold; padding: 10px; background: #4ECDC4; color: white; border-radius: 10px; margin: 10px 0;">
    ⏱️ Atualizando em: <span id="seconds">60</span> segundos
</div>

<script>
    // Contador regressivo
    let seconds = 60;
    const timerElement = document.getElementById('seconds');
    
    function updateTimer() {
        seconds--;
        if (seconds <= 0) {
            seconds = 60;
            // Força o recarregamento da página
            window.location.reload();
        }
        timerElement.textContent = seconds;
    }
    
    // Atualiza a cada 1 segundo
    setInterval(updateTimer, 1000);
</script>

<!-- META refresh como fallback -->
<meta http-equiv="refresh" content="65">
""", height=100)

# ============================================================================
# CONSULTAR API
# ============================================================================
resultado = consultar_api_pedidos()

if resultado["sucesso"] and resultado["dados"]:
    api_status.success("✅ API Online")
    df = pd.DataFrame(resultado["dados"])
    
    # Mapeamento das colunas
    df_renamed = df.rename(columns={
        'TIPO_ITEM': 'TIPO_ITEM',
        'TIPO_LIMITE': 'TIPO_LIMITE',
        'ENTREGA': 'COUNT_ENTREGA',
        'QT_PECAS': 'QT_PECAS'
    })
    
    df_renamed['STATUS'] = df['STATUS']
    df_renamed['COUNT_ENTREGA'] = pd.to_numeric(df_renamed['COUNT_ENTREGA'], errors='coerce').fillna(1)
    df_renamed['QT_PECAS'] = pd.to_numeric(df_renamed['QT_PECAS'], errors='coerce').fillna(0)
    
    df_renamed['TIPO_PEDIDO'] = df_renamed['STATUS'].map(CLASSIFICACAO_STATUS)
    df_renamed['TIPO_PEDIDO'] = df_renamed['TIPO_PEDIDO'].fillna('OUTROS')
    
    df_abertos = df_renamed[df_renamed['TIPO_PEDIDO'] == 'ABERTOS'].copy()
    
    # ============================================================================
    # MÉTRICAS
    # ============================================================================
    st.markdown("---")
    st.markdown("### 📈 MÉTRICAS ATUAIS")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(df_abertos):,}</div>
            <div class="metric-label">📦 Pedidos Abertos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_pecas = df_abertos['QT_PECAS'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_pecas:,}</div>
            <div class="metric-label">🧩 Total de Peças</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        media = total_pecas / len(df_abertos) if len(df_abertos) > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{media:.1f}</div>
            <div class="metric-label">📊 Média Peças/Pedido</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{df_abertos['STATUS'].nunique()}</div>
            <div class="metric-label">🔄 Status</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ============================================================================
    # GRÁFICOS
    # ============================================================================
    if len(df_abertos) > 0:
        st.markdown("---")
        st.markdown("### 📊 ANÁLISE GRÁFICA")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📦 Pedidos por Tipo de Limite")
            pivot = pd.crosstab(
                df_abertos['TIPO_LIMITE'],
                df_abertos['TIPO_ITEM'],
                values=df_abertos['COUNT_ENTREGA'],
                aggfunc='sum'
            ).fillna(0)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            cores = sns.color_palette("husl", len(pivot.columns))
            pivot.plot(kind='bar', stacked=True, ax=ax, color=cores)
            ax.set_xlabel('Tipo de Limite')
            ax.set_ylabel('Quantidade de Pedidos')
            plt.xticks(rotation=45)
            st.pyplot(fig)
        
        with col2:
            st.subheader("🧩 Peças por Tipo de Limite")
            pivot2 = pd.crosstab(
                df_abertos['TIPO_LIMITE'],
                df_abertos['TIPO_ITEM'],
                values=df_abertos['QT_PECAS'],
                aggfunc='sum'
            ).fillna(0)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            pivot2.plot(kind='bar', stacked=True, ax=ax, color=cores)
            ax.set_xlabel('Tipo de Limite')
            ax.set_ylabel('Quantidade de Peças')
            plt.xticks(rotation=45)
            st.pyplot(fig)
        
        # ============================================================================
        # TABELA
        # ============================================================================
        st.markdown("---")
        st.markdown("### 📋 DADOS DETALHADOS")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            tipos_limite = ['Todos'] + sorted(df_abertos['TIPO_LIMITE'].unique().tolist())
            filtro_limite = st.selectbox("Filtrar por Tipo Limite", tipos_limite)
        with col2:
            tipos_item = ['Todos'] + sorted(df_abertos['TIPO_ITEM'].unique().tolist())
            filtro_item = st.selectbox("Filtrar por Tipo Item", tipos_item)
        with col3:
            status_opcoes = ['Todos'] + sorted(df_abertos['STATUS'].unique().tolist())
            filtro_status = st.selectbox("Filtrar por Status", status_opcoes)
        
        df_filtrado = df_abertos.copy()
        if filtro_limite != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['TIPO_LIMITE'] == filtro_limite]
        if filtro_item != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['TIPO_ITEM'] == filtro_item]
        if filtro_status != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['STATUS'] == filtro_status]
        
        st.dataframe(df_filtrado, use_container_width=True, height=400)
        
        # Download
        csv = df_filtrado.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"pedidos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
else:
    st.error("❌ Erro ao conectar com a API")
    api_status.error("❌ API Offline")

# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
st.markdown(f"🕒 Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
st.markdown("🔄 Atualização automática a cada 1 minuto")