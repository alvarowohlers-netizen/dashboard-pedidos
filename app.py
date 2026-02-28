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

# CSS para TV
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        text-align: center;
        padding: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 8px solid #FF6B6B;
    }
    .metric-value {
        font-size: 3rem;
        font-weight: bold;
        color: #333;
    }
    .metric-label {
        font-size: 1.5rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">📺 TV DASHBOARD - PEDIDOS ABERTOS</h1>', unsafe_allow_html=True)

# ============================================================================
# CONFIGURAÇÃO DE TEMPO (AJUSTE AQUI!)
# ============================================================================
MINUTOS_PARA_REFRESH = 5  # ← Mude para 5, 10, 15, 30, 60 minutos
SEGUNDOS_PARA_REFRESH = MINUTOS_PARA_REFRESH * 60

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
@st.cache_data(ttl=60)
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
# MÚLTIPLOS MÉTODOS DE REFRESH
# ============================================================================

# MÉTODO 1: META REFRESH (mais confiável)
st.markdown(f"""
<meta http-equiv="refresh" content="{SEGUNDOS_PARA_REFRESH}">
""", unsafe_allow_html=True)

# MÉTODO 2: JAVASCRIPT COM RELOAD FORÇADO
st.components.v1.html(f"""
<script>
    // Método 1: setTimeout
    setTimeout(function() {{
        console.log('🔄 Refresh método 1');
        window.location.reload(true);
    }}, {SEGUNDOS_PARA_REFRESH * 1000});
    
    // Método 2: setInterval (backup)
    setInterval(function() {{
        console.log('🔄 Refresh método 2');
        window.location.reload(true);
    }}, {SEGUNDOS_PARA_REFRESH * 1000 + 1000});
    
    // Método 3: Forçar limpeza de cache
    if (!window.location.search.includes('_t=')) {{
        var url = window.location.href + 
                  (window.location.href.includes('?') ? '&' : '?') + 
                  '_t=' + new Date().getTime();
        window.location.replace(url);
    }}
    
    // Mostrar timer na tela (para debug)
    var timerDiv = document.createElement('div');
    timerDiv.style.cssText = 'position: fixed; bottom: 10px; right: 10px; background: #333; color: white; padding: 10px; border-radius: 5px; z-index: 9999; font-size: 16px;';
    timerDiv.id = 'tv-timer';
    document.body.appendChild(timerDiv);
    
    var seconds = {SEGUNDOS_PARA_REFRESH};
    setInterval(function() {{
        seconds--;
        if (seconds <= 0) seconds = {SEGUNDOS_PARA_REFRESH};
        var mins = Math.floor(seconds / 60);
        var secs = seconds % 60;
        document.getElementById('tv-timer').innerHTML = '🔄 Próximo refresh: ' + mins + 'min ' + secs + 's';
    }}, 1000);
</script>
""", height=0)

# MÉTODO 4: STREAMLIT RERUN
if 'ultimo_refresh' not in st.session_state:
    st.session_state.ultimo_refresh = datetime.now()

tempo_passado = (datetime.now() - st.session_state.ultimo_refresh).seconds
if tempo_passado >= SEGUNDOS_PARA_REFRESH:
    st.session_state.ultimo_refresh = datetime.now()
    st.cache_data.clear()
    st.rerun()

# ============================================================================
# CONSULTAR API E MOSTRAR DADOS
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
    df_renamed['TIPO_PEDIDO'] = df_renamed['STATUS'].map(CLASSIFICACAO_STATUS).fillna('OUTROS')
    df_abertos = df_renamed[df_renamed['TIPO_PEDIDO'] == 'ABERTOS'].copy()
    
    # MÉTRICAS GRANDES (para TV)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(df_abertos):,}</div>
            <div class="metric-label">📦 PEDIDOS ABERTOS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_pecas = df_abertos['QT_PECAS'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_pecas:,}</div>
            <div class="metric-label">🧩 TOTAL PEÇAS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        media = total_pecas / len(df_abertos) if len(df_abertos) > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{media:.1f}</div>
            <div class="metric-label">📊 MÉDIA PEÇAS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{SEGUNDOS_PARA_REFRESH // 60}</div>
            <div class="metric-label">⏱️ REFRESH (min)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # GRÁFICOS
    if len(df_abertos) > 0:
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            pivot = pd.crosstab(df_abertos['TIPO_LIMITE'], df_abertos['TIPO_ITEM'], 
                               values=df_abertos['COUNT_ENTREGA'], aggfunc='sum').fillna(0)
            fig, ax = plt.subplots(figsize=(12, 6))
            pivot.plot(kind='bar', stacked=True, ax=ax, 
                      color=sns.color_palette("husl", len(pivot.columns)))
            ax.set_title('Pedidos por Tipo', fontsize=16)
            ax.set_xlabel('Tipo Limite', fontsize=14)
            plt.xticks(rotation=45, fontsize=12)
            st.pyplot(fig)
        
        with col2:
            pivot2 = pd.crosstab(df_abertos['TIPO_LIMITE'], df_abertos['TIPO_ITEM'],
                                values=df_abertos['QT_PECAS'], aggfunc='sum').fillna(0)
            fig, ax = plt.subplots(figsize=(12, 6))
            pivot2.plot(kind='bar', stacked=True, ax=ax,
                       color=sns.color_palette("husl", len(pivot2.columns)))
            ax.set_title('Peças por Tipo', fontsize=16)
            ax.set_xlabel('Tipo Limite', fontsize=14)
            plt.xticks(rotation=45, fontsize=12)
            st.pyplot(fig)
    
    # INFO
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; background: #e8f4fd; border-radius: 10px; margin-top: 20px;'>
        <h3>🕒 Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</h3>
        <h3>⏱️ Próximo refresh em {MINUTOS_PARA_REFRESH} minutos</h3>
    </div>
    """, unsafe_allow_html=True)

else:
    st.error("❌ Erro na API - tentando novamente...")
    time.sleep(5)
    st.rerun()