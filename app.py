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
from datetime import datetime, timedelta, timezone
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
    fuso_br = timezone(timedelta(hours=-3))
    return datetime.now(timezone.utc).astimezone(fuso_br)

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
    <span>📊 DASHBOARD DE PEDIDOS E FATURAMENTO - TV 📊 &nbsp;&nbsp;&nbsp; 📊 DASHBOARD DE PEDIDOS E FATURAMENTO - TV 📊 &nbsp;&nbsp;&nbsp; </span>
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
    canal: None (todos), "TRF", "DIST", ou "VENDA" (exclui TRF e DIST)
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
# FUNÇÃO PARA COMPLETAR DADOS DE FATURAMENTO ATÉ HORA ATUAL (CORRIGIDA)
# ============================================================================
def completar_dados_ate_hora_atual(df_existente, tipo, hora_atual):
    """
    Completa os dados até a hora atual se a API retornou dados incompletos
    NUNCA cria dados para horas futuras
    """
    if df_existente is None or len(df_existente) == 0:
        return None
        
    # Extrair hora máxima dos dados existentes
    if 'HORA' in df_existente.columns:
        hora_maxima_api = df_existente['HORA'].max()
    else:
        # Se não tem coluna HORA, tentar extrair do PERIODO
        df_existente['HORA_EXTRAIDA'] = df_existente['PERIODO'].str.extract('(\d+)')
        df_existente['HORA'] = pd.to_numeric(df_existente['HORA_EXTRAIDA'], errors='coerce')
        df_existente = df_existente.dropna(subset=['HORA'])
        df_existente['HORA'] = df_existente['HORA'].astype(int)
        hora_maxima_api = df_existente['HORA'].max()
    
    # 🔥 CORREÇÃO: NÃO CRIAR DADOS PARA HORAS FUTURAS
    # Se a hora máxima da API já é maior ou igual à hora atual, só retornar até hora atual
    if hora_maxima_api >= hora_atual:
        df_existente = df_existente[df_existente['HORA'] <= hora_atual]
        return df_existente
    
    # Se a API retornou dados até uma hora anterior à atual
    # Retornar apenas os dados reais, sem completar
    return df_existente[df_existente['HORA'] <= hora_atual]

# ============================================================================
# CRIAÇÃO DAS ABAS
# ============================================================================
tab1, tab2 = st.tabs(["📦 PEDIDOS ABERTOS", "💰 FATURAMENTO"])

