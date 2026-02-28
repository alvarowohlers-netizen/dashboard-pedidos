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
    page_title="📺 TV Dashboard - Pedidos",
    page_icon="📊",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
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
    .section-header {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        border-left: 5px solid #4ECDC4;
    }
    .refresh-info {
        background: #e8f4fd;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-size: 1.5rem;
        margin: 20px 0;
        border: 3px solid #4ECDC4;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# TÍTULO
# ============================================================================
st.markdown('<h1 class="main-header">📊 DASHBOARD DE PEDIDOS ABERTOS - TV</h1>', unsafe_allow_html=True)

# ============================================================================
# CONTADOR DE REFRESH (usa session_state)
# ============================================================================
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0
else:
    st.session_state.refresh_count += 1

# Mostra informação do refresh
st.markdown(f"""
<div class="refresh-info">
    🔄 AUTO-REFRESH ATIVO | Atualização #{st.session_state.refresh_count} | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# ============================================================================
# META REFRESH - A CADA 60 SEGUNDOS (1 MINUTO)
# ============================================================================
st.markdown("""
<meta http-equiv="refresh" content="60">
""", unsafe_allow_html=True)

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
# FUNÇÃO PARA CONSULTAR API (SEM CACHE PARA TESTE)
# ============================================================================
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
    except Exception as e:
        return {"sucesso": False, "dados": None, "erro": str(e)}
    
    return {"sucesso": False, "dados": None}

# ============================================================================
# CONSULTAR API
# ============================================================================
with st.spinner("📡 Buscando dados..."):
    resultado = consultar_api_pedidos()

if resultado["sucesso"] and resultado["dados"]:
    df = pd.DataFrame(resultado["dados"])
    
    # Processar dados
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
    # GRÁFICOS - TODOS OS QUE VOCÊ QUER
    # ============================================================================
    if len(df_abertos) > 0:
        # GRÁFICO 1: Barras empilhadas
        st.markdown('<p class="section-header">📦 PEDIDOS POR TIPO DE LIMITE</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            pivot = pd.crosstab(
                df_abertos['TIPO_LIMITE'],
                df_abertos['TIPO_ITEM'],
                values=df_abertos['COUNT_ENTREGA'],
                aggfunc='sum'
            ).fillna(0)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            cores = sns.color_palette("husl", len(pivot.columns))
            pivot.plot(kind='bar', stacked=True, ax=ax, color=cores)
            ax.set_title('Quantidade de Pedidos', fontsize=14, fontweight='bold')
            ax.set_xlabel('Tipo de Limite', fontsize=12)
            ax.set_ylabel('Quantidade de Pedidos', fontsize=12)
            ax.legend(title='Tipo Item')
            plt.xticks(rotation=45)
            st.pyplot(fig)
        
        with col2:
            pivot2 = pd.crosstab(
                df_abertos['TIPO_LIMITE'],
                df_abertos['TIPO_ITEM'],
                values=df_abertos['QT_PECAS'],
                aggfunc='sum'
            ).fillna(0)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            pivot2.plot(kind='bar', stacked=True, ax=ax, color=cores)
            ax.set_title('Quantidade de Peças', fontsize=14, fontweight='bold')
            ax.set_xlabel('Tipo de Limite', fontsize=12)
            ax.set_ylabel('Quantidade de Peças', fontsize=12)
            ax.legend(title='Tipo Item')
            plt.xticks(rotation=45)
            st.pyplot(fig)
        
        # GRÁFICO 2: Top Status
        st.markdown('<p class="section-header">🏆 ANÁLISE POR STATUS</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            status_count = df_abertos['STATUS'].value_counts().head(10)
            fig, ax = plt.subplots(figsize=(10, 6))
            status_count.plot(kind='barh', ax=ax, color='#4ECDC4')
            ax.set_title('Top 10 Status', fontsize=14, fontweight='bold')
            ax.set_xlabel('Quantidade')
            st.pyplot(fig)
        
        with col2:
            status_media = df_abertos.groupby('STATUS')['QT_PECAS'].mean().sort_values(ascending=False).head(10)
            fig, ax = plt.subplots(figsize=(10, 6))
            status_media.plot(kind='barh', ax=ax, color='#FF6B6B')
            ax.set_title('Média de Peças por Status', fontsize=14, fontweight='bold')
            ax.set_xlabel('Média')
            st.pyplot(fig)
        
        # GRÁFICO 3: Gráficos de pizza
        st.markdown('<p class="section-header">🥧 DISTRIBUIÇÃO</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            item_count = df_abertos['TIPO_ITEM'].value_counts()
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(item_count.values, labels=item_count.index, autopct='%1.1f%%')
            ax.set_title('Pedidos por Tipo Item', fontsize=14, fontweight='bold')
            st.pyplot(fig)
        
        with col2:
            item_pecas = df_abertos.groupby('TIPO_ITEM')['QT_PECAS'].sum()
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(item_pecas.values, labels=item_pecas.index, autopct='%1.1f%%')
            ax.set_title('Peças por Tipo Item', fontsize=14, fontweight='bold')
            st.pyplot(fig)
        
        # TABELA
        st.markdown('<p class="section-header">📋 DADOS DETALHADOS</p>', unsafe_allow_html=True)
        st.dataframe(df_abertos, use_container_width=True, height=400)
    
    else:
        st.warning("⚠️ Nenhum pedido aberto encontrado")
    
else:
    st.error("❌ Erro ao conectar com a API")

# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray; padding: 20px; font-size: 1.2rem;'>
    <p>⏱️ Próxima atualização em 60 segundos</p>
    <p>🕒 Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    <p>🔄 Total de atualizações: {st.session_state.refresh_count}</p>
</div>
""", unsafe_allow_html=True)