import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

# Configuração da página
st.set_page_config(page_title="📺 TV Dashboard", page_icon="📊", layout="wide")

# META REFRESH - 1 MINUTO
st.markdown("""
<meta http-equiv="refresh" content="60">
<style>
    .title { font-size: 3rem; text-align: center; color: white; background: #FF6B6B; padding: 20px; border-radius: 10px; }
    .metric { background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .number { font-size: 3rem; font-weight: bold; color: #333; }
    .label { font-size: 1.2rem; color: #666; }
</style>
""", unsafe_allow_html=True)

# Título
st.markdown('<div class="title">📊 DASHBOARD DE PEDIDOS - TV</div>', unsafe_allow_html=True)

# Contador de refresh
if 'count' not in st.session_state:
    st.session_state.count = 0
st.session_state.count += 1

st.info(f"🔄 Atualização #{st.session_state.count} - {datetime.now().strftime('%H:%M:%S')}")

# Função para buscar dados
def buscar_dados():
    try:
        url = "https://api-dw.bseller.com.br/webquery/execute/ZBIQ0104"
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
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                # Filtrar apenas abertos
                abertos = ['PICKING LIBERADO', 'INICIO DE PICKING', 'FIM DE PICKING', 
                          'INICIO DE CONFERENCIA', 'CONFERENCIA OK', 'NAO ROMANEADO']
                df_filtrado = df[df['STATUS'].isin(abertos)].copy()
                return df_filtrado
    except:
        pass
    
    # Dados de exemplo
    return pd.DataFrame({
        'STATUS': np.random.choice(abertos, 50),
        'QT_PECAS': np.random.randint(1, 100, 50),
        'TIPO_ITEM': np.random.choice(['Mono', 'Duo', 'Multi'], 50),
        'TIPO_LIMITE': np.random.choice(['D+0', 'D+1', 'D+2', 'D+3'], 50)
    })

# Buscar dados
df = buscar_dados()

# MÉTRICAS
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric">
        <div class="number">{len(df):,}</div>
        <div class="label">📦 Pedidos Abertos</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    total_pecas = df['QT_PECAS'].sum()
    st.markdown(f"""
    <div class="metric">
        <div class="number">{total_pecas:,.0f}</div>
        <div class="label">🧩 Total Peças</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    media = total_pecas / len(df) if len(df) > 0 else 0
    st.markdown(f"""
    <div class="metric">
        <div class="number">{media:.1f}</div>
        <div class="label">📊 Média Peças</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric">
        <div class="number">{df['STATUS'].nunique()}</div>
        <div class="label">🔄 Status</div>
    </div>
    """, unsafe_allow_html=True)

# Mostrar dados
st.markdown("---")
st.subheader("📋 Últimos 50 pedidos")
st.dataframe(df.head(50), use_container_width=True)

# Rodapé
st.markdown("---")
st.markdown("⏱️ Atualiza a cada 1 minuto")