# ============================================================================
# ABA 1: PEDIDOS ABERTOS (CÓDIGO EXISTENTE)
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
# ABA 2: FATURAMENTO (COM FILTROS PARA TRF E DIST)
# ============================================================================
with tab2:
    st.markdown('<p class="section-header">💰 FATURAMENTO (COM FILTRO DE CANAIS)</p>', unsafe_allow_html=True)
    
    # Obter hora atual do sistema (LIMITAR A HORA ATUAL)
    hora_atual = datetime.now().hour
    
    with st.spinner("📡 Consultando APIs de faturamento..."):
        # Consultar APIs para cada canal
        dados_todos = consultar_api_faturamento(None)      # Todos os canais
        dados_trf = consultar_api_faturamento("TRF")       # Apenas TRF
        dados_dist = consultar_api_faturamento("DIST")     # Apenas DIST
    
    # Dicionário para armazenar DataFrames
    dfs = {}
    
    # Processar dados de cada canal
    for nome, resultado in [("TODOS", dados_todos), ("TRF", dados_trf), ("DIST", dados_dist)]:
        if resultado["sucesso"] and resultado["dados"]:
            df = pd.DataFrame(resultado["dados"])
            
            # Processar dados
            colunas_numericas = ['FATURADOS', 'EXPEDIDOS', 'INCLUIDOS', 'APROVADOS']
            for coluna in colunas_numericas:
                if coluna in df.columns:
                    df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
            
            # Garantir coluna HORA
            if 'HORA' not in df.columns:
                df['HORA_EXTRAIDA'] = df['PERIODO'].str.extract('(\d+)')
                df['HORA'] = pd.to_numeric(df['HORA_EXTRAIDA'], errors='coerce')
                df = df.dropna(subset=['HORA'])
                df['HORA'] = df['HORA'].astype(int)
            
            df = df.sort_values('HORA')
            
            # COMPLETAR E LIMITAR À HORA ATUAL (NÃO CRIA DADOS FUTUROS)
            df = completar_dados_ate_hora_atual(df, nome, hora_atual)
            dfs[nome] = df
        else:
            # Criar dados de exemplo apenas até hora atual
            st.info(f"⚠️ API {nome} não disponível - usando dados de exemplo até {hora_atual}:00")
            horas = [h for h in range(hora_atual + 1)]
            dados_exemplo = []
            for hora in horas:
                base = 1000 if nome == "TODOS" else (200 if nome == "TRF" else 150)
                dados_exemplo.append({
                    'FATURADOS': np.random.randint(base, base * 2),
                    'EXPEDIDOS': np.random.randint(base//3, base//2),
                    'INCLUIDOS': np.random.randint(base//2, base),
                    'APROVADOS': np.random.randint(base//2, base),
                    'PERIODO': f"{hora:02d}:00",
                    'HORA': hora
                })
            dfs[nome] = pd.DataFrame(dados_exemplo)
    
    # Verificar se temos dados para processar
    if dfs.get("TODOS") is not None and dfs.get("TRF") is not None and dfs.get("DIST") is not None:
        
        # FILTROS INTERATIVOS
        st.markdown("### 🔍 FILTROS")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            incluir_trf = st.checkbox("Incluir TRANSFERÊNCIA (TRF)", value=True, key="incluir_trf")
        with col2:
            incluir_dist = st.checkbox("Incluir DISTRIBUIÇÃO (DIST)", value=True, key="incluir_dist")
        with col3:
            st.markdown("##### 💡 VENDA DO DIA = TODOS - (TRF + DIST)")
        
        st.markdown("---")
        
        # Obter horas comuns
        horas_comuns = sorted(set(dfs["TODOS"]['HORA']).intersection(
            set(dfs["TRF"]['HORA'])).intersection(set(dfs["DIST"]['HORA'])))
        
        if not horas_comuns:
            st.error("❌ Não há horas comuns entre os datasets")
        else:
            # Filtrar dados pelas horas comuns
            df_todos_filtrado = dfs["TODOS"][dfs["TODOS"]['HORA'].isin(horas_comuns)].copy()
            df_trf_filtrado = dfs["TRF"][dfs["TRF"]['HORA'].isin(horas_comuns)].copy()
            df_dist_filtrado = dfs["DIST"][dfs["DIST"]['HORA'].isin(horas_comuns)].copy()
            
            hora_final = max(horas_comuns)
            
            # Calcular totais com base nos filtros
            total_todos = df_todos_filtrado['FATURADOS'].sum()
            total_trf = df_trf_filtrado['FATURADOS'].sum() if incluir_trf else 0
            total_dist = df_dist_filtrado['FATURADOS'].sum() if incluir_dist else 0
            total_venda = total_todos - total_trf - total_dist
            
            # Criar DataFrame consolidado
            df_consolidado = pd.merge(
                df_todos_filtrado[['HORA', 'PERIODO', 'FATURADOS']].rename(columns={'FATURADOS': 'TODOS'}),
                df_trf_filtrado[['HORA', 'FATURADOS']].rename(columns={'FATURADOS': 'TRF'}),
                on='HORA',
                how='left'
            ).fillna(0)
            
            df_consolidado = pd.merge(
                df_consolidado,
                df_dist_filtrado[['HORA', 'FATURADOS']].rename(columns={'FATURADOS': 'DIST'}),
                on='HORA',
                how='left'
            ).fillna(0)
            
            # Calcular VENDA e LÍQUIDO
            df_consolidado['VENDA'] = df_consolidado['TODOS'] - df_consolidado['TRF'] - df_consolidado['DIST']
            
            # Aplicar filtros para o líquido
            trf_para_liquido = df_consolidado['TRF'] if incluir_trf else 0
            dist_para_liquido = df_consolidado['DIST'] if incluir_dist else 0
            df_consolidado['LIQUIDO'] = df_consolidado['TODOS'] - trf_para_liquido - dist_para_liquido
            
            df_consolidado['ACUMULADO'] = df_consolidado['LIQUIDO'].cumsum()
            
            # MÉTRICAS PRINCIPAIS
            st.markdown("### 📊 MÉTRICAS")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("💰 TOTAL GERAL", formatar_br(total_todos))
            with col2:
                st.metric("🔄 TRANSFERÊNCIA", formatar_br(total_trf) if incluir_trf else "0 (filtrado)")
            with col3:
                st.metric("📦 DISTRIBUIÇÃO", formatar_br(total_dist) if incluir_dist else "0 (filtrado)")
            with col4:
                cor_venda = "green" if total_venda >= 0 else "red"
                st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 10px; border-left: 5px solid {cor_venda};">
                    <div style="font-size: 2rem; font-weight: bold;">{formatar_br(total_venda)}</div>
                    <div>💵 VENDA DO DIA</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # GRÁFICO 1: COMPARATIVO POR HORA (COM TODOS OS CANAIS)
            st.markdown('<p class="section-header">📊 COMPARATIVO POR HORA - TODOS OS CANAIS</p>', unsafe_allow_html=True)
            
            fig = go.Figure()
            
            # Barras para cada canal
            fig.add_trace(go.Bar(
                name='TODOS',
                x=df_consolidado['HORA'],
                y=df_consolidado['TODOS'],
                marker_color='blue',
                text=[formatar_br(v) for v in df_consolidado['TODOS']],
                textposition='inside',
                hovertemplate='Hora: %{x}:00<br>TODOS: %{y:,.0f}'.replace(",", ".") + '<extra></extra>'
            ))
            
            if incluir_trf:
                fig.add_trace(go.Bar(
                    name='TRF',
                    x=df_consolidado['HORA'],
                    y=df_consolidado['TRF'],
                    marker_color='red',
                    text=[formatar_br(v) for v in df_consolidado['TRF']],
                    textposition='inside',
                    hovertemplate='Hora: %{x}:00<br>TRF: %{y:,.0f}'.replace(",", ".") + '<extra></extra>'
                ))
            
            if incluir_dist:
                fig.add_trace(go.Bar(
                    name='DIST',
                    x=df_consolidado['HORA'],
                    y=df_consolidado['DIST'],
                    marker_color='orange',
                    text=[formatar_br(v) for v in df_consolidado['DIST']],
                    textposition='inside',
                    hovertemplate='Hora: %{x}:00<br>DIST: %{y:,.0f}'.replace(",", ".") + '<extra></extra>'
                ))
            
            fig.add_trace(go.Bar(
                name='VENDA',
                x=df_consolidado['HORA'],
                y=df_consolidado['VENDA'],
                marker_color='green',
                text=[formatar_br(v) for v in df_consolidado['VENDA']],
                textposition='inside',
                hovertemplate='Hora: %{x}:00<br>VENDA: %{y:,.0f}'.replace(",", ".") + '<extra></extra>'
            ))
            
            fig.update_layout(
                title='Faturamento por Hora - Todos os Canais',
                xaxis_title='Hora do Dia',
                yaxis_title='Quantidade',
                barmode='group',
                height=500,
                template='plotly_white',
                xaxis = dict(
                    tickmode = 'linear',
                    tick0 = 0,
                    dtick = 1  # Mostrar TODAS as horas (1 em 1)
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # GRÁFICO 2: VENDA LÍQUIDA (com base nos filtros)
            st.markdown('<p class="section-header">📈 VENDA LÍQUIDA (com filtros aplicados)</p>', unsafe_allow_html=True)
            
            fig = go.Figure()
            
            cores = ['green' if x >= 0 else 'red' for x in df_consolidado['LIQUIDO']]
            
            fig.add_trace(go.Bar(
                x=df_consolidado['HORA'],
                y=df_consolidado['LIQUIDO'],
                marker_color=cores,
                text=[formatar_br(v) for v in df_consolidado['LIQUIDO']],
                textposition='outside',
                hovertemplate='Hora: %{x}:00<br>Líquido: %{y:,.0f}'.replace(",", ".") + '<extra></extra>'
            ))
            
            fig.update_layout(
                title='Venda Líquida por Hora',
                xaxis_title='Hora do Dia',
                yaxis_title='Quantidade',
                height=400,
                template='plotly_white',
                xaxis = dict(
                    tickmode = 'linear',
                    tick0 = 0,
                    dtick = 1  # Mostrar TODAS as horas
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # GRÁFICO 3: ACUMULADO
            st.markdown('<p class="section-header">📈 VENDA ACUMULADA</p>', unsafe_allow_html=True)
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_consolidado['HORA'],
                y=df_consolidado['ACUMULADO'],
                mode='lines+markers+text',
                line=dict(color='blue', width=4),
                marker=dict(size=10, color='red'),
                text=[formatar_br(v) for v in df_consolidado['ACUMULADO']],
                textposition='top center',
                hovertemplate='Hora: %{x}:00<br>Acumulado: %{y:,.0f}'.replace(",", ".") + '<extra></extra>'
            ))
            
            fig.update_layout(
                title='Venda Acumulada',
                xaxis_title='Hora do Dia',
                yaxis_title='Quantidade Acumulada',
                height=400,
                template='plotly_white',
                xaxis = dict(
                    tickmode = 'linear',
                    tick0 = 0,
                    dtick = 1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # TABELA DE DADOS
            st.markdown('<p class="section-header">📋 DADOS DE FATURAMENTO</p>', unsafe_allow_html=True)
            
            df_display = df_consolidado.copy()
            df_display['PERIODO'] = df_display['HORA'].apply(lambda x: f"{int(x):02d}:00")
            df_display['TODOS'] = df_display['TODOS'].apply(formatar_br)
            df_display['TRF'] = df_display['TRF'].apply(formatar_br)
            df_display['DIST'] = df_display['DIST'].apply(formatar_br)
            df_display['VENDA'] = df_display['VENDA'].apply(formatar_br)
            df_display['LÍQUIDO'] = df_display['LIQUIDO'].apply(formatar_br)
            df_display['ACUMULADO'] = df_display['ACUMULADO'].apply(formatar_br)
            
            st.dataframe(
                df_display[['PERIODO', 'TODOS', 'TRF', 'DIST', 'VENDA', 'LÍQUIDO', 'ACUMULADO']],
                use_container_width=True,
                height=400
            )
            
            # Download
            csv = df_consolidado.to_csv(index=False)
            st.download_button(
                label="📥 Download Dados de Faturamento",
                data=csv,
                file_name=f"faturamento_{hora_br.strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.markdown("---")
            st.info(f"📊 Período analisado: 00:00 até {hora_final:02d}:00 (apenas dados reais, sem previsões)")
            
    else:
        st.error("❌ Não foi possível processar dados de faturamento")

# ============================================================================
# RODAPÉ COM HORÁRIO BRASILEIRO
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