"""
Dashboard Bolsa Buffett-Graham - VERSIÓN 2
Autor: Para David Lopez - Plan A + Plan B
Mejoras v2:
- Reorganización campos (costo primero, precio actual editable aparte)
- Panel actualización precios con timestamps
- Gráfica comparativa con selector multiselect
- Mejor UX
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go

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
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .plan-a-badge {
        background: #2d5a3d; color: white; padding: 4px 12px;
        border-radius: 20px; font-weight: bold; font-size: 12px;
    }
    .plan-b-badge {
        background: #2a4a7a; color: white; padding: 4px 12px;
        border-radius: 20px; font-weight: bold; font-size: 12px;
    }
    .timestamp {
        font-size: 11px; color: #888; font-style: italic;
    }
    .precio-viejo {
        color: #c0392b; font-weight: bold;
    }
    .precio-reciente {
        color: #27ae60; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============ INICIALIZACIÓN SESSION STATE ============
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

# ============ FUNCIONES ============

def analizar_buffett_graham(data):
    puntaje = 0
    razones_positivas = []
    razones_negativas = []
    
    if data.get('net_income', 0) > 0:
        puntaje += 15
        razones_positivas.append(f"✅ Genera ganancias (${data['net_income']:,.0f}M)")
    else:
        razones_negativas.append("❌ No genera ganancias (red flag)")
    
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
        razones_positivas.append(f"✅ Deuda manejable ({debt_equity:.2f})")
    elif debt_equity > 1.5:
        razones_negativas.append(f"⚠️ Deuda alta ({debt_equity:.2f})")
    
    roe = data.get('roe', 0)
    if roe > 20:
        puntaje += 15
        razones_positivas.append(f"🏆 ROE excelente ({roe:.1f}%)")
    elif roe > 12:
        puntaje += 10
        razones_positivas.append(f"✅ ROE bueno ({roe:.1f}%)")
    elif roe < 8:
        razones_negativas.append(f"⚠️ ROE bajo ({roe:.1f}%)")
    
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
        razones_positivas.append(f"✅ Genera cash flow (${cash_flow:,.0f}M)")
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
        'puntaje': puntaje,
        'decision': decision,
        'emoji': emoji,
        'positivas': razones_positivas,
        'negativas': razones_negativas
    }

def calcular_pyg_posicion(posicion):
    costo_total = posicion['shares'] * posicion['costo_promedio']
    valor_actual = posicion['shares'] * posicion.get('precio_actual', posicion['costo_promedio'])
    pyg = valor_actual - costo_total
    pyg_pct = (pyg / costo_total) * 100 if costo_total > 0 else 0
    return pyg, pyg_pct

def tiempo_desde_actualizacion(timestamp_str):
    """Calcula tiempo desde última actualización."""
    if not timestamp_str:
        return "Nunca", "rojo"
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        delta = datetime.now() - timestamp
        
        if delta.total_seconds() < 3600:
            return f"Hace {int(delta.total_seconds() / 60)} min", "verde"
        elif delta.total_seconds() < 86400:
            return f"Hace {int(delta.total_seconds() / 3600)} horas", "verde"
        elif delta.days < 7:
            return f"Hace {delta.days} días", "amarillo"
        else:
            return f"Hace {delta.days} días ⚠️", "rojo"
    except:
        return "Error", "rojo"

# ============ SIDEBAR ============
st.sidebar.title("📊 Bolsa B-G")
st.sidebar.markdown("---")

pagina = st.sidebar.radio(
    "Navegación",
    ["🏠 Dashboard", "💼 Mis Posiciones", "💱 Actualizar Precios",
     "📋 Órdenes Activas", "🔍 Análisis GlobalData", 
     "📄 Generar Reporte", "⚙️ Configuración"]
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Hora actual: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ============ PÁGINA: DASHBOARD ============
if pagina == "🏠 Dashboard":
    st.markdown("""
    <div class="main-header">
        <h1>📊 Dashboard Bolsa Buffett-Graham</h1>
        <p>Sistema dual Plan A + Plan B | Sistema automatizado con GTC orders</p>
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
        st.metric("💼 Patrimonio Total", f"${valor_total:,.2f}",
                  f"+${pyg_papel_a + pyg_papel_b:.2f}")
    with col2:
        st.metric("🏆 Plan A", f"${valor_a:,.2f}", f"+${pyg_papel_a:.2f}")
    with col3:
        st.metric("🚀 Plan B", f"${valor_b:,.2f}", f"+${pyg_papel_b:.2f}")
    with col4:
        cash_total = st.session_state.cash_a + st.session_state.cash_b
        cash_pct = (cash_total / valor_total * 100) if valor_total > 0 else 0
        st.metric("💰 Cash Total", f"${cash_total:,.2f}", f"{cash_pct:.1f}%")
    
    st.markdown("---")
    
    # ============ GRÁFICA COMPARATIVA (NUEVA) ============
    st.subheader("📈 Comparación Rendimiento Acciones")
    
    if st.session_state.posiciones:
        # Selector multiselect
        todos_tickers = [f"{p['ticker']} ({p['cuenta']})" for p in st.session_state.posiciones]
        
        col_sel, col_tipo = st.columns([3, 1])
        with col_sel:
            tickers_seleccionados = st.multiselect(
                "Selecciona acciones a comparar (vacío = todas)",
                options=todos_tickers,
                default=todos_tickers
            )
        with col_tipo:
            tipo_grafico = st.selectbox("Tipo", ["Barras", "Líneas"])
        
        if tickers_seleccionados:
            # Preparar datos
            data_comp = []
            for pos in st.session_state.posiciones:
                label = f"{pos['ticker']} ({pos['cuenta']})"
                if label in tickers_seleccionados:
                    pyg, pyg_pct = calcular_pyg_posicion(pos)
                    data_comp.append({
                        'Ticker': pos['ticker'],
                        'Cuenta': pos['cuenta'],
                        'Label': label,
                        'PyG $': pyg,
                        'PyG %': pyg_pct,
                        'Valor Actual': pos['shares'] * pos.get('precio_actual', pos['costo_promedio']),
                        'Costo Total': pos['shares'] * pos['costo_promedio']
                    })
            
            df_comp = pd.DataFrame(data_comp)
            
            # Métrica a graficar
            metrica = st.radio("Ver:", ["PyG %", "PyG $", "Valor Actual"], horizontal=True)
            
            if tipo_grafico == "Barras":
                fig = px.bar(
                    df_comp.sort_values(metrica, ascending=False),
                    x='Label', y=metrica, color='Cuenta',
                    color_discrete_map={'Plan A': '#2d5a3d', 'Plan B': '#2a4a7a'},
                    text=metrica
                )
                if metrica == "PyG %":
                    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                else:
                    fig.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
                fig.update_layout(height=400, showlegend=True, xaxis_title="", yaxis_title=metrica)
            else:  # Líneas
                fig = go.Figure()
                for cuenta in ['Plan A', 'Plan B']:
                    df_cuenta = df_comp[df_comp['Cuenta'] == cuenta].sort_values(metrica)
                    if not df_cuenta.empty:
                        fig.add_trace(go.Scatter(
                            x=df_cuenta['Ticker'], y=df_cuenta[metrica],
                            mode='lines+markers+text', name=cuenta,
                            text=df_cuenta[metrica].apply(lambda x: f"{x:.1f}" if metrica == "PyG %" else f"${x:.2f}"),
                            textposition="top center",
                            line=dict(color='#2d5a3d' if cuenta == 'Plan A' else '#2a4a7a', width=3)
                        ))
                fig.update_layout(height=400, xaxis_title="", yaxis_title=metrica)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla resumen
            st.markdown("**Resumen de las acciones seleccionadas:**")
            df_display = df_comp[['Ticker', 'Cuenta', 'Costo Total', 'Valor Actual', 'PyG $', 'PyG %']].copy()
            df_display['Costo Total'] = df_display['Costo Total'].apply(lambda x: f"${x:.2f}")
            df_display['Valor Actual'] = df_display['Valor Actual'].apply(lambda x: f"${x:.2f}")
            df_display['PyG $'] = df_display['PyG $'].apply(lambda x: f"${x:+.2f}")
            df_display['PyG %'] = df_display['PyG %'].apply(lambda x: f"{x:+.1f}%")
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Selecciona al menos una acción para ver la comparación")
    else:
        st.info("Agrega posiciones en '💼 Mis Posiciones' para ver comparación")
    
    st.markdown("---")
    
    # Distribución pie
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Distribución Plan A")
        if pos_a:
            df_a = pd.DataFrame([{
                'Ticker': p['ticker'],
                'Valor': p['shares'] * p.get('precio_actual', p['costo_promedio'])
            } for p in pos_a])
            df_a.loc[len(df_a)] = ['Cash', st.session_state.cash_a]
            fig = px.pie(df_a, values='Valor', names='Ticker', hole=0.4)
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin posiciones en Plan A")
    
    with col2:
        st.subheader("📊 Distribución Plan B")
        if pos_b:
            df_b = pd.DataFrame([{
                'Ticker': p['ticker'],
                'Valor': p['shares'] * p.get('precio_actual', p['costo_promedio'])
            } for p in pos_b])
            df_b.loc[len(df_b)] = ['Cash', st.session_state.cash_b]
            fig = px.pie(df_b, values='Valor', names='Ticker', hole=0.4)
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin posiciones en Plan B")
    
    st.markdown("---")
    
    # Rendimiento
    st.subheader("📈 Rendimiento Total")
    inv_total = st.session_state.inversion_inicial_a + st.session_state.inversion_inicial_b
    pyg_total = pyg_papel_a + pyg_papel_b + st.session_state.pyg_realizada_a + st.session_state.pyg_realizada_b
    rendimiento_pct = (pyg_total / inv_total * 100) if inv_total > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💵 Inversión Inicial", f"${inv_total:,.2f}")
    with col2:
        st.metric("📊 Ganancia Total", f"${pyg_total:+.2f}",
                  f"PyG Real: ${st.session_state.pyg_realizada_a + st.session_state.pyg_realizada_b:.2f}")
    with col3:
        st.metric("🚀 Rendimiento", f"{rendimiento_pct:+.2f}%",
                  f"Anualizado: {rendimiento_pct * 3:.1f}%")

# ============ PÁGINA: MIS POSICIONES (REORGANIZADA) ============
elif pagina == "💼 Mis Posiciones":
    st.title("💼 Mis Posiciones")
    
    tab1, tab2 = st.tabs(["➕ Agregar Posición", "📋 Ver Posiciones"])
    
    with tab1:
        st.subheader("Agregar nueva posición")
        st.caption("💡 Solo meter datos de la COMPRA. El precio actual se actualiza aparte en '💱 Actualizar Precios'")
        
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Ticker", "", placeholder="MSFT").upper()
            shares = st.number_input("Cantidad (shares)", 0.0, format="%.6f")
            costo = st.number_input("💰 Costo promedio (base de coste) $", 0.0, format="%.2f",
                                     help="Precio al que compraste la acción")
        with col2:
            cuenta = st.selectbox("Cuenta", ["Plan A", "Plan B"])
            sector = st.selectbox("Sector", ["Tech", "Semis", "Consumer", "Financial",
                                              "Energy", "Oro", "Crypto", "ETF", "Otro"])
            fecha_compra = st.date_input("Fecha de compra", datetime.now())
        
        if st.button("➕ Agregar posición", type="primary"):
            if ticker and shares > 0 and costo > 0:
                nueva = {
                    'ticker': ticker,
                    'shares': shares,
                    'costo_promedio': costo,
                    'precio_actual': costo,  # Inicia igual al costo (0 PyG)
                    'cuenta': cuenta,
                    'sector': sector,
                    'fecha_compra': fecha_compra.strftime('%Y-%m-%d'),
                    'ultima_actualizacion_precio': None  # Nunca actualizado aún
                }
                st.session_state.posiciones.append(nueva)
                st.success(f"✅ {ticker} agregado a {cuenta}. Ahora ve a '💱 Actualizar Precios' para meter precio actual.")
                st.rerun()
            else:
                st.error("Todos los campos obligatorios")
    
    with tab2:
        if st.session_state.posiciones:
            for cuenta_filtro in ["Plan A", "Plan B"]:
                pos_cuenta = [p for p in st.session_state.posiciones if p['cuenta'] == cuenta_filtro]
                if pos_cuenta:
                    badge_class = 'plan-a-badge' if cuenta_filtro == 'Plan A' else 'plan-b-badge'
                    st.markdown(f'<span class="{badge_class}">{cuenta_filtro}</span>',
                               unsafe_allow_html=True)
                    
                    data = []
                    for i, p in enumerate(st.session_state.posiciones):
                        if p['cuenta'] != cuenta_filtro:
                            continue
                        pyg, pyg_pct = calcular_pyg_posicion(p)
                        tiempo, color = tiempo_desde_actualizacion(p.get('ultima_actualizacion_precio'))
                        data.append({
                            '#': i,
                            'Ticker': p['ticker'],
                            'Shares': f"{p['shares']:.4f}",
                            'Costo Base': f"${p['costo_promedio']:.2f}",
                            'Precio Actual': f"${p.get('precio_actual', 0):.2f}",
                            'PyG $': f"${pyg:+.2f}",
                            'PyG %': f"{pyg_pct:+.1f}%",
                            'Sector': p.get('sector', '-'),
                            'Precio actualizado': tiempo
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                    st.markdown("---")
            
            # Eliminar
            with st.expander("🗑️ Eliminar posición"):
                idx_eliminar = st.number_input("Índice #", 0,
                                               len(st.session_state.posiciones)-1 if st.session_state.posiciones else 0)
                if st.button("Confirmar eliminación"):
                    st.session_state.posiciones.pop(idx_eliminar)
                    st.success("Eliminada")
                    st.rerun()
        else:
            st.info("No tienes posiciones agregadas aún")

# ============ PÁGINA: ACTUALIZAR PRECIOS (NUEVA) ============
elif pagina == "💱 Actualizar Precios":
    st.title("💱 Actualizar Precios Actuales")
    st.caption("💡 Actualiza aquí los precios de mercado. Cada acción guarda la fecha/hora de su última actualización.")
    
    if not st.session_state.posiciones:
        st.info("No tienes posiciones aún. Agrégalas en '💼 Mis Posiciones'.")
    else:
        # Advertencia de precios viejos
        posiciones_viejas = [p for p in st.session_state.posiciones 
                             if p.get('ultima_actualizacion_precio') is None or
                             (datetime.now() - datetime.fromisoformat(p['ultima_actualizacion_precio'])).days > 3]
        
        if posiciones_viejas:
            st.warning(f"⚠️ {len(posiciones_viejas)} acción(es) con precios viejos o nunca actualizados")
        
        st.markdown("---")
        
        # Actualización masiva por cuenta
        for cuenta_filtro in ["Plan A", "Plan B"]:
            pos_cuenta = [(i, p) for i, p in enumerate(st.session_state.posiciones) 
                          if p['cuenta'] == cuenta_filtro]
            
            if pos_cuenta:
                badge_class = 'plan-a-badge' if cuenta_filtro == 'Plan A' else 'plan-b-badge'
                st.markdown(f'<span class="{badge_class}">{cuenta_filtro}</span>', unsafe_allow_html=True)
                
                for idx, pos in pos_cuenta:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
                        
                        with col1:
                            st.markdown(f"**{pos['ticker']}**")
                            st.caption(f"Costo: ${pos['costo_promedio']:.2f}")
                        
                        with col2:
                            precio_anterior = pos.get('precio_actual', pos['costo_promedio'])
                            nuevo_precio = st.number_input(
                                "Precio actual $",
                                value=float(precio_anterior),
                                format="%.2f",
                                key=f"precio_{idx}",
                                label_visibility="collapsed"
                            )
                        
                        with col3:
                            pyg, pyg_pct = calcular_pyg_posicion({
                                'shares': pos['shares'],
                                'costo_promedio': pos['costo_promedio'],
                                'precio_actual': nuevo_precio
                            })
                            color = "🟢" if pyg >= 0 else "🔴"
                            st.markdown(f"{color} **${pyg:+.2f}** ({pyg_pct:+.1f}%)")
                        
                        with col4:
                            tiempo, color_t = tiempo_desde_actualizacion(pos.get('ultima_actualizacion_precio'))
                            st.caption(f"⏱️ {tiempo}")
                        
                        with col5:
                            if st.button("💾 Guardar", key=f"save_{idx}"):
                                st.session_state.posiciones[idx]['precio_actual'] = nuevo_precio
                                st.session_state.posiciones[idx]['ultima_actualizacion_precio'] = datetime.now().isoformat()
                                st.success("✅")
                                st.rerun()
                        
                        st.markdown("---")
        
        # Botón actualizar TODO
        st.markdown("### 🚀 Actualización masiva")
        if st.button("💾 Guardar TODOS los precios de arriba", type="primary"):
            for idx, pos in enumerate(st.session_state.posiciones):
                nuevo_precio = st.session_state.get(f"precio_{idx}")
                if nuevo_precio is not None:
                    st.session_state.posiciones[idx]['precio_actual'] = nuevo_precio
                    st.session_state.posiciones[idx]['ultima_actualizacion_precio'] = datetime.now().isoformat()
            st.success("✅ Todos los precios actualizados con timestamp")
            st.balloons()
            st.rerun()

# ============ PÁGINA: ÓRDENES ACTIVAS ============
elif pagina == "📋 Órdenes Activas":
    st.title("📋 Órdenes GTC Activas")
    
    tab1, tab2 = st.tabs(["➕ Agregar Orden", "📋 Ver Órdenes"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            ticker_o = st.text_input("Ticker", "", placeholder="AVGO").upper()
            tipo = st.selectbox("Tipo", ["BUY", "SELL"])
            precio = st.number_input("Precio LIMIT ($)", 0.0, format="%.2f")
        with col2:
            cantidad = st.number_input("Cantidad / Amount", 0.0, format="%.4f")
            cuenta_o = st.selectbox("Cuenta", ["Plan A", "Plan B"], key="cuenta_orden")
            precio_actual_o = st.number_input("Precio actual mercado ($)", 0.0, format="%.2f", key="precio_act_o")
        
        if st.button("➕ Agregar orden", type="primary"):
            if ticker_o and precio > 0:
                nueva_orden = {
                    'ticker': ticker_o,
                    'tipo': tipo,
                    'precio_limit': precio,
                    'cantidad': cantidad,
                    'cuenta': cuenta_o,
                    'precio_actual': precio_actual_o,
                    'fecha': datetime.now().strftime('%Y-%m-%d'),
                    'ultima_actualizacion': datetime.now().isoformat()
                }
                st.session_state.ordenes.append(nueva_orden)
                st.success(f"✅ Orden {tipo} {ticker_o} @ ${precio} agregada")
                st.rerun()
    
    with tab2:
        if st.session_state.ordenes:
            data = []
            for i, o in enumerate(st.session_state.ordenes):
                if o['precio_actual'] > 0:
                    if o['tipo'] == 'BUY':
                        distancia = ((o['precio_actual'] - o['precio_limit']) / o['precio_actual']) * 100
                        dist_text = f"-{distancia:.1f}%" if distancia > 0 else f"+{abs(distancia):.1f}%"
                    else:
                        distancia = ((o['precio_limit'] - o['precio_actual']) / o['precio_actual']) * 100
                        dist_text = f"+{distancia:.1f}%" if distancia > 0 else f"-{abs(distancia):.1f}%"
                else:
                    dist_text = "N/A"
                
                data.append({
                    '#': i,
                    'Ticker': o['ticker'],
                    'Tipo': o['tipo'],
                    'Precio Limit': f"${o['precio_limit']:.2f}",
                    'Precio Actual': f"${o['precio_actual']:.2f}",
                    'Distancia': dist_text,
                    'Cuenta': o['cuenta']
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            
            with st.expander("🗑️ Eliminar orden"):
                idx_el_o = st.number_input("Índice #", 0,
                                           len(st.session_state.ordenes)-1 if st.session_state.ordenes else 0)
                if st.button("Confirmar eliminar"):
                    st.session_state.ordenes.pop(idx_el_o)
                    st.rerun()
        else:
            st.info("No tienes órdenes activas")

# ============ PÁGINA: ANÁLISIS GLOBALDATA ============
elif pagina == "🔍 Análisis GlobalData":
    st.title("🔍 Análisis GlobalData")
    st.caption("Mete los datos de GlobalData y obtén análisis Buffett-Graham automático")
    
    tab1, tab2 = st.tabs(["➕ Nuevo Análisis", "📊 Análisis Guardados"])
    
    with tab1:
        ticker_g = st.text_input("Ticker", "", placeholder="MSFT").upper()
        
        st.markdown("### 📊 Datos Financials (Statements)")
        col1, col2, col3 = st.columns(3)
        with col1:
            revenue_actual = st.number_input("Revenue 2026 ($M)", 0.0, format="%.0f")
            revenue_anterior = st.number_input("Revenue 2025 ($M)", 0.0, format="%.0f")
        with col2:
            net_income = st.number_input("Net Income 2026 ($M)", 0.0, format="%.0f")
            eps_actual = st.number_input("EPS 2026 ($)", 0.0, format="%.2f")
        with col3:
            eps_anterior = st.number_input("EPS 2025 ($)", 0.0, format="%.2f")
            cash_ops = st.number_input("Cash from Operations ($M)", 0.0, format="%.0f")
        
        st.markdown("### 📈 Datos Ratios")
        col1, col2, col3 = st.columns(3)
        with col1:
            op_margin = st.number_input("Operating Margin (%)", 0.0, format="%.1f")
            net_margin = st.number_input("Net Margin (%)", 0.0, format="%.1f")
        with col2:
            roe = st.number_input("ROE (%)", 0.0, format="%.1f")
            roa = st.number_input("ROA (%)", 0.0, format="%.1f")
        with col3:
            debt_eq = st.number_input("Debt/Equity", 0.0, format="%.2f")
            precio_actual_g = st.number_input("Precio actual ($)", 0.0, format="%.2f")
        
        if st.button("🔍 Analizar", type="primary"):
            if ticker_g:
                rev_growth = ((revenue_actual - revenue_anterior) / revenue_anterior * 100) if revenue_anterior > 0 else 0
                eps_growth = ((eps_actual - eps_anterior) / eps_anterior * 100) if eps_anterior > 0 else 0
                
                data = {
                    'ticker': ticker_g, 'revenue': revenue_actual,
                    'revenue_growth': rev_growth, 'net_income': net_income,
                    'eps': eps_actual, 'eps_growth': eps_growth,
                    'operating_margin': op_margin, 'net_margin': net_margin,
                    'roe': roe, 'roa': roa, 'debt_to_equity': debt_eq,
                    'cash_from_operations': cash_ops, 'precio_actual': precio_actual_g,
                    'fecha_analisis': datetime.now().strftime('%Y-%m-%d')
                }
                
                analisis = analizar_buffett_graham(data)
                data['analisis'] = analisis
                st.session_state.analisis_globaldata[ticker_g] = data
                
                st.markdown("---")
                st.markdown(f"## {analisis['emoji']} {ticker_g} - Puntaje: {analisis['puntaje']}/100")
                st.markdown(f"### Decisión: **{analisis['decision']}**")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### ✅ Puntos Positivos")
                    for p in analisis['positivas']:
                        st.markdown(f"- {p}")
                with col2:
                    st.markdown("#### ⚠️ Puntos Negativos")
                    if analisis['negativas']:
                        for n in analisis['negativas']:
                            st.markdown(f"- {n}")
                    else:
                        st.success("Sin red flags!")
                
                st.success(f"✅ Análisis de {ticker_g} guardado")
    
    with tab2:
        if st.session_state.analisis_globaldata:
            for ticker, data in st.session_state.analisis_globaldata.items():
                an = data['analisis']
                with st.expander(f"{an['emoji']} {ticker} - {an['decision']} ({an['puntaje']}/100)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Revenue Growth", f"{data['revenue_growth']:.1f}%")
                        st.metric("Operating Margin", f"{data['operating_margin']:.1f}%")
                        st.metric("ROE", f"{data['roe']:.1f}%")
                    with col2:
                        st.metric("EPS Growth", f"{data['eps_growth']:.1f}%")
                        st.metric("Debt/Equity", f"{data['debt_to_equity']:.2f}")
                        st.metric("Net Income", f"${data['net_income']:,.0f}M")
                    
                    st.markdown("**Positivos:**")
                    for p in an['positivas']:
                        st.markdown(f"- {p}")
                    if an['negativas']:
                        st.markdown("**Negativos:**")
                        for n in an['negativas']:
                            st.markdown(f"- {n}")
        else:
            st.info("No tienes análisis guardados aún")

# ============ PÁGINA: GENERAR REPORTE ============
elif pagina == "📄 Generar Reporte":
    st.title("📄 Generar Reporte Ejecutivo")
    
    st.markdown("""
    Genera un reporte completo con todos tus datos para:
    - 📊 Ver tu estado consolidado
    - 📤 Compartir con asesor
    - 💾 Archivo histórico
    - 🤖 Mandarme a mí para análisis
    """)
    
    formato = st.radio("Formato", ["📄 PDF Ejecutivo", "📊 JSON (para Claude)", "📋 Texto para WhatsApp"])
    
    if st.button("🚀 Generar reporte", type="primary"):
        pos_a = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan A']
        pos_b = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan B']
        valor_a = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_a) + st.session_state.cash_a
        valor_b = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_b) + st.session_state.cash_b
        
        if formato == "📄 PDF Ejecutivo":
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib.units import inch
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib import colors
                
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                styles = getSampleStyleSheet()
                elements = []
                
                elements.append(Paragraph(f"<b>Reporte Bolsa Buffett-Graham</b>", styles['Title']))
                elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
                elements.append(Spacer(1, 0.3*inch))
                
                elements.append(Paragraph("<b>RESUMEN EJECUTIVO</b>", styles['Heading2']))
                resumen_data = [
                    ['Métrica', 'Plan A', 'Plan B', 'Total'],
                    ['Cartera', f"${valor_a:,.2f}", f"${valor_b:,.2f}", f"${valor_a+valor_b:,.2f}"],
                    ['Cash', f"${st.session_state.cash_a:.2f}", f"${st.session_state.cash_b:.2f}",
                     f"${st.session_state.cash_a+st.session_state.cash_b:.2f}"],
                    ['PyG Realizada', f"${st.session_state.pyg_realizada_a:.2f}",
                     f"${st.session_state.pyg_realizada_b:.2f}",
                     f"${st.session_state.pyg_realizada_a+st.session_state.pyg_realizada_b:.2f}"],
                ]
                t = Table(resumen_data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2d5a3d')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 0.3*inch))
                
                if st.session_state.posiciones:
                    elements.append(Paragraph("<b>POSICIONES</b>", styles['Heading2']))
                    pos_data = [['Ticker', 'Cuenta', 'Shares', 'Costo', 'Actual', 'PyG']]
                    for p in st.session_state.posiciones:
                        pyg, _ = calcular_pyg_posicion(p)
                        pos_data.append([p['ticker'], p['cuenta'], f"{p['shares']:.4f}",
                                        f"${p['costo_promedio']:.2f}",
                                        f"${p.get('precio_actual', 0):.2f}",
                                        f"${pyg:+.2f}"])
                    t2 = Table(pos_data)
                    t2.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2a4a7a')),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                        ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ]))
                    elements.append(t2)
                
                doc.build(elements)
                buffer.seek(0)
                
                st.download_button(
                    "📥 Descargar PDF",
                    data=buffer,
                    file_name=f"reporte_bolsa_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )
                st.success("✅ PDF generado")
            except ImportError:
                st.warning("Instala reportlab: pip install reportlab")
        
        elif formato == "📊 JSON (para Claude)":
            reporte = {
                'fecha': datetime.now().isoformat(),
                'resumen': {
                    'inversion_inicial_a': st.session_state.inversion_inicial_a,
                    'inversion_inicial_b': st.session_state.inversion_inicial_b,
                    'cash_a': st.session_state.cash_a,
                    'cash_b': st.session_state.cash_b,
                    'pyg_realizada_a': st.session_state.pyg_realizada_a,
                    'pyg_realizada_b': st.session_state.pyg_realizada_b,
                },
                'posiciones': st.session_state.posiciones,
                'ordenes': st.session_state.ordenes,
                'analisis_globaldata': {k: v for k, v in st.session_state.analisis_globaldata.items()}
            }
            
            json_str = json.dumps(reporte, indent=2, ensure_ascii=False)
            st.code(json_str, language='json')
            st.download_button(
                "📥 Descargar JSON",
                data=json_str,
                file_name=f"bolsa_data_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        
        else:  # WhatsApp
            texto = f"""📊 *BOLSA - {datetime.now().strftime('%d/%m/%Y')}*

💼 *Plan A*
- Cartera: ${valor_a:,.2f}
- Cash: ${st.session_state.cash_a:.2f}
- PyG Real: ${st.session_state.pyg_realizada_a:.2f}

🚀 *Plan B*
- Cartera: ${valor_b:,.2f}
- Cash: ${st.session_state.cash_b:.2f}

📋 *Posiciones*: {len(st.session_state.posiciones)}
🎯 *Órdenes activas*: {len(st.session_state.ordenes)}

💰 *Total patrimonio*: ${valor_a+valor_b:,.2f}
"""
            st.text_area("Copiar y pegar en WhatsApp:", texto, height=300)

# ============ PÁGINA: CONFIGURACIÓN ============
elif pagina == "⚙️ Configuración":
    st.title("⚙️ Configuración")
    
    st.subheader("💰 Inversión Inicial")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.inversion_inicial_a = st.number_input(
            "Inversión Inicial Plan A ($)",
            value=st.session_state.inversion_inicial_a, format="%.2f")
    with col2:
        st.session_state.inversion_inicial_b = st.number_input(
            "Inversión Inicial Plan B ($)",
            value=st.session_state.inversion_inicial_b, format="%.2f")
    
    st.subheader("💵 Cash Actual")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.cash_a = st.number_input(
            "Cash Plan A ($)",
            value=st.session_state.cash_a, format="%.2f")
    with col2:
        st.session_state.cash_b = st.number_input(
            "Cash Plan B ($)",
            value=st.session_state.cash_b, format="%.2f")
    
    st.subheader("💵 PyG Realizada (histórica)")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.pyg_realizada_a = st.number_input(
            "PyG Realizada Plan A ($)",
            value=st.session_state.pyg_realizada_a, format="%.2f")
    with col2:
        st.session_state.pyg_realizada_b = st.number_input(
            "PyG Realizada Plan B ($)",
            value=st.session_state.pyg_realizada_b, format="%.2f")
    
    st.markdown("---")
    st.subheader("💾 Backup / Restore")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Exportar TODO (backup)"):
            backup = {
                'posiciones': st.session_state.posiciones,
                'ordenes': st.session_state.ordenes,
                'analisis_globaldata': st.session_state.analisis_globaldata,
                'config': {
                    'inversion_inicial_a': st.session_state.inversion_inicial_a,
                    'inversion_inicial_b': st.session_state.inversion_inicial_b,
                    'cash_a': st.session_state.cash_a,
                    'cash_b': st.session_state.cash_b,
                    'pyg_realizada_a': st.session_state.pyg_realizada_a,
                    'pyg_realizada_b': st.session_state.pyg_realizada_b,
                }
            }
            st.download_button(
                "📥 Descargar backup",
                data=json.dumps(backup, indent=2, ensure_ascii=False),
                file_name=f"backup_bolsa_{datetime.now().strftime('%Y%m%d')}.json"
            )
    
    with col2:
        uploaded = st.file_uploader("📂 Restaurar backup", type=['json'])
        if uploaded is not None:
            try:
                backup = json.load(uploaded)
                st.session_state.posiciones = backup.get('posiciones', [])
                st.session_state.ordenes = backup.get('ordenes', [])
                st.session_state.analisis_globaldata = backup.get('analisis_globaldata', {})
                config = backup.get('config', {})
                for k, v in config.items():
                    setattr(st.session_state, k, v)
                st.success("✅ Backup restaurado")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
