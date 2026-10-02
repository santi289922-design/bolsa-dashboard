"""
Dashboard Bolsa Buffett-Graham - VERSIÓN 3
Con Google Sheets como base de datos (sync automático PC + Celular)
Autor: Para David Lopez - Plan A + Plan B
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Bolsa Buffett-Graham",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a4a2d 0%, #2d5a3d 100%);
        color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;
    }
    .plan-a-badge {
        background: #2d5a3d; color: white; padding: 4px 12px;
        border-radius: 20px; font-weight: bold; font-size: 12px;
    }
    .plan-b-badge {
        background: #2a4a7a; color: white; padding: 4px 12px;
        border-radius: 20px; font-weight: bold; font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ============ CONEXIÓN GOOGLE SHEETS ============
@st.cache_resource
def conectar_google_sheets():
    """Conecta con Google Sheets usando credenciales de Streamlit Secrets."""
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(st.secrets["sheet_id"])
        return sheet
    except Exception as e:
        st.error(f"❌ Error conectando con Google Sheets: {e}")
        st.info("Verifica Streamlit Secrets: gcp_service_account y sheet_id")
        return None

def cargar_datos():
    """Carga todos los datos desde Google Sheets."""
    sheet = conectar_google_sheets()
    if sheet is None:
        return
    
    try:
        # Posiciones
        ws_pos = sheet.worksheet("posiciones")
        records = ws_pos.get_all_records()
        st.session_state.posiciones = []
        for r in records:
            if r.get('ticker'):
                st.session_state.posiciones.append({
                    'ticker': str(r['ticker']),
                    'shares': float(r.get('shares', 0) or 0),
                    'costo_promedio': float(r.get('costo_promedio', 0) or 0),
                    'precio_actual': float(r.get('precio_actual', 0) or 0),
                    'cuenta': str(r.get('cuenta', 'Plan A')),
                    'sector': str(r.get('sector', 'Otro')),
                    'fecha_compra': str(r.get('fecha_compra', '')),
                    'ultima_actualizacion_precio': str(r.get('ultima_actualizacion_precio', '') or None)
                })
        
        # Órdenes
        ws_ord = sheet.worksheet("ordenes")
        records = ws_ord.get_all_records()
        st.session_state.ordenes = []
        for r in records:
            if r.get('ticker'):
                st.session_state.ordenes.append({
                    'ticker': str(r['ticker']),
                    'tipo': str(r.get('tipo', 'BUY')),
                    'precio_limit': float(r.get('precio_limit', 0) or 0),
                    'cantidad': float(r.get('cantidad', 0) or 0),
                    'cuenta': str(r.get('cuenta', 'Plan A')),
                    'precio_actual': float(r.get('precio_actual', 0) or 0),
                    'fecha': str(r.get('fecha', ''))
                })
        
        # Análisis
        ws_an = sheet.worksheet("analisis")
        records = ws_an.get_all_records()
        st.session_state.analisis_globaldata = {}
        for r in records:
            if r.get('ticker'):
                ticker = str(r['ticker'])
                st.session_state.analisis_globaldata[ticker] = {
                    'ticker': ticker,
                    'revenue': float(r.get('revenue', 0) or 0),
                    'revenue_growth': float(r.get('revenue_growth', 0) or 0),
                    'net_income': float(r.get('net_income', 0) or 0),
                    'eps': float(r.get('eps', 0) or 0),
                    'eps_growth': float(r.get('eps_growth', 0) or 0),
                    'operating_margin': float(r.get('operating_margin', 0) or 0),
                    'roe': float(r.get('roe', 0) or 0),
                    'debt_to_equity': float(r.get('debt_to_equity', 0) or 0),
                    'cash_from_operations': float(r.get('cash_from_operations', 0) or 0),
                    'precio_actual': float(r.get('precio_actual', 0) or 0),
                    'puntaje': int(r.get('puntaje', 0) or 0),
                    'decision': str(r.get('decision', '')),
                    'fecha_analisis': str(r.get('fecha_analisis', ''))
                }
        
        # Config
        ws_cfg = sheet.worksheet("config")
        records = ws_cfg.get_all_records()
        for r in records:
            if r.get('parametro'):
                param = str(r['parametro'])
                try:
                    valor = float(r.get('valor', 0) or 0)
                except:
                    valor = 0
                setattr(st.session_state, param, valor)
        
        return True
    except Exception as e:
        st.error(f"❌ Error cargando datos: {e}")
        return False

def guardar_posiciones():
    """Guarda posiciones en Google Sheets."""
    sheet = conectar_google_sheets()
    if sheet is None:
        return False
    try:
        ws = sheet.worksheet("posiciones")
        ws.clear()
        headers = ['ticker', 'shares', 'costo_promedio', 'precio_actual', 
                   'cuenta', 'sector', 'fecha_compra', 'ultima_actualizacion_precio']
        ws.append_row(headers)
        for p in st.session_state.posiciones:
            ws.append_row([
                p.get('ticker', ''), p.get('shares', 0), p.get('costo_promedio', 0),
                p.get('precio_actual', 0), p.get('cuenta', ''), p.get('sector', ''),
                p.get('fecha_compra', ''), p.get('ultima_actualizacion_precio', '') or ''
            ])
        return True
    except Exception as e:
        st.error(f"Error guardando posiciones: {e}")
        return False

def guardar_ordenes():
    """Guarda órdenes en Google Sheets."""
    sheet = conectar_google_sheets()
    if sheet is None:
        return False
    try:
        ws = sheet.worksheet("ordenes")
        ws.clear()
        headers = ['ticker', 'tipo', 'precio_limit', 'cantidad', 'cuenta', 'precio_actual', 'fecha']
        ws.append_row(headers)
        for o in st.session_state.ordenes:
            ws.append_row([
                o.get('ticker', ''), o.get('tipo', ''), o.get('precio_limit', 0),
                o.get('cantidad', 0), o.get('cuenta', ''), o.get('precio_actual', 0),
                o.get('fecha', '')
            ])
        return True
    except Exception as e:
        st.error(f"Error guardando órdenes: {e}")
        return False

def guardar_analisis():
    """Guarda análisis en Google Sheets."""
    sheet = conectar_google_sheets()
    if sheet is None:
        return False
    try:
        ws = sheet.worksheet("analisis")
        ws.clear()
        headers = ['ticker', 'revenue', 'revenue_growth', 'net_income', 'eps', 'eps_growth',
                   'operating_margin', 'roe', 'debt_to_equity', 'cash_from_operations',
                   'precio_actual', 'puntaje', 'decision', 'fecha_analisis']
        ws.append_row(headers)
        for ticker, d in st.session_state.analisis_globaldata.items():
            an = d.get('analisis', {})
            ws.append_row([
                ticker, d.get('revenue', 0), d.get('revenue_growth', 0),
                d.get('net_income', 0), d.get('eps', 0), d.get('eps_growth', 0),
                d.get('operating_margin', 0), d.get('roe', 0), d.get('debt_to_equity', 0),
                d.get('cash_from_operations', 0), d.get('precio_actual', 0),
                an.get('puntaje', 0), an.get('decision', ''), d.get('fecha_analisis', '')
            ])
        return True
    except Exception as e:
        st.error(f"Error guardando análisis: {e}")
        return False

def guardar_config():
    """Guarda config en Google Sheets."""
    sheet = conectar_google_sheets()
    if sheet is None:
        return False
    try:
        ws = sheet.worksheet("config")
        ws.clear()
        headers = ['parametro', 'valor']
        ws.append_row(headers)
        for param in ['inversion_inicial_a', 'inversion_inicial_b', 'cash_a', 
                      'cash_b', 'pyg_realizada_a', 'pyg_realizada_b']:
            ws.append_row([param, getattr(st.session_state, param, 0)])
        return True
    except Exception as e:
        st.error(f"Error guardando config: {e}")
        return False

# ============ INICIALIZACIÓN ============
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False
if 'posiciones' not in st.session_state:
    st.session_state.posiciones = []
if 'ordenes' not in st.session_state:
    st.session_state.ordenes = []
if 'analisis_globaldata' not in st.session_state:
    st.session_state.analisis_globaldata = {}
if 'inversion_inicial_a' not in st.session_state:
    st.session_state.inversion_inicial_a = 2500.0
if 'inversion_inicial_b' not in st.session_state:
    st.session_state.inversion_inicial_b = 3000.0
if 'cash_a' not in st.session_state:
    st.session_state.cash_a = 793.34
if 'cash_b' not in st.session_state:
    st.session_state.cash_b = 2610.0
if 'pyg_realizada_a' not in st.session_state:
    st.session_state.pyg_realizada_a = 42.73
if 'pyg_realizada_b' not in st.session_state:
    st.session_state.pyg_realizada_b = 0.0

# Cargar datos automáticamente al abrir la app
if not st.session_state.datos_cargados:
    with st.spinner("🔄 Cargando datos de Google Sheets..."):
        if cargar_datos():
            st.session_state.datos_cargados = True

# ============ FUNCIONES ============

def analizar_buffett_graham(data):
    puntaje = 0
    razones_positivas = []
    razones_negativas = []
    
    if data.get('net_income', 0) > 0:
        puntaje += 15
        razones_positivas.append(f"✅ Genera ganancias (${data['net_income']:,.0f}M)")
    else:
        razones_negativas.append("❌ No genera ganancias")
    
    growth = data.get('revenue_growth', 0)
    if growth > 15:
        puntaje += 20
        razones_positivas.append(f"🚀 Crecimiento alto ({growth:.1f}%)")
    elif growth > 8:
        puntaje += 10
        razones_positivas.append(f"✅ Crecimiento sólido ({growth:.1f}%)")
    elif growth < 0:
        razones_negativas.append(f"❌ Crecimiento negativo ({growth:.1f}%)")
    
    margin = data.get('operating_margin', 0)
    if margin > 25:
        puntaje += 15
        razones_positivas.append(f"🏆 Márgenes excelentes ({margin:.1f}%) - Wide moat")
    elif margin > 15:
        puntaje += 10
        razones_positivas.append(f"✅ Márgenes buenos ({margin:.1f}%)")
    elif margin < 5:
        razones_negativas.append(f"⚠️ Márgenes bajos ({margin:.1f}%)")
    
    debt_equity = data.get('debt_to_equity', 1)
    if debt_equity < 0.3:
        puntaje += 15
        razones_positivas.append(f"💪 Deuda baja ({debt_equity:.2f})")
    elif debt_equity < 0.6:
        puntaje += 8
    elif debt_equity > 1.5:
        razones_negativas.append(f"⚠️ Deuda alta ({debt_equity:.2f})")
    
    roe = data.get('roe', 0)
    if roe > 20:
        puntaje += 15
        razones_positivas.append(f"🏆 ROE excelente ({roe:.1f}%)")
    elif roe > 12:
        puntaje += 10
        razones_positivas.append(f"✅ ROE bueno ({roe:.1f}%)")
    
    eps_growth = data.get('eps_growth', 0)
    if eps_growth > 15:
        puntaje += 10
        razones_positivas.append(f"🚀 EPS creciendo {eps_growth:.1f}%")
    elif eps_growth > 5:
        puntaje += 5
    elif eps_growth < 0:
        razones_negativas.append(f"❌ EPS decreciendo")
    
    cash_flow = data.get('cash_from_operations', 0)
    if cash_flow > 0:
        puntaje += 10
        razones_positivas.append(f"✅ Cash flow positivo")
    else:
        razones_negativas.append("❌ Cash flow negativo")
    
    if puntaje >= 75:
        decision = "COMPRAR / MANTENER FUERTE"
        emoji = "🟢"
    elif puntaje >= 50:
        decision = "MANTENER"
        emoji = "🟡"
    elif puntaje >= 30:
        decision = "VIGILAR / REDUCIR"
        emoji = "🟠"
    else:
        decision = "EVITAR / VENDER"
        emoji = "🔴"
    
    return {
        'puntaje': puntaje, 'decision': decision, 'emoji': emoji,
        'positivas': razones_positivas, 'negativas': razones_negativas
    }

def calcular_pyg_posicion(posicion):
    costo_total = posicion['shares'] * posicion['costo_promedio']
    valor_actual = posicion['shares'] * posicion.get('precio_actual', posicion['costo_promedio'])
    pyg = valor_actual - costo_total
    pyg_pct = (pyg / costo_total) * 100 if costo_total > 0 else 0
    return pyg, pyg_pct

def tiempo_desde_actualizacion(timestamp_str):
    if not timestamp_str or timestamp_str == 'None':
        return "Nunca"
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        delta = datetime.now() - timestamp
        if delta.total_seconds() < 3600:
            return f"Hace {int(delta.total_seconds() / 60)} min"
        elif delta.total_seconds() < 86400:
            return f"Hace {int(delta.total_seconds() / 3600)}h"
        elif delta.days < 7:
            return f"Hace {delta.days}d"
        else:
            return f"Hace {delta.days}d ⚠️"
    except:
        return "N/A"

# ============ SIDEBAR ============
st.sidebar.title("📊 Bolsa B-G")
st.sidebar.caption("💾 Datos en Google Sheets")

if st.sidebar.button("🔄 Recargar datos"):
    st.session_state.datos_cargados = False
    st.rerun()

st.sidebar.markdown("---")

pagina = st.sidebar.radio(
    "Navegación",
    ["🏠 Dashboard", "💼 Mis Posiciones", "💱 Actualizar Precios",
     "📋 Órdenes Activas", "🔍 Análisis GlobalData",
     "📄 Generar Reporte", "⚙️ Configuración"]
)

st.sidebar.markdown("---")
st.sidebar.caption(f"🕐 {datetime.now().strftime('%d/%m %H:%M')}")

# ============ PÁGINA: DASHBOARD ============
if pagina == "🏠 Dashboard":
    st.markdown("""
    <div class="main-header">
        <h1>📊 Dashboard Bolsa Buffett-Graham</h1>
        <p>Sistema dual Plan A + Plan B | Datos sincronizados en la nube</p>
    </div>
    """, unsafe_allow_html=True)
    
    pos_a = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan A']
    pos_b = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan B']
    
    valor_a = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_a) + st.session_state.cash_a
    valor_b = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_b) + st.session_state.cash_b
    valor_total = valor_a + valor_b
    
    pyg_papel_a = sum(calcular_pyg_posicion(p)[0] for p in pos_a)
    pyg_papel_b = sum(calcular_pyg_posicion(p)[0] for p in pos_b)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💼 Total", f"${valor_total:,.2f}", f"+${pyg_papel_a + pyg_papel_b:.2f}")
    with col2:
        st.metric("🏆 Plan A", f"${valor_a:,.2f}", f"+${pyg_papel_a:.2f}")
    with col3:
        st.metric("🚀 Plan B", f"${valor_b:,.2f}", f"+${pyg_papel_b:.2f}")
    with col4:
        cash_total = st.session_state.cash_a + st.session_state.cash_b
        st.metric("💰 Cash", f"${cash_total:,.2f}",
                  f"{(cash_total/valor_total*100):.1f}%" if valor_total > 0 else "0%")
    
    st.markdown("---")
    
    # Comparación
    st.subheader("📈 Comparación Rendimiento")
    if st.session_state.posiciones:
        todos_tickers = [f"{p['ticker']} ({p['cuenta']})" for p in st.session_state.posiciones]
        col_sel, col_tipo = st.columns([3, 1])
        with col_sel:
            tickers_sel = st.multiselect("Acciones:", todos_tickers, default=todos_tickers)
        with col_tipo:
            tipo_g = st.selectbox("Tipo", ["Barras", "Líneas"])
        
        if tickers_sel:
            data_comp = []
            for pos in st.session_state.posiciones:
                label = f"{pos['ticker']} ({pos['cuenta']})"
                if label in tickers_sel:
                    pyg, pyg_pct = calcular_pyg_posicion(pos)
                    data_comp.append({
                        'Ticker': pos['ticker'], 'Cuenta': pos['cuenta'], 'Label': label,
                        'PyG $': pyg, 'PyG %': pyg_pct,
                        'Valor Actual': pos['shares'] * pos.get('precio_actual', pos['costo_promedio'])
                    })
            df_comp = pd.DataFrame(data_comp)
            metrica = st.radio("Ver:", ["PyG %", "PyG $", "Valor Actual"], horizontal=True)
            
            if tipo_g == "Barras":
                fig = px.bar(df_comp.sort_values(metrica, ascending=False),
                             x='Label', y=metrica, color='Cuenta',
                             color_discrete_map={'Plan A': '#2d5a3d', 'Plan B': '#2a4a7a'},
                             text=metrica)
                if metrica == "PyG %":
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                else:
                    fig.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
                fig.update_layout(height=400)
            else:
                fig = go.Figure()
                for cuenta in ['Plan A', 'Plan B']:
                    df_c = df_comp[df_comp['Cuenta'] == cuenta].sort_values(metrica)
                    if not df_c.empty:
                        fig.add_trace(go.Scatter(
                            x=df_c['Ticker'], y=df_c[metrica], mode='lines+markers',
                            name=cuenta, line=dict(color='#2d5a3d' if cuenta == 'Plan A' else '#2a4a7a', width=3)
                        ))
                fig.update_layout(height=400)
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Agrega posiciones para ver comparación")
    
    st.markdown("---")
    
    # Pies
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Plan A")
        if pos_a:
            df_a = pd.DataFrame([{'Ticker': p['ticker'],
                'Valor': p['shares'] * p.get('precio_actual', p['costo_promedio'])} for p in pos_a])
            df_a.loc[len(df_a)] = ['Cash', st.session_state.cash_a]
            st.plotly_chart(px.pie(df_a, values='Valor', names='Ticker', hole=0.4), use_container_width=True)
    with col2:
        st.subheader("📊 Plan B")
        if pos_b:
            df_b = pd.DataFrame([{'Ticker': p['ticker'],
                'Valor': p['shares'] * p.get('precio_actual', p['costo_promedio'])} for p in pos_b])
            df_b.loc[len(df_b)] = ['Cash', st.session_state.cash_b]
            st.plotly_chart(px.pie(df_b, values='Valor', names='Ticker', hole=0.4), use_container_width=True)

# ============ PÁGINA: MIS POSICIONES ============
elif pagina == "💼 Mis Posiciones":
    st.title("💼 Mis Posiciones")
    tab1, tab2 = st.tabs(["➕ Agregar", "📋 Ver"])
    
    with tab1:
        st.caption("💡 Solo meter datos de la COMPRA")
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Ticker").upper()
            shares = st.number_input("Shares", 0.0, format="%.6f")
            costo = st.number_input("💰 Costo promedio ($)", 0.0, format="%.2f")
        with col2:
            cuenta = st.selectbox("Cuenta", ["Plan A", "Plan B"])
            sector = st.selectbox("Sector", ["Tech", "Semis", "Consumer", "Financial",
                                              "Energy", "Oro", "Crypto", "ETF", "Otro"])
            fecha_c = st.date_input("Fecha compra", datetime.now())
        
        if st.button("➕ Agregar y guardar en Sheets", type="primary"):
            if ticker and shares > 0 and costo > 0:
                st.session_state.posiciones.append({
                    'ticker': ticker, 'shares': shares, 'costo_promedio': costo,
                    'precio_actual': costo, 'cuenta': cuenta, 'sector': sector,
                    'fecha_compra': fecha_c.strftime('%Y-%m-%d'),
                    'ultima_actualizacion_precio': None
                })
                with st.spinner("Guardando en Google Sheets..."):
                    if guardar_posiciones():
                        st.success(f"✅ {ticker} guardado en la nube")
                        st.rerun()
    
    with tab2:
        if st.session_state.posiciones:
            for cuenta_f in ["Plan A", "Plan B"]:
                pos_c = [p for p in st.session_state.posiciones if p['cuenta'] == cuenta_f]
                if pos_c:
                    badge = 'plan-a-badge' if cuenta_f == 'Plan A' else 'plan-b-badge'
                    st.markdown(f'<span class="{badge}">{cuenta_f}</span>', unsafe_allow_html=True)
                    data = []
                    for i, p in enumerate(st.session_state.posiciones):
                        if p['cuenta'] != cuenta_f:
                            continue
                        pyg, pyg_pct = calcular_pyg_posicion(p)
                        data.append({
                            '#': i, 'Ticker': p['ticker'], 'Shares': f"{p['shares']:.4f}",
                            'Costo': f"${p['costo_promedio']:.2f}",
                            'Actual': f"${p.get('precio_actual', 0):.2f}",
                            'PyG $': f"${pyg:+.2f}", 'PyG %': f"{pyg_pct:+.1f}%",
                            'Actualizado': tiempo_desde_actualizacion(p.get('ultima_actualizacion_precio'))
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                    st.markdown("---")
            
            with st.expander("🗑️ Eliminar"):
                idx = st.number_input("Índice #", 0, len(st.session_state.posiciones)-1)
                if st.button("Eliminar y guardar"):
                    st.session_state.posiciones.pop(idx)
                    guardar_posiciones()
                    st.rerun()
        else:
            st.info("Sin posiciones")

# ============ PÁGINA: ACTUALIZAR PRECIOS ============
elif pagina == "💱 Actualizar Precios":
    st.title("💱 Actualizar Precios")
    
    if not st.session_state.posiciones:
        st.info("Agrega posiciones primero")
    else:
        for cuenta_f in ["Plan A", "Plan B"]:
            pos_c = [(i, p) for i, p in enumerate(st.session_state.posiciones) if p['cuenta'] == cuenta_f]
            if pos_c:
                badge = 'plan-a-badge' if cuenta_f == 'Plan A' else 'plan-b-badge'
                st.markdown(f'<span class="{badge}">{cuenta_f}</span>', unsafe_allow_html=True)
                
                for idx, pos in pos_c:
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    with col1:
                        st.markdown(f"**{pos['ticker']}**")
                        st.caption(f"Costo: ${pos['costo_promedio']:.2f}")
                    with col2:
                        nuevo = st.number_input(
                            "Precio actual $",
                            value=float(pos.get('precio_actual', pos['costo_promedio'])),
                            format="%.2f", key=f"p_{idx}", label_visibility="collapsed"
                        )
                    with col3:
                        pyg, pyg_pct = calcular_pyg_posicion({
                            'shares': pos['shares'], 'costo_promedio': pos['costo_promedio'],
                            'precio_actual': nuevo
                        })
                        color = "🟢" if pyg >= 0 else "🔴"
                        st.markdown(f"{color} **${pyg:+.2f}** ({pyg_pct:+.1f}%)")
                        st.caption(f"⏱️ {tiempo_desde_actualizacion(pos.get('ultima_actualizacion_precio'))}")
                    with col4:
                        if st.button("💾", key=f"s_{idx}"):
                            st.session_state.posiciones[idx]['precio_actual'] = nuevo
                            st.session_state.posiciones[idx]['ultima_actualizacion_precio'] = datetime.now().isoformat()
                            guardar_posiciones()
                            st.rerun()
                    st.markdown("---")
        
        if st.button("💾 Guardar TODOS en Sheets", type="primary"):
            for idx in range(len(st.session_state.posiciones)):
                key = f"p_{idx}"
                if key in st.session_state:
                    st.session_state.posiciones[idx]['precio_actual'] = st.session_state[key]
                    st.session_state.posiciones[idx]['ultima_actualizacion_precio'] = datetime.now().isoformat()
            if guardar_posiciones():
                st.success("✅ Todos guardados")
                st.balloons()
                st.rerun()

# ============ PÁGINA: ÓRDENES ============
elif pagina == "📋 Órdenes Activas":
    st.title("📋 Órdenes GTC")
    tab1, tab2 = st.tabs(["➕ Agregar", "📋 Ver"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            ticker_o = st.text_input("Ticker").upper()
            tipo = st.selectbox("Tipo", ["BUY", "SELL"])
            precio = st.number_input("Precio LIMIT", 0.0, format="%.2f")
        with col2:
            cantidad = st.number_input("Cantidad", 0.0, format="%.4f")
            cuenta_o = st.selectbox("Cuenta", ["Plan A", "Plan B"], key="co")
            precio_act = st.number_input("Precio mercado", 0.0, format="%.2f", key="pm")
        
        if st.button("➕ Agregar y guardar", type="primary"):
            if ticker_o and precio > 0:
                st.session_state.ordenes.append({
                    'ticker': ticker_o, 'tipo': tipo, 'precio_limit': precio,
                    'cantidad': cantidad, 'cuenta': cuenta_o, 'precio_actual': precio_act,
                    'fecha': datetime.now().strftime('%Y-%m-%d')
                })
                if guardar_ordenes():
                    st.success(f"✅ Orden guardada")
                    st.rerun()
    
    with tab2:
        if st.session_state.ordenes:
            data = []
            for i, o in enumerate(st.session_state.ordenes):
                data.append({
                    '#': i, 'Ticker': o['ticker'], 'Tipo': o['tipo'],
                    'Limit': f"${o['precio_limit']:.2f}",
                    'Actual': f"${o['precio_actual']:.2f}",
                    'Cuenta': o['cuenta']
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            with st.expander("🗑️ Eliminar"):
                idx = st.number_input("Índice", 0, len(st.session_state.ordenes)-1)
                if st.button("Eliminar"):
                    st.session_state.ordenes.pop(idx)
                    guardar_ordenes()
                    st.rerun()
        else:
            st.info("Sin órdenes")

# ============ PÁGINA: ANÁLISIS GLOBALDATA ============
elif pagina == "🔍 Análisis GlobalData":
    st.title("🔍 Análisis GlobalData")
    tab1, tab2 = st.tabs(["➕ Nuevo", "📊 Guardados"])
    
    with tab1:
        ticker_g = st.text_input("Ticker").upper()
        st.markdown("### 📊 Financials")
        col1, col2, col3 = st.columns(3)
        with col1:
            rev_a = st.number_input("Revenue 2026 ($M)", 0.0)
            rev_p = st.number_input("Revenue 2025 ($M)", 0.0)
        with col2:
            ni = st.number_input("Net Income ($M)", 0.0)
            eps_a = st.number_input("EPS 2026", 0.0, format="%.2f")
        with col3:
            eps_p = st.number_input("EPS 2025", 0.0, format="%.2f")
            cf = st.number_input("Cash Operations ($M)", 0.0)
        
        st.markdown("### 📈 Ratios")
        col1, col2, col3 = st.columns(3)
        with col1:
            om = st.number_input("Operating Margin %", 0.0, format="%.1f")
        with col2:
            roe = st.number_input("ROE %", 0.0, format="%.1f")
        with col3:
            de = st.number_input("Debt/Equity", 0.0, format="%.2f")
            pa = st.number_input("Precio actual $", 0.0, format="%.2f")
        
        if st.button("🔍 Analizar y guardar", type="primary"):
            if ticker_g:
                rg = ((rev_a - rev_p) / rev_p * 100) if rev_p > 0 else 0
                epsg = ((eps_a - eps_p) / eps_p * 100) if eps_p > 0 else 0
                data = {
                    'ticker': ticker_g, 'revenue': rev_a, 'revenue_growth': rg,
                    'net_income': ni, 'eps': eps_a, 'eps_growth': epsg,
                    'operating_margin': om, 'roe': roe, 'debt_to_equity': de,
                    'cash_from_operations': cf, 'precio_actual': pa,
                    'fecha_analisis': datetime.now().strftime('%Y-%m-%d')
                }
                an = analizar_buffett_graham(data)
                data['analisis'] = an
                st.session_state.analisis_globaldata[ticker_g] = data
                if guardar_analisis():
                    st.success(f"✅ Guardado")
                
                st.markdown(f"## {an['emoji']} {ticker_g} - {an['puntaje']}/100")
                st.markdown(f"### **{an['decision']}**")
                col1, col2 = st.columns(2)
                with col1:
                    for p in an['positivas']:
                        st.markdown(f"- {p}")
                with col2:
                    for n in an['negativas']:
                        st.markdown(f"- {n}")
    
    with tab2:
        if st.session_state.analisis_globaldata:
            for t, d in st.session_state.analisis_globaldata.items():
                an = d.get('analisis', {})
                with st.expander(f"{an.get('emoji', '')} {t} - {d.get('decision', '')} ({d.get('puntaje', 0)}/100)"):
                    st.json(d)

# ============ PÁGINA: GENERAR REPORTE ============
elif pagina == "📄 Generar Reporte":
    st.title("📄 Generar Reporte")
    formato = st.radio("Formato", ["📊 JSON (para Claude)", "📋 Texto WhatsApp"])
    
    pos_a = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan A']
    pos_b = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan B']
    valor_a = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_a) + st.session_state.cash_a
    valor_b = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_b) + st.session_state.cash_b
    
    if st.button("🚀 Generar", type="primary"):
        if formato == "📊 JSON (para Claude)":
            rep = {
                'fecha': datetime.now().isoformat(),
                'config': {k: getattr(st.session_state, k) for k in 
                          ['inversion_inicial_a', 'inversion_inicial_b', 'cash_a', 
                           'cash_b', 'pyg_realizada_a', 'pyg_realizada_b']},
                'posiciones': st.session_state.posiciones,
                'ordenes': st.session_state.ordenes,
                'analisis': st.session_state.analisis_globaldata
            }
            js = json.dumps(rep, indent=2, ensure_ascii=False)
            st.code(js, language='json')
            st.download_button("📥 Descargar JSON", js,
                             file_name=f"bolsa_{datetime.now().strftime('%Y%m%d')}.json")
        else:
            txt = f"""📊 *BOLSA - {datetime.now().strftime('%d/%m/%Y')}*

💼 Plan A: ${valor_a:,.2f}
🚀 Plan B: ${valor_b:,.2f}
💰 TOTAL: ${valor_a+valor_b:,.2f}

Cash A: ${st.session_state.cash_a:.2f}
Cash B: ${st.session_state.cash_b:.2f}
"""
            st.text_area("Copiar:", txt, height=250)

# ============ PÁGINA: CONFIGURACIÓN ============
elif pagina == "⚙️ Configuración":
    st.title("⚙️ Configuración")
    st.caption("Los cambios se guardan automáticamente en Google Sheets")
    
    st.subheader("💰 Inversión Inicial")
    col1, col2 = st.columns(2)
    with col1:
        nueva_inv_a = st.number_input("Plan A ($)", value=float(st.session_state.inversion_inicial_a), format="%.2f")
    with col2:
        nueva_inv_b = st.number_input("Plan B ($)", value=float(st.session_state.inversion_inicial_b), format="%.2f")
    
    st.subheader("💵 Cash")
    col1, col2 = st.columns(2)
    with col1:
        nuevo_cash_a = st.number_input("Cash Plan A ($)", value=float(st.session_state.cash_a), format="%.2f")
    with col2:
        nuevo_cash_b = st.number_input("Cash Plan B ($)", value=float(st.session_state.cash_b), format="%.2f")
    
    st.subheader("💵 PyG Realizada")
    col1, col2 = st.columns(2)
    with col1:
        nueva_pyg_a = st.number_input("PyG Plan A ($)", value=float(st.session_state.pyg_realizada_a), format="%.2f")
    with col2:
        nueva_pyg_b = st.number_input("PyG Plan B ($)", value=float(st.session_state.pyg_realizada_b), format="%.2f")
    
    if st.button("💾 Guardar configuración en Sheets", type="primary"):
        st.session_state.inversion_inicial_a = nueva_inv_a
        st.session_state.inversion_inicial_b = nueva_inv_b
        st.session_state.cash_a = nuevo_cash_a
        st.session_state.cash_b = nuevo_cash_b
        st.session_state.pyg_realizada_a = nueva_pyg_a
        st.session_state.pyg_realizada_b = nueva_pyg_b
        if guardar_config():
            st.success("✅ Configuración guardada en la nube")
            st.balloons()
