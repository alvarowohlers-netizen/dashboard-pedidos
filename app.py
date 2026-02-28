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

# ============================================================================
# META REFRESH - 30 MINUTOS (1800 SEGUNDOS)
# ============================================================================
st.markdown("""
<meta http-equiv="refresh" content="1800">
<style>
    /* CSS DAS PRIMEIRAS VERSÕES */
    @keyframes marquee {
        0% { transform: translateX(100%); }
        50% { transform: translateX(0%); }
        100% { transform: translateX(-100%); }
    }
    
    .marquee-header {
        font-size: 2.5rem;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
        overflow: hidden;
        white-space: nowrap;
        position: relative;
    }
    
    .marquee-header span {
        display: inline-block;
        animation: marquee 20s linear infinite;
        padding-left: 100%;
    }
    
    .marquee-header span:after {
        content: " 📊 DASHBOARD DE PEDIDOS ABERTOS - TV 📊 ";
        margin-left: 50px;
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
        font-weight: bold;
        font-size: 1.3rem;
    }
    .grafico-label {
        font-size: 1.1rem;
        color: #666;
        margin-left: 10px;
        font-weight: bold;
    }
    .refresh-box {
        background: #e8f4fd;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-size: 1.3rem;
        margin: 20px 0;
        border: 2px solid #4ECDC4;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# TÍTULO EM FORMATO DE LETREIRO (MARQUEE) - MAIS LENTO E COM DUPLICAÇÃO
# ============================================================================
st.markdown("""
<div class="marquee-header">
    <span>📊 DASHBOARD DE PEDIDOS ABERTOS - TV 📊 &nbsp;&nbsp;&nbsp; 📊 DASHBOARD DE PEDIDOS ABERTOS - TV 📊 &nbsp;&nbsp;&nbsp; </span>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# CONTROLE DE ATUALIZAÇÃO
# ============================================================================
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0
st.session_state.refresh_count += 1

st.markdown(f"""
<div class="refresh-box">
    🔄 AUTO-REFRESH ATIVO | Atualização #{st.session_state.refresh_count} | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
</div>
""", unsafe_allow_html=True)

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
@st.cache_data(ttl=30)
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
    
    # ============================================================================
    # FILTRO PARA EXCLUIR CANAIS TRF E DIST
    # ============================================================================
    if 'CANAL' in df_renamed.columns:
        canais_excluir = ['TRF', 'DIST']
        df_renamed = df_renamed[~df_renamed['CANAL'].isin(canais_excluir)]
        st.sidebar.success(f"✅ Filtro aplicado: canais TRF e DIST removidos")
    
    df_renamed['TIPO_PEDIDO'] = df_renamed['STATUS'].map(CLASSIFICACAO_STATUS)
    df_renamed['TIPO_PEDIDO'] = df_renamed['TIPO_PEDIDO'].fillna('OUTROS')
    
    # Filtrar apenas ABERTOS
    df_abertos = df_renamed[df_renamed['TIPO_PEDIDO'] == 'ABERTOS'].copy()
    
    # ============================================================================
    # MÉTRICAS PRINCIPAIS (CARDS BONITOS)
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
    # GRÁFICOS - TODOS COM NOMES CLAROS (1.A, 1.B, 2.A, 2.B, ETC)
    # ============================================================================
    if len(df_abertos) > 0:
        
        # ============================================================================
        # GRÁFICO 1.A - PEDIDOS POR TIPO DE LIMITE (BARRAS EMPILHADAS)
        # ============================================================================
        st.markdown('<p class="section-header">📊 GRÁFICO 1.A - PEDIDOS POR TIPO DE LIMITE (BARRAS EMPILHADAS)</p>', unsafe_allow_html=True)
        
        # Tabela pivot para contagem de pedidos
        pivot_count = pd.crosstab(
            df_abertos['TIPO_LIMITE'],
            df_abertos['TIPO_ITEM'],
            values=df_abertos['COUNT_ENTREGA'],
            aggfunc='sum'
        ).fillna(0)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        cores = sns.color_palette("husl", len(pivot_count.columns))
        bars = pivot_count.plot(kind='bar', stacked=True, ax=ax, color=cores)
        
        # Adicionar rótulos de dados corrigido (total por barra)
        for c in ax.containers:
            ax.bar_label(c, label_type='center', fontsize=9, fontweight='bold', color='white')
        
        ax.set_title('Quantidade de Pedidos por Tipo', fontsize=14, fontweight='bold')
        ax.set_xlabel('Tipo de Limite', fontsize=12)
        ax.set_ylabel('Quantidade de Pedidos', fontsize=12)
        ax.legend(title='Tipo Item', bbox_to_anchor=(1.05, 1))
        ax.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        
        # ============================================================================
        # GRÁFICO 1.B - PEÇAS POR TIPO DE LIMITE (BARRAS EMPILHADAS + LINHA DE MÉDIA)
        # ============================================================================
        st.markdown('<p class="section-header">📊 GRÁFICO 1.B - PEÇAS POR TIPO DE LIMITE (COM LINHA DE MÉDIA PEÇAS/PEDIDO)</p>', unsafe_allow_html=True)
        
        # Tabela pivot para quantidade de peças
        pivot_pecas = pd.crosstab(
            df_abertos['TIPO_LIMITE'],
            df_abertos['TIPO_ITEM'],
            values=df_abertos['QT_PECAS'],
            aggfunc='sum'
        ).fillna(0)
        
        # Calcular total de pedidos por tipo_limite para média
        total_pedidos_por_limite = df_abertos.groupby('TIPO_LIMITE')['COUNT_ENTREGA'].sum()
        total_pecas_por_limite = pivot_pecas.sum(axis=1)
        media_pecas_por_pedido = (total_pecas_por_limite / total_pedidos_por_limite).fillna(0)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        cores = sns.color_palette("husl", len(pivot_pecas.columns))
        bars = pivot_pecas.plot(kind='bar', stacked=True, ax=ax, color=cores)
        
        # Adicionar rótulos de dados nas barras de peças
        for c in ax.containers:
            ax.bar_label(c, label_type='center', fontsize=9, fontweight='bold', color='white')
        
        # Criar eixo secundário para a linha de média
        ax2 = ax.twinx()
        ax2.plot(range(len(media_pecas_por_pedido)), media_pecas_por_pedido.values, 
                color='red', marker='o', linewidth=3, markersize=8, label='Média Peças/Pedido')
        ax2.set_ylabel('Média de Peças por Pedido', fontsize=12, color='red')
        ax2.tick_params(axis='y', labelcolor='red')
        ax2.set_ylim(0, media_pecas_por_pedido.max() * 1.2)
        
        # Adicionar valores na linha de média
        for i, (idx, valor) in enumerate(media_pecas_por_pedido.items()):
            ax2.text(i, valor + 0.5, f'{valor:.1f}', ha='center', va='bottom', 
                    fontweight='bold', color='red', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
        
        ax.set_title('Quantidade de Peças por Tipo com Média Peças/Pedido', fontsize=14, fontweight='bold')
        ax.set_xlabel('Tipo de Limite', fontsize=12)
        ax.set_ylabel('Quantidade de Peças', fontsize=12)
        ax.legend(title='Tipo Item', bbox_to_anchor=(1.05, 0.8))
        ax.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        
        st.markdown("---")
        
        # ============================================================================
        # GRÁFICO 2.A - TOP 10 STATUS (MAIS FREQUENTES)
        # ============================================================================
        st.markdown('<p class="section-header">🏆 GRÁFICO 2.A - TOP 10 STATUS (MAIS FREQUENTES)</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            status_count = df_abertos['STATUS'].value_counts().head(10)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(range(len(status_count)), status_count.values, color='#4ECDC4')
            ax.set_yticks(range(len(status_count)))
            ax.set_yticklabels(status_count.index)
            ax.set_xlabel('Quantidade de Pedidos', fontsize=12)
            ax.set_title('Top 10 Status mais frequentes', fontsize=14, fontweight='bold')
            
            # Adicionar valores nas barras
            for i, (bar, val) in enumerate(zip(bars, status_count.values)):
                ax.text(val, i, f' {val}', va='center', fontweight='bold')
            
            plt.tight_layout()
            st.pyplot(fig)
        
        # ============================================================================
        # GRÁFICO 2.B - TOP 10 MÉDIA DE PEÇAS POR STATUS
        # ============================================================================
        st.markdown('<p class="section-header">🏆 GRÁFICO 2.B - TOP 10 MÉDIA DE PEÇAS POR STATUS</p>', unsafe_allow_html=True)
        
        with col2:
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
        
        # ============================================================================
        # GRÁFICO 3.A - DISTRIBUIÇÃO DE PEDIDOS POR TIPO ITEM (PIZZA)
        # ============================================================================
        st.markdown('<p class="section-header">🥧 GRÁFICO 3.A - DISTRIBUIÇÃO DE PEDIDOS POR TIPO ITEM</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            item_count = df_abertos['TIPO_ITEM'].value_counts()
            
            fig, ax = plt.subplots(figsize=(8, 8))
            cores_pie = sns.color_palette("Set3", len(item_count))
            wedges, texts, autotexts = ax.pie(
                item_count.values, 
                labels=item_count.index, 
                autopct='%1.1f%%',
                colors=cores_pie,
                startangle=90,
                textprops={'fontsize': 12, 'fontweight': 'bold'}
            )
            ax.set_title('Proporção de Pedidos por Tipo Item', fontsize=14, fontweight='bold', pad=20)
            plt.tight_layout()
            st.pyplot(fig)
        
        # ============================================================================
        # GRÁFICO 3.B - DISTRIBUIÇÃO DE PEÇAS POR TIPO ITEM (PIZZA)
        # ============================================================================
        st.markdown('<p class="section-header">🥧 GRÁFICO 3.B - DISTRIBUIÇÃO DE PEÇAS POR TIPO ITEM</p>', unsafe_allow_html=True)
        
        with col2:
            item_pecas = df_abertos.groupby('TIPO_ITEM')['QT_PECAS'].sum()
            
            fig, ax = plt.subplots(figsize=(8, 8))
            wedges, texts, autotexts = ax.pie(
                item_pecas.values, 
                labels=item_pecas.index, 
                autopct='%1.1f%%',
                colors=cores_pie,
                startangle=90,
                textprops={'fontsize': 12, 'fontweight': 'bold'}
            )
            ax.set_title('Proporção de Peças por Tipo Item', fontsize=14, fontweight='bold', pad=20)
            plt.tight_layout()
            st.pyplot(fig)
        
        st.markdown("---")
        
        # ============================================================================
        # GRÁFICO 4.A - PEDIDOS POR TIPO LIMITE (BARRAS SIMPLES)
        # ============================================================================
        st.markdown('<p class="section-header">📊 GRÁFICO 4.A - PEDIDOS POR TIPO LIMITE</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            limite_count = df_abertos['TIPO_LIMITE'].value_counts()
            
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(range(len(limite_count)), limite_count.values, color='#45B7D1')
            ax.set_xticks(range(len(limite_count)))
            ax.set_xticklabels(limite_count.index)
            ax.set_title('Pedidos por Tipo Limite', fontsize=14, fontweight='bold')
            ax.set_xlabel('Tipo Limite', fontsize=12)
            ax.set_ylabel('Quantidade', fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')
            plt.xticks(rotation=45)
            
            # Adicionar valores nas barras
            for i, (bar, v) in enumerate(zip(bars, limite_count.values)):
                ax.text(i, v + 5, str(v), ha='center', fontweight='bold', fontsize=11)
            
            plt.tight_layout()
            st.pyplot(fig)
        
        # ============================================================================
        # GRÁFICO 4.B - PEÇAS POR TIPO LIMITE (BARRAS SIMPLES)
        # ============================================================================
        st.markdown('<p class="section-header">📊 GRÁFICO 4.B - PEÇAS POR TIPO LIMITE</p>', unsafe_allow_html=True)
        
        with col2:
            limite_pecas = df_abertos.groupby('TIPO_LIMITE')['QT_PECAS'].sum()
            
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(range(len(limite_pecas)), limite_pecas.values, color='#FF6B6B')
            ax.set_xticks(range(len(limite_pecas)))
            ax.set_xticklabels(limite_pecas.index)
            ax.set_title('Peças por Tipo Limite', fontsize=14, fontweight='bold')
            ax.set_xlabel('Tipo Limite', fontsize=12)
            ax.set_ylabel('Quantidade', fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')
            plt.xticks(rotation=45)
            
            # Adicionar valores nas barras
            for i, (bar, v) in enumerate(zip(bars, limite_pecas.values)):
                ax.text(i, v + 50, str(v), ha='center', fontweight='bold', fontsize=11)
            
            plt.tight_layout()
            st.pyplot(fig)
        
        st.markdown("---")
        
        # ============================================================================
        # TABELA COM FILTROS
        # ============================================================================
        st.markdown('<p class="section-header">📋 TABELA - DADOS DETALHADOS</p>', unsafe_allow_html=True)
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tipos_limite = ['Todos'] + sorted(df_abertos['TIPO_LIMITE'].unique().tolist())
            filtro_limite = st.selectbox("📌 Filtrar por Tipo Limite", tipos_limite)
        
        with col2:
            tipos_item = ['Todos'] + sorted(df_abertos['TIPO_ITEM'].unique().tolist())
            filtro_item = st.selectbox("📦 Filtrar por Tipo Item", tipos_item)
        
        with col3:
            status_opcoes = ['Todos'] + sorted(df_abertos['STATUS'].unique().tolist())
            filtro_status = st.selectbox("🔄 Filtrar por Status", status_opcoes)
        
        # Aplicar filtros
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
    st.markdown(f"⏱️ Refresh: 30 minutos")
with col3:
    st.markdown(f"🔄 Ciclo: {st.session_state.refresh_count}")