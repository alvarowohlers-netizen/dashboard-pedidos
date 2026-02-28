import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="📺 TV Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# META REFRESH - A CADA 1 MINUTO (MAIS SIMPLES POSSÍVEL)
# ============================================================================
st.markdown("""
<meta http-equiv="refresh" content="60">
<style>
    .main-title {
        font-size: 2.5rem;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .metric-box {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 5px solid #FF6B6B;
        margin: 0.5rem;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #333;
    }
    .metric-label {
        font-size: 1rem;
        color: #666;
    }
    .refresh-status {
        background: #e8f4fd;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
        font-size: 1.2rem;
        border: 2px solid #4ECDC4;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# TÍTULO
# ============================================================================
st.markdown('<div class="main-title">📊 DASHBOARD DE PEDIDOS - TV</div>', unsafe_allow_html=True)

# ============================================================================
# CONTADOR DE REFRESH
# ============================================================================
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0
else:
    st.session_state.refresh_count += 1

st.markdown(f"""
<div class="refresh-status">
    🔄 Atualização #{st.session_state.refresh_count} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# ============================================================================
# CLASSIFICAÇÃO DOS STATUS (SIMPLIFICADA)
# ============================================================================
STATUS_ABERTOS = [
    "EXCLUSAO DE ONDA DE COLETA",
    "FIM DE PICKING",
    "INCLUSAO EM ONDA DE COLETA",
    "INCLUSAO EM PROGRAMA DE COLETA",
    "INICIO DE CONFERENCIA",
    "INICIO DE PICKING",
    "NAO ROMANEADO",
    "PEDIDO NAO CONFORMIDADE",
    "PICKING LIBERADO",
    "RECEBIMENTO DO HOST"
]

# ============================================================================
# FUNÇÃO PARA CONSULTAR API (SIMPLIFICADA)
# ============================================================================
def consultar_api():
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
            return {"sucesso": True, "dados": data}
    except:
        pass
    
    return {"sucesso": False, "dados": None}

# ============================================================================
# CONSULTAR API
# ============================================================================
resultado = consultar_api()

if resultado["sucesso"] and resultado["dados"]:
    df = pd.DataFrame(resultado["dados"])
    
    # Filtrar apenas status abertos
    df_abertos = df[df['STATUS'].isin(STATUS_ABERTOS)].copy()
    
    # Garantir colunas necessárias
    if 'QT_PECAS' not in df_abertos.columns:
        df_abertos['QT_PECAS'] = 1
    if 'TIPO_ITEM' not in df_abertos.columns:
        df_abertos['TIPO_ITEM'] = 'N/A'
    if 'TIPO_LIMITE' not in df_abertos.columns:
        df_abertos['TIPO_LIMITE'] = 'N/A'
    
    # Converter para numérico
    df_abertos['QT_PECAS'] = pd.to_numeric(df_abertos['QT_PECAS'], errors='coerce').fillna(0)
    
    # ============================================================================
    # MÉTRICAS
    # ============================================================================
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{len(df_abertos):,}</div>
            <div class="metric-label">📦 Pedidos Abertos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_pecas = df_abertos['QT_PECAS'].sum()
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{total_pecas:,.0f}</div>
            <div class="metric-label">🧩 Total Peças</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        media = total_pecas / len(df_abertos) if len(df_abertos) > 0 else 0
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{media:.1f}</div>
            <div class="metric-label">📊 Média Peças</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{df_abertos['STATUS'].nunique()}</div>
            <div class="metric-label">🔄 Status</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ============================================================================
    # GRÁFICO SIMPLES
    # ============================================================================
    if len(df_abertos) > 0:
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Pedidos por Status")
            status_count = df_abertos['STATUS'].value_counts().head(10)
            fig, ax = plt.subplots(figsize=(10, 6))
            status_count.plot(kind='barh', ax=ax, color='#4ECDC4')
            ax.set_xlabel('Quantidade')
            st.pyplot(fig)
        
        with col2:
            st.subheader("📊 Peças por Status")
            status_pecas = df_abertos.groupby('STATUS')['QT_PECAS'].sum().sort_values(ascending=False).head(10)
            fig, ax = plt.subplots(figsize=(10, 6))
            status_pecas.plot(kind='barh', ax=ax, color='#FF6B6B')
            ax.set_xlabel('Quantidade de Peças')
            st.pyplot(fig)
        
        # Tabela
        st.markdown("---")
        st.subheader("📋 Dados")
        st.dataframe(df_abertos[['STATUS', 'QT_PECAS', 'TIPO_ITEM', 'TIPO_LIMITE']].head(50), 
                    use_container_width=True, height=400)
    
else:
    st.error("❌ Erro na API - Usando dados de exemplo")
    
    # Dados de exemplo
    dados_exemplo = []
    for i in range(100):
        dados_exemplo.append({
            'STATUS': np.random.choice(STATUS_ABERTOS),
            'QT_PECAS': np.random.randint(1, 100),
            'TIPO_ITEM': np.random.choice(['Mono', 'Duo', '3 itens+']),
            'TIPO_LIMITE': np.random.choice(['D+0', 'D+1', 'D+2', 'D+3', 'D+4+'])
        })
    df_abertos = pd.DataFrame(dados_exemplo)
    st.rerun()

# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray; padding: 10px;'>
    ⏱️ Próxima atualização em 60 segundos
</div>
""", unsafe_allow_html=True)