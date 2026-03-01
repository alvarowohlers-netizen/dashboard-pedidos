import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="📺 TV Dashboard - Pedidos e Faturamento",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# FUNÇÃO PARA OBTER HORÁRIO BRASILEIRO (UTC-3)
# ============================================================================
def horario_brasil():
    """
    Retorna o datetime atual no horário de São Paulo/Brasil (UTC-3)
    """
    fuso_sp = pytz.timezone('America/Sao_Paulo')
    utc_now = datetime.now(pytz.UTC)
    return utc_now.astimezone(fuso_sp)

# ============================================================================
# FUNÇÃO PARA OBTER A HORA ATUAL NO BRASIL
# ============================================================================
def hora_atual_brasil():
    """
    Retorna apenas a hora atual no horário de Brasília (0-23)
    """
    fuso_sp = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(pytz.UTC).astimezone(fuso_sp)
    return agora.hour

# ============================================================================
# FUNÇÃO PARA FORMATAR NÚMEROS NO PADRÃO BRASILEIRO
# ============================================================================
def formatar_br(valor):
    return f"{valor:,.0f}".replace(",", ".")

# ============================================================================
# META REFRESH - 30 MINUTOS (1800 SEGUNDOS)
# ============================================================================
st.markdown("""
<meta http-equiv="refresh" content="1800">
<style>
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
# TÍTULO EM FORMATO DE LETREIRO
# ============================================================================
st.markdown("""
<div class="marquee-header">
    <span>📊 DASHBOARD DE PEDIDOS E FATURAMENTO - TV 📊</span>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# CONTROLE DE ATUALIZAÇÃO COM HORÁRIO BRASILEIRO
# ============================================================================
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0
st.session_state.refresh_count += 1

hora_br = horario_brasil()

st.markdown(f"""
<div class="refresh-box">
    🔄 AUTO-REFRESH ATIVO | Atualização #{st.session_state.refresh_count} | {hora_br.strftime('%d/%m/%Y %H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# ============================================================================
# CLASSIFICAÇÃO DOS STATUS (para aba de Pedidos)
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
# FUNÇÃO PARA CONSULTAR API DE PEDIDOS (ZBIQ0104)
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
# FUNÇÃO PARA CONSULTAR API DE FATURAMENTO (ZBIQ0099)
# ============================================================================
def consultar_api_faturamento(canal=None):
    """
    Função para consultar a API de faturamento
    canal: None (todos), "TRF", "DIST"
    """
    api_url = "https://api-dw.bseller.com.br/webquery/execute/ZBIQ0099"
    token = "5A9D7B5EAC2E7478E05324F3A8C0D448"
    
    # Configurar parâmetros base
    payload_base = {
        "P_ID_CIA": "11277",
        "P_ID_FILIAL": "2", 
        "P_ID_UNINEG": None,
        "P_START_ROW": 1,
        "P_PAGE_SIZE": 1000
    }
    
    # Adicionar canal específico
    if canal in ["TRF", "DIST"]:
        payload_base["P_ID_CANAL"] = canal
    else:
        payload_base["P_ID_CANAL"] = None
    
    payload = {"parametros": payload_base}
    
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return {"sucesso": True, "dados": data, "registros": len(data), "canal": canal}
        return {"sucesso": False, "dados": None, "erro": f"Erro {response.status_code}", "canal": canal}
            
    except Exception as e:
        return {"sucesso": False, "dados": None, "erro": str(e), "canal": canal}

# ============================================================================
# FUNÇÃO PARA ORDENAR TIPO LIMITE
# ============================================================================
def ordenar_tipo_limite(tipos):
    ordem = {'Data Limite': 0, 'D+1': 1, 'D+2': 2, 'D+3': 3, 'D+4+': 4}
    return sorted(tipos, key=lambda x: ordem.get(x, 999))

# ============================================================================
# FUNÇÃO PARA PROCESSAR DADOS DE FATURAMENTO (CORRIGIDA)
# ============================================================================
def processar_dados_faturamento(df, nome):
    """
    Processa dados de faturamento e filtra pela hora atual de Brasília
    Versão corrigida com tratamento de erros
    """
    if df is None or len(df) == 0:
        st.warning(f"⚠️ {nome}: DataFrame vazio")
        return None
    
    try:
        # Garantir colunas numéricas
        colunas_numericas = ['FATURADOS', 'EXPEDIDOS', 'INCLUIDOS', 'APROVADOS']
        for coluna in colunas_numericas:
            if coluna in df.columns:
                df[coluna] = pd.to_numeric(df[coluna], errors='coerce').fillna(0)
        
        # Verificar se PERIODO existe
        if 'PERIODO' not in df.columns:
            st.error(f"❌ {nome}: Coluna PERIODO não encontrada")
            return None
        
        # Extrair HORA do PERIODO (formato "HH:00") - VERSÃO CORRIGIDA
        df['HORA_STR'] = df['PERIODO'].astype(str).str.extract(r'(\d{2})')[0]
        df['HORA'] = pd.to_numeric(df['HORA_STR'], errors='coerce')
        
        # Remover linhas com hora inválida
        df = df.dropna(subset=['HORA'])
        df['HORA'] = df['HORA'].astype(int)
        
        if len(df) == 0:
            st.warning(f"⚠️ {nome}: Nenhuma hora válida encontrada")
            return None
        
        # OBTER HORA ATUAL DE BRASÍLIA
        hora_atual_br = hora_atual_brasil()
        
        # FILTRO: Manter apenas horas até a hora atual de Brasília
        df_filtrado = df[df['HORA'] <= hora_atual_br].copy()
        
        st.sidebar.write(f"🔍 {nome}: Horas disponíveis: {sorted(df['HORA'].unique())}")
        st.sidebar.write(f"🔍 {nome}: Hora atual Brasília: {hora_atual_br}")
        st.sidebar.write(f"🔍 {nome}: Registros após filtro: {len(df_filtrado)}")
        
        return df_filtrado.sort_values('HORA')
        
    except Exception as e:
        st.error(f"❌ Erro processando {nome}: {str(e)}")
        return None

# ============================================================================
# CRIAÇÃO DAS ABAS
# ============================================================================
tab1, tab2 = st.tabs(["📦 PEDIDOS ABERTOS", "💰 FATURAMENTO"])

# ============================================================================
# ABA 1: PEDIDOS ABERTOS
# ============================================================================
with tab1:
    # Consultar API de pedidos
    with st.spinner("📡 Buscando dados de pedidos..."):
        resultado_pedidos = consultar_api_pedidos()

    if resultado_pedidos["sucesso"] and resultado_pedidos["dados"]:
        df = pd.DataFrame(resultado_pedidos["dados"])
        
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
        
        # Filtrar canais
        if 'CANAL' in df_renamed.columns:
            canais_excluir = ['TRF', 'DIST']
            df_renamed = df_renamed[~df_renamed['CANAL'].isin(canais_excluir)]
        
        df_renamed['TIPO_PEDIDO'] = df_renamed['STATUS'].map(CLASSIFICACAO_STATUS)
        df_renamed['TIPO_PEDIDO'] = df_renamed['TIPO_PEDIDO'].fillna('OUTROS')
        
        # Filtrar apenas ABERTOS
        df_abertos = df_renamed[df_renamed['TIPO_PEDIDO'] == 'ABERTOS'].copy()
        
        # Métricas
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(df_abertos):,}</div>
                <div class="metric-label">📦 Pedidos Abertos</div>
            </div>
            """.replace(",", "."), unsafe_allow_html=True)
        
        with col2:
            total_pecas = df_abertos['QT_PECAS'].sum()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{total_pecas:,.0f}</div>
                <div class="metric-label">🧩 Total de Peças</div>
            </div>
            """.replace(",", "."), unsafe_allow_html=True)
        
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
                <div class="metric-value">{df_abertos['STATUS'].nunique():,}</div>
                <div class="metric-label">🔄 Status Diferentes</div>
            </div>
            """.replace(",", "."), unsafe_allow_html=True)
        
        st.markdown("---")
        
        if len(df_abertos) > 0:
            
            # GRÁFICO 1.A - PEDIDOS POR TIPO DE LIMITE
            st.markdown('<p class="section-header">📊 GRÁFICO 1.A - PEDIDOS POR TIPO DE LIMITE (BARRAS EMPILHADAS)</p>', unsafe_allow_html=True)
            
            # Preparar dados com ordenação correta
            df_abertos['TIPO_LIMITE'] = pd.Categorical(
                df_abertos['TIPO_LIMITE'], 
                categories=ordenar_tipo_limite(df_abertos['TIPO_LIMITE'].unique()),
                ordered=True
            )
            
            # Tabela pivot para contagem de pedidos
            pivot_count = pd.crosstab(
                df_abertos['TIPO_LIMITE'],
                df_abertos['TIPO_ITEM']
            ).fillna(0).reset_index()
            
            # Criar gráfico interativo
            fig = go.Figure()
            
            for item in pivot_count.columns[1:]:
                fig.add_trace(go.Bar(
                    name=item,
                    x=pivot_count['TIPO_LIMITE'],
                    y=pivot_count[item],
                    text=[formatar_br(v) for v in pivot_count[item]],
                    textposition='inside',
                    textfont=dict(color='white', size=12, family='Arial Black'),
                    hovertemplate='<b>%{x}</b><br>' +
                                  f'{item}: %{{y:,.0f}} pedidos'.replace(",", ".") +
                                  '<extra></extra>'
                ))
            
            fig.update_layout(
                title='Quantidade de Pedidos por Tipo',
                xaxis_title='Tipo de Limite',
                yaxis_title='Quantidade de Pedidos',
                barmode='stack',
                hovermode='x unified',
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=1.05
                ),
                height=500,
                template='plotly_white'
            )
            
            fig.update_yaxes(tickformat=",.0f")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # GRÁFICO 1.B - PEÇAS POR TIPO DE LIMITE
            st.markdown('<p class="section-header">📊 GRÁFICO 1.B - PEÇAS POR TIPO DE LIMITE (COM LINHA DE MÉDIA PEÇAS/PEDIDO)</p>', unsafe_allow_html=True)
            
            # Tabela pivot para quantidade de peças
            pivot_pecas = pd.crosstab(
                df_abertos['TIPO_LIMITE'],
                df_abertos['TIPO_ITEM'],
                values=df_abertos['QT_PECAS'],
                aggfunc='sum'
            ).fillna(0).reset_index()
            
            # Calcular totais de pedidos e peças por tipo_limite
            totais_pedidos_limite = df_abertos.groupby('TIPO_LIMITE').size()
            totais_pecas_limite = df_abertos.groupby('TIPO_LIMITE')['QT_PECAS'].sum()
            
            # Calcular média de peças por pedido
            medias = []
            for tipo in pivot_pecas['TIPO_LIMITE']:
                if tipo in totais_pedidos_limite.index and totais_pedidos_limite[tipo] > 0:
                    media = totais_pecas_limite[tipo] / totais_pedidos_limite[tipo]
                    medias.append(round(media, 1))
                else:
                    medias.append(0)
            
            # Criar figura com dois eixos y
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Adicionar barras empilhadas
            for item in pivot_pecas.columns[1:]:
                fig.add_trace(
                    go.Bar(
                        name=item,
                        x=pivot_pecas['TIPO_LIMITE'],
                        y=pivot_pecas[item],
                        text=[formatar_br(v) for v in pivot_pecas[item]],
                        textposition='inside',
                        textfont=dict(color='white', size=11, family='Arial Black'),
                        hovertemplate='<b>%{x}</b><br>' +
                                      f'{item}: %{{y:,.0f}} peças'.replace(",", ".") +
                                      '<extra></extra>'
                    ),
                    secondary_y=False
                )
            
            # Adicionar linha de média
            fig.add_trace(
                go.Scatter(
                    name='Média Peças/Pedido',
                    x=pivot_pecas['TIPO_LIMITE'],
                    y=medias,
                    mode='lines+markers+text',
                    line=dict(color='red', width=4),
                    marker=dict(size=12, color='red'),
                    text=[f'{m:.1f}'.replace('.', ',') for m in medias],
                    textposition='top center',
                    textfont=dict(color='red', size=12, family='Arial Black'),
                    hovertemplate='<b>%{x}</b><br>' +
                                  'Média: %{y:.1f} peças/pedido'.replace('.', ',') +
                                  '<extra></extra>'
                ),
                secondary_y=True
            )
            
            # Configurar layout
            fig.update_layout(
                title='Quantidade de Peças por Tipo com Média Peças/Pedido',
                hovermode='x unified',
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=1.05
                ),
                height=500,
                template='plotly_white'
            )
            
            fig.update_xaxes(title_text='Tipo de Limite')
            fig.update_yaxes(title_text='Quantidade de Peças', tickformat=",.0f", secondary_y=False)
            fig.update_yaxes(title_text='Média de Peças por Pedido', secondary_y=True, 
                            range=[0, max(medias) * 1.3 if medias and max(medias) > 0 else 1])
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # GRÁFICO 2.A - TOP 10 STATUS
            st.markdown('<p class="section-header">🏆 GRÁFICO 2.A - TOP 10 STATUS (MAIS FREQUENTES)</p>', unsafe_allow_html=True)
            
            status_count = df_abertos['STATUS'].value_counts().head(10).reset_index()
            status_count.columns = ['STATUS', 'QUANTIDADE']
            
            fig = px.bar(
                status_count,
                y='STATUS',
                x='QUANTIDADE',
                orientation='h',
                title='Top 10 Status mais frequentes',
                labels={'QUANTIDADE': 'Quantidade de Pedidos', 'STATUS': 'Status'},
                text=status_count['QUANTIDADE'].apply(formatar_br),
                color_discrete_sequence=['#4ECDC4']
            )
            
            fig.update_traces(
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Pedidos: %{x:,.0f}'.replace(",", ".")
            )
            
            fig.update_layout(height=400, template='plotly_white')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # GRÁFICO 2.B - TOP 10 MÉDIA DE PEÇAS POR STATUS
            st.markdown('<p class="section-header">🏆 GRÁFICO 2.B - TOP 10 MÉDIA DE PEÇAS POR STATUS</p>', unsafe_allow_html=True)
            
            status_media = df_abertos.groupby('STATUS')['QT_PECAS'].mean().sort_values(ascending=False).head(10).reset_index()
            status_media.columns = ['STATUS', 'MEDIA']
            
            fig = px.bar(
                status_media,
                y='STATUS',
                x='MEDIA',
                orientation='h',
                title='Top 10 - Média de Peças por Status',
                labels={'MEDIA': 'Média de Peças', 'STATUS': 'Status'},
                text=status_media['MEDIA'].apply(lambda x: f'{x:.1f}'.replace('.', ',')),
                color_discrete_sequence=['#FF6B6B']
            )
            
            fig.update_traces(
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Média: %{x:.1f} peças'.replace('.', ',')
            )
            
            fig.update_layout(height=400, template='plotly_white')
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # GRÁFICO 3.A e 3.B - Distribuição
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<p class="section-header">🥧 GRÁFICO 3.A - DISTRIBUIÇÃO DE PEDIDOS POR TIPO ITEM</p>', unsafe_allow_html=True)
                item_count = df_abertos['TIPO_ITEM'].value_counts().reset_index()
                item_count.columns = ['TIPO_ITEM', 'QUANTIDADE']
                
                fig = px.pie(
                    item_count,
                    values='QUANTIDADE',
                    names='TIPO_ITEM',
                    title='Proporção de Pedidos por Tipo Item',
                    hole=0.3,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>Pedidos: %{value:,.0f}'.replace(",", ".") + '<br>Percentual: %{percent}<extra></extra>'
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown('<p class="section-header">🥧 GRÁFICO 3.B - DISTRIBUIÇÃO DE PEÇAS POR TIPO ITEM</p>', unsafe_allow_html=True)
                item_pecas = df_abertos.groupby('TIPO_ITEM')['QT_PECAS'].sum().reset_index()
                item_pecas.columns = ['TIPO_ITEM', 'QUANTIDADE']
                
                fig = px.pie(
                    item_pecas,
                    values='QUANTIDADE',
                    names='TIPO_ITEM',
                    title='Proporção de Peças por Tipo Item',
                    hole=0.3,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>Peças: %{value:,.0f}'.replace(",", ".") + '<br>Percentual: %{percent}<extra></extra>'
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # GRÁFICO 4.A e 4.B - Por Tipo Limite
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<p class="section-header">📊 GRÁFICO 4.A - PEDIDOS POR TIPO LIMITE</p>', unsafe_allow_html=True)
                limite_count = df_abertos['TIPO_LIMITE'].value_counts().reindex(
                    ordenar_tipo_limite(df_abertos['TIPO_LIMITE'].unique())
                ).reset_index()
                limite_count.columns = ['TIPO_LIMITE', 'QUANTIDADE']
                
                fig = px.bar(
                    limite_count,
                    x='TIPO_LIMITE',
                    y='QUANTIDADE',
                    title='Pedidos por Tipo Limite',
                    labels={'QUANTIDADE': 'Quantidade', 'TIPO_LIMITE': 'Tipo Limite'},
                    text=limite_count['QUANTIDADE'].apply(formatar_br),
                    color_discrete_sequence=['#45B7D1']
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown('<p class="section-header">📊 GRÁFICO 4.B - PEÇAS POR TIPO LIMITE</p>', unsafe_allow_html=True)
                limite_pecas = df_abertos.groupby('TIPO_LIMITE')['QT_PECAS'].sum().reindex(
                    ordenar_tipo_limite(df_abertos['TIPO_LIMITE'].unique())
                ).reset_index()
                limite_pecas.columns = ['TIPO_LIMITE', 'QUANTIDADE']
                
                fig = px.bar(
                    limite_pecas,
                    x='TIPO_LIMITE',
                    y='QUANTIDADE',
                    title='Peças por Tipo Limite',
                    labels={'QUANTIDADE': 'Quantidade', 'TIPO_LIMITE': 'Tipo Limite'},
                    text=limite_pecas['QUANTIDADE'].apply(formatar_br),
                    color_discrete_sequence=['#FF6B6B']
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # TABELA
            st.markdown('<p class="section-header">📋 TABELA - DADOS DETALHADOS</p>', unsafe_allow_html=True)
            
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                tipos_limite = ['Todos'] + ordenar_tipo_limite(df_abertos['TIPO_LIMITE'].unique().tolist())
                filtro_limite = st.selectbox("📌 Filtrar por Tipo Limite", tipos_limite, key='filtro_limite_pedidos')
            with col2:
                tipos_item = ['Todos'] + sorted(df_abertos['TIPO_ITEM'].unique().tolist())
                filtro_item = st.selectbox("📦 Filtrar por Tipo Item", tipos_item, key='filtro_item_pedidos')
            with col3:
                status_opcoes = ['Todos'] + sorted(df_abertos['STATUS'].unique().tolist())
                filtro_status = st.selectbox("🔄 Filtrar por Status", status_opcoes, key='filtro_status_pedidos')
            
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
                file_name=f"pedidos_{hora_br.strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        else:
            st.warning("⚠️ Nenhum pedido aberto encontrado")
    
    else:
        st.error("❌ Erro ao conectar com a API de pedidos")

# ============================================================================
# ABA 2: FATURAMENTO (VERSÃO CORRIGIDA)
# ============================================================================
with tab2:
    st.markdown('<p class="section-header">💰 FATURAMENTO (COM FILTRO DE CANAIS)</p>', unsafe_allow_html=True)
    
    # OBTER HORA ATUAL DE BRASÍLIA
    hora_atual_br = hora_atual_brasil()
    
    st.success(f"🕒 HORA ATUAL DE BRASÍLIA: {hora_atual_br:02d}:00")
    
    with st.spinner("📡 Consultando APIs de faturamento..."):
        dados_todos = consultar_api_faturamento(None)
        dados_trf = consultar_api_faturamento("TRF")
        dados_dist = consultar_api_faturamento("DIST")
    
    dfs = {}
    
    # Processar cada canal
    for nome, resultado in [("TODOS", dados_todos), ("TRF", dados_trf), ("DIST", dados_dist)]:
        if resultado["sucesso"] and resultado["dados"]:
            df = pd.DataFrame(resultado["dados"])
            dfs[nome] = processar_dados_faturamento(df, nome)
        else:
            st.warning(f"⚠️ API {nome} não disponível")
    
    # Verificar se temos dados
    if dfs.get("TODOS") is not None and not dfs["TODOS"].empty:
        
        st.markdown("### 🔍 FILTROS")
        col1, col2 = st.columns(2)
        
        with col1:
            incluir_trf = st.checkbox("Incluir TRANSFERÊNCIA (TRF)", value=True)
        with col2:
            incluir_dist = st.checkbox("Incluir DISTRIBUIÇÃO (DIST)", value=True)
        
        # Preparar dados base
        df_base = dfs["TODOS"].copy()
        df_base = df_base.rename(columns={'FATURADOS': 'TODOS'})
        
        # Adicionar TRF se disponível e selecionado
        if incluir_trf and dfs.get("TRF") is not None and not dfs["TRF"].empty:
            df_trf = dfs["TRF"][['HORA', 'FATURADOS']].rename(columns={'FATURADOS': 'TRF'})
            df_base = df_base.merge(df_trf, on='HORA', how='left').fillna(0)
        else:
            df_base['TRF'] = 0
        
        # Adicionar DIST se disponível e selecionado
        if incluir_dist and dfs.get("DIST") is not None and not dfs["DIST"].empty:
            df_dist = dfs["DIST"][['HORA', 'FATURADOS']].rename(columns={'FATURADOS': 'DIST'})
            df_base = df_base.merge(df_dist, on='HORA', how='left').fillna(0)
        else:
            df_base['DIST'] = 0
        
        # Calcular vendas
        df_base['VENDA'] = df_base['TODOS'] - df_base['TRF'] - df_base['DIST']
        df_base['ACUMULADO'] = df_base['VENDA'].cumsum()
        
        # Métricas
        st.markdown("### 📊 MÉTRICAS")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 TOTAL GERAL", formatar_br(df_base['TODOS'].sum()))
        with col2:
            st.metric("🔄 TRANSFERÊNCIA", formatar_br(df_base['TRF'].sum()))
        with col3:
            st.metric("📦 DISTRIBUIÇÃO", formatar_br(df_base['DIST'].sum()))
        with col4:
            st.metric("💵 VENDA DO DIA", formatar_br(df_base['VENDA'].sum()))
        
        # Gráfico de barras
        st.markdown("### 📊 FATURAMENTO POR HORA")
        fig = go.Figure()
        
        fig.add_trace(go.Bar(name='TODOS', x=df_base['HORA'], y=df_base['TODOS'], 
                            marker_color='blue', text=df_base['TODOS'].apply(formatar_br)))
        
        if incluir_trf:
            fig.add_trace(go.Bar(name='TRF', x=df_base['HORA'], y=df_base['TRF'], 
                                marker_color='red', text=df_base['TRF'].apply(formatar_br)))
        
        if incluir_dist:
            fig.add_trace(go.Bar(name='DIST', x=df_base['HORA'], y=df_base['DIST'], 
                                marker_color='orange', text=df_base['DIST'].apply(formatar_br)))
        
        fig.add_trace(go.Bar(name='VENDA', x=df_base['HORA'], y=df_base['VENDA'], 
                            marker_color='green', text=df_base['VENDA'].apply(formatar_br)))
        
        fig.update_layout(barmode='group', height=500, template='plotly_white',
                         xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela
        st.markdown("### 📋 DADOS")
        df_display = df_base.copy()
        for col in ['TODOS', 'TRF', 'DIST', 'VENDA', 'ACUMULADO']:
            df_display[col] = df_display[col].apply(formatar_br)
        
        st.dataframe(df_display[['HORA', 'TODOS', 'TRF', 'DIST', 'VENDA', 'ACUMULADO']], 
                    use_container_width=True, height=400)
        
        st.info(f"📊 Período: 00:00 até {df_base['HORA'].max():02d}:00")
    
    else:
        st.error("❌ Não foi possível carregar dados de faturamento")

# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
hora_br_rodape = horario_brasil()
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"🕒 Última: {hora_br_rodape.strftime('%d/%m/%Y %H:%M:%S')}")
with col2:
    st.markdown(f"⏱️ Refresh: 30 minutos")
with col3:
    st.markdown(f"🔄 Ciclo: {st.session_state.refresh_count}")