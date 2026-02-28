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
    page_title="📺 TV Dashboard - Pedidos",
    page_icon="📊",
    layout="wide"
)

# CSS personalizado (versão original)
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
    .section-header {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        border-left: 5px solid #4ECDC4;
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
st.markdown('<h1 class="main-header">📊 DASHBOARD DE PEDIDOS ABERTOS - TV</h1>', unsafe_allow_html=True)

# ============================================================================
# CONFIGURAÇÃO DE TEMPO (1 MINUTO PARA TESTE)
# ============================================================================
MINUTOS_PARA_REFRESH = 1  # 1 minuto para teste
SEGUNDOS_PARA_REFRESH = MINUTOS_PARA_REFRESH * 60

# ============================================================================
# CLASSIFICAÇÃO DOS STATUS (COMPLETA)
# ============================================================================
CLASSIFICACAO_STATUS = {
    # EXPEDIÇÃO
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
    
    # ABERTOS
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
@st.cache_data(ttl=30)  # Cache de 30 segundos
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
# MÚLTIPLOS MÉTODOS DE REFRESH (1 MINUTO)
# ============================================================================

# MÉTODO 1: META REFRESH
st.markdown(f"""
<meta http-equiv="refresh" content="{SEGUNDOS_PARA_REFRESH}">
""", unsafe_allow_html=True)

# MÉTODO 2: JAVASCRIPT COM TIMER
st.components.v1.html(f"""
<script>
    // Timer visual
    var timerDiv = document.createElement('div');
    timerDiv.style.cssText = 'position: fixed; bottom: 20px; right: 20px; background: #333; color: white; padding: 15px; border-radius: 10px; z-index: 9999; font-size: 18px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3);';
    timerDiv.id = 'tv-timer';
    document.body.appendChild(timerDiv);
    
    var seconds = {SEGUNDOS_PARA_REFRESH};
    setInterval(function() {{
        seconds--;
        if (seconds <= 0) {{
            seconds = {SEGUNDOS_PARA_REFRESH};
            window.location.reload(true);
        }}
        var display = Math.floor(seconds / 60) + 'min ' + (seconds % 60) + 's';
        document.getElementById('tv-timer').innerHTML = '🔄 ' + display;
    }}, 1000);
    
    // Força reload no tempo exato
    setTimeout(function() {{
        window.location.reload(true);
    }}, {SEGUNDOS_PARA_REFRESH * 1000});
</script>
""", height=0)

# MÉTODO 3: STREAMLIT RERUN
if 'ultimo_refresh' not in st.session_state:
    st.session_state.ultimo_refresh = datetime.now()
if 'contador_refresh' not in st.session_state:
    st.session_state.contador_refresh = 0

tempo_passado = (datetime.now() - st.session_state.ultimo_refresh).seconds
if tempo_passado >= SEGUNDOS_PARA_REFRESH:
    st.session_state.ultimo_refresh = datetime.now()
    st.session_state.contador_refresh += 1
    st.cache_data.clear()
    st.rerun()

# ============================================================================
# CONSULTAR API
# ============================================================================
with st.spinner("📡 Buscando dados..."):
    resultado = consultar_api_pedidos()

if resultado["sucesso"] and resultado["dados"]:
    df = pd.DataFrame(resultado["dados"])
    
    # Status da API
    st.sidebar.success(f"✅ API Online - {resultado['registros']} registros")
    st.sidebar.info(f"🔄 Refresh: {st.session_state.contador_refresh}")
    
    # Processar dados (igual versão original)
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
    
    # Filtrar abertos
    df_abertos = df_renamed[df_renamed['TIPO_PEDIDO'] == 'ABERTOS'].copy()
    
    # ============================================================================
    # MÉTRICAS PRINCIPAIS (igual versão original)
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
            <div class="metric-label">🔄 Status Diferentes</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ============================================================================
    # GRÁFICOS (TODOS OS QUE TINHA NAS PRIMEIRAS VERSÕES)
    # ============================================================================
    if len(df_abertos) > 0:
        # GRÁFICO 1: Pedidos por Tipo de Limite (barras empilhadas)
        st.markdown('<p class="section-header">📦 PEDIDOS POR TIPO DE LIMITE</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            pivot_count = pd.crosstab(
                df_abertos['TIPO_LIMITE'],
                df_abertos['TIPO_ITEM'],
                values=df_abertos['COUNT_ENTREGA'],
                aggfunc='sum'
            ).fillna(0)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            cores = sns.color_palette("husl", len(pivot_count.columns))
            pivot_count.plot(kind='bar', stacked=True, ax=ax, color=cores)
            ax.set_title('Quantidade de Pedidos', fontsize=14, fontweight='bold')
            ax.set_xlabel('Tipo de Limite', fontsize=12)
            ax.set_ylabel('Quantidade de Pedidos', fontsize=12)
            ax.legend(title='Tipo Item', bbox_to_anchor=(1.05, 1))
            ax.grid(True, alpha=0.3, axis='y')
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            
            st.info(f"📊 Total de pedidos: **{pivot_count.sum().sum():,.0f}**")
        
        with col2:
            pivot_pecas = pd.crosstab(
                df_abertos['TIPO_LIMITE'],
                df_abertos['TIPO_ITEM'],
                values=df_abertos['QT_PECAS'],
                aggfunc='sum'
            ).fillna(0)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            pivot_pecas.plot(kind='bar', stacked=True, ax=ax, color=cores)
            ax.set_title('Quantidade de Peças', fontsize=14, fontweight='bold')
            ax.set_xlabel('Tipo de Limite', fontsize=12)
            ax.set_ylabel('Quantidade de Peças', fontsize=12)
            ax.legend(title='Tipo Item', bbox_to_anchor=(1.05, 1))
            ax.grid(True, alpha=0.3, axis='y')
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            
            st.info(f"📦 Total de peças: **{pivot_pecas.sum().sum():,.0f}**")
        
        st.markdown("---")
        
        # GRÁFICO 2: Análise por Status
        st.markdown('<p class="section-header">🏆 ANÁLISE POR STATUS</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            status_count = df_abertos['STATUS'].value_counts().head(10)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(range(len(status_count)), status_count.values, color='#4ECDC4')
            ax.set_yticks(range(len(status_count)))
            ax.set_yticklabels(status_count.index)
            ax.set_xlabel('Quantidade de Pedidos', fontsize=12)
            ax.set_title('Top 10 Status mais frequentes', fontsize=14, fontweight='bold')
            
            for i, (bar, val) in enumerate(zip(bars, status_count.values)):
                ax.text(val, i, f' {val}', va='center', fontweight='bold')
            
            plt.tight_layout()
            st.pyplot(fig)
        
        with col2:
            # Média de peças por status
            status_media = df_abertos.groupby('STATUS')['QT_PECAS'].mean().sort_values(ascending=False).head(10)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(range(len(status_media)), status_media.values, color='#FF6B6B')
            ax.set_yticks(range(len(status_media)))
            ax.set_yticklabels(status_media.index)
            ax.set_xlabel('Média de Peças', fontsize=12)
            ax.set_title('Top 10 - Média de Peças por Status', fontsize=14, fontweight='bold')
            
            for i, (bar, val) in enumerate(zip(bars, status_media.values)):
                ax.text(val, i, f' {val:.1f}', va='center', fontweight='bold')
            
            plt.tight_layout()
            st.pyplot(fig)
        
        st.markdown("---")
        
        # GRÁFICO 3: Distribuição por Tipo Item (pizza)
        st.markdown('<p class="section-header">🥧 DISTRIBUIÇÃO POR TIPO ITEM</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            item_count = df_abertos['TIPO_ITEM'].value_counts()
            
            fig, ax = plt.subplots(figsize=(10, 8))
            cores_pie = sns.color_palette("Set3", len(item_count))
            wedges, texts, autotexts = ax.pie(
                item_count.values, 
                labels=item_count.index, 
                autopct='%1.1f%%',
                colors=cores_pie,
                startangle=90,
                textprops={'fontsize': 14, 'fontweight': 'bold'}
            )
            ax.set_title('Proporção de Pedidos por Tipo Item', fontsize=14, fontweight='bold', pad=20)
            plt.tight_layout()
            st.pyplot(fig)
        
        with col2:
            item_pecas = df_abertos.groupby('TIPO_ITEM')['QT_PECAS'].sum()
            
            fig, ax = plt.subplots(figsize=(10, 8))
            wedges, texts, autotexts = ax.pie(
                item_pecas.values, 
                labels=item_pecas.index, 
                autopct='%1.1f%%',
                colors=cores_pie,
                startangle=90,
                textprops={'fontsize': 14, 'fontweight': 'bold'}
            )
            ax.set_title('Proporção de Peças por Tipo Item', fontsize=14, fontweight='bold', pad=20)
            plt.tight_layout()
            st.pyplot(fig)
        
        st.markdown("---")
        
        # GRÁFICO 4: Análise por Tipo Limite
        st.markdown('<p class="section-header">📊 ANÁLISE POR TIPO LIMITE</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            limite_count = df_abertos['TIPO_LIMITE'].value_counts()
            
            fig, ax = plt.subplots(figsize=(10, 6))
            limite_count.plot(kind='bar', ax=ax, color='#45B7D1')
            ax.set_title('Pedidos por Tipo Limite', fontsize=14, fontweight='bold')
            ax.set_xlabel('Tipo Limite', fontsize=12)
            ax.set_ylabel('Quantidade', fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')
            plt.xticks(rotation=45)
            
            for i, v in enumerate(limite_count.values):
                ax.text(i, v + 5, str(v), ha='center', fontweight='bold')
            
            plt.tight_layout()
            st.pyplot(fig)
        
        with col2:
            limite_pecas = df_abertos.groupby('TIPO_LIMITE')['QT_PECAS'].sum()
            
            fig, ax = plt.subplots(figsize=(10, 6))
            limite_pecas.plot(kind='bar', ax=ax, color='#FF6B6B')
            ax.set_title('Peças por Tipo Limite', fontsize=14, fontweight='bold')
            ax.set_xlabel('Tipo Limite', fontsize=12)
            ax.set_ylabel('Quantidade', fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')
            plt.xticks(rotation=45)
            
            for i, v in enumerate(limite_pecas.values):
                ax.text(i, v + 50, str(v), ha='center', fontweight='bold')
            
            plt.tight_layout()
            st.pyplot(fig)
        
        # ============================================================================
        # TABELA DE DADOS (com filtros)
        # ============================================================================
        st.markdown("---")
        st.markdown('<p class="section-header">📋 DADOS DETALHADOS</p>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tipos_limite = ['Todos'] + sorted(df_abertos['TIPO_LIMITE'].unique().tolist())
            filtro_limite = st.selectbox("📌 Tipo Limite", tipos_limite)
        
        with col2:
            tipos_item = ['Todos'] + sorted(df_abertos['TIPO_ITEM'].unique().tolist())
            filtro_item = st.selectbox("📦 Tipo Item", tipos_item)
        
        with col3:
            status_opcoes = ['Todos'] + sorted(df_abertos['STATUS'].unique().tolist())
            filtro_status = st.selectbox("🔄 Status", status_opcoes)
        
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
            mime="text/csv",
            use_container_width=True
        )
        
        # Estatísticas da tabela
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Registros", len(df_filtrado))
        with col2:
            st.metric("🧩 Total Peças", df_filtrado['QT_PECAS'].sum())
        with col3:
            st.metric("📈 Média Peças", f"{df_filtrado['QT_PECAS'].mean():.1f}")
    
    else:
        st.warning("⚠️ Nenhum pedido aberto encontrado")
    
else:
    st.error("❌ Erro ao conectar com a API")

# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"🕒 Última: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
with col2:
    st.markdown(f"⏱️ Refresh: a cada {MINUTOS_PARA_REFRESH} minuto(s)")
with col3:
    st.markdown(f"🔄 Ciclo: {st.session_state.contador_refresh}")