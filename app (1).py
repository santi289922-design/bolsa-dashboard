"""
Dashboard Bolsa Buffett-Graham - VERSIÓN 4.1
Mejoras v4.1:
- Yahoo Finance automático
- Alertas inteligentes
- Gráficas históricas por acción
- Carga PDF GlobalData
- Guardado optimizado anti-cuota
- NOTICIAS financieras + crypto + Colombia
- TRM USD/COP + EUR/COP con histórico interactivo

Autor: Para David Lopez - Plan A + Plan B
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf
import time
import re
import feedparser

st.set_page_config(
    page_title="Bolsa B-G v4.1",
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
    .plan-a-badge { background: #2d5a3d; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .plan-b-badge { background: #2a4a7a; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
    .alert-urgent { background: #ffe6e6; border-left: 4px solid #c0392b; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .alert-warning { background: #fff8e1; border-left: 4px solid #f39c12; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .alert-info { background: #e3f2fd; border-left: 4px solid #2196f3; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .alert-success { background: #e8f5e9; border-left: 4px solid #27ae60; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .news-item { background: #f8f9fa; border-left: 3px solid #2a4a7a; padding: 10px; margin: 6px 0; border-radius: 4px; }
    .news-item a { color: #1a4a2d; font-weight: 600; text-decoration: none; }
    .news-source { font-size: 11px; color: #6c757d; font-style: italic; }
    .trm-card { background: linear-gradient(135deg, #fff 0%, #f0f0f0 100%); border: 2px solid #2d5a3d; padding: 15px; border-radius: 8px; text-align: center; }
    .trm-value { font-size: 24px; font-weight: bold; color: #1a4a2d; }
    .trm-change-up { color: #27ae60; font-weight: bold; }
    .trm-change-down { color: #c0392b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ============ GOOGLE SHEETS ============
@st.cache_resource
def conectar_google_sheets():
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(credentials)
        return client.open_by_key(st.secrets["sheet_id"])
    except Exception as e:
        st.error(f"❌ Google Sheets: {e}")
        return None

def cargar_datos():
    sheet = conectar_google_sheets()
    if sheet is None:
        return False
    try:
        ws = sheet.worksheet("posiciones")
        st.session_state.posiciones = []
        for r in ws.get_all_records():
            if r.get('ticker'):
                st.session_state.posiciones.append({
                    'ticker': str(r['ticker']).upper(),
                    'shares': float(r.get('shares', 0) or 0),
                    'costo_promedio': float(r.get('costo_promedio', 0) or 0),
                    'precio_actual': float(r.get('precio_actual', 0) or 0),
                    'cuenta': str(r.get('cuenta', 'Plan A')),
                    'sector': str(r.get('sector', 'Otro')),
                    'fecha_compra': str(r.get('fecha_compra', '')),
                    'ultima_actualizacion_precio': str(r.get('ultima_actualizacion_precio', '') or '')
                })
        
        ws = sheet.worksheet("ordenes")
        st.session_state.ordenes = []
        for r in ws.get_all_records():
            if r.get('ticker'):
                st.session_state.ordenes.append({
                    'ticker': str(r['ticker']).upper(),
                    'tipo': str(r.get('tipo', 'BUY')),
                    'precio_limit': float(r.get('precio_limit', 0) or 0),
                    'cantidad': float(r.get('cantidad', 0) or 0),
                    'cuenta': str(r.get('cuenta', 'Plan A')),
                    'precio_actual': float(r.get('precio_actual', 0) or 0),
                    'fecha': str(r.get('fecha', ''))
                })
        
        ws = sheet.worksheet("analisis")
        st.session_state.analisis_globaldata = {}
        for r in ws.get_all_records():
            if r.get('ticker'):
                t = str(r['ticker']).upper()
                st.session_state.analisis_globaldata[t] = {
                    'ticker': t,
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
        
        ws = sheet.worksheet("config")
        for r in ws.get_all_records():
            if r.get('parametro'):
                try:
                    setattr(st.session_state, str(r['parametro']), float(r.get('valor', 0) or 0))
                except:
                    pass
        return True
    except Exception as e:
        st.error(f"❌ Cargando: {e}")
        return False

def guardar_todo():
    sheet = conectar_google_sheets()
    if sheet is None:
        return False
    try:
        ws = sheet.worksheet("posiciones")
        ws.clear()
        rows = [['ticker', 'shares', 'costo_promedio', 'precio_actual',
                 'cuenta', 'sector', 'fecha_compra', 'ultima_actualizacion_precio']]
        for p in st.session_state.posiciones:
            rows.append([p.get('ticker', ''), p.get('shares', 0), p.get('costo_promedio', 0),
                        p.get('precio_actual', 0), p.get('cuenta', ''), p.get('sector', ''),
                        p.get('fecha_compra', ''), p.get('ultima_actualizacion_precio', '') or ''])
        ws.update('A1', rows)
        time.sleep(1)
        
        ws = sheet.worksheet("ordenes")
        ws.clear()
        rows = [['ticker', 'tipo', 'precio_limit', 'cantidad', 'cuenta', 'precio_actual', 'fecha']]
        for o in st.session_state.ordenes:
            rows.append([o.get('ticker', ''), o.get('tipo', ''), o.get('precio_limit', 0),
                        o.get('cantidad', 0), o.get('cuenta', ''), o.get('precio_actual', 0),
                        o.get('fecha', '')])
        ws.update('A1', rows)
        time.sleep(1)
        
        ws = sheet.worksheet("analisis")
        ws.clear()
        rows = [['ticker', 'revenue', 'revenue_growth', 'net_income', 'eps', 'eps_growth',
                 'operating_margin', 'roe', 'debt_to_equity', 'cash_from_operations',
                 'precio_actual', 'puntaje', 'decision', 'fecha_analisis']]
        for t, d in st.session_state.analisis_globaldata.items():
            an = d.get('analisis', {})
            rows.append([t, d.get('revenue', 0), d.get('revenue_growth', 0),
                        d.get('net_income', 0), d.get('eps', 0), d.get('eps_growth', 0),
                        d.get('operating_margin', 0), d.get('roe', 0), d.get('debt_to_equity', 0),
                        d.get('cash_from_operations', 0), d.get('precio_actual', 0),
                        an.get('puntaje', d.get('puntaje', 0)),
                        an.get('decision', d.get('decision', '')),
                        d.get('fecha_analisis', '')])
        ws.update('A1', rows)
        time.sleep(1)
        
        ws = sheet.worksheet("config")
        ws.clear()
        rows = [['parametro', 'valor']]
        for p in ['inversion_inicial_a', 'inversion_inicial_b', 'cash_a',
                  'cash_b', 'pyg_realizada_a', 'pyg_realizada_b']:
            rows.append([p, getattr(st.session_state, p, 0)])
        ws.update('A1', rows)
        
        st.session_state.cambios_pendientes = False
        return True
    except Exception as e:
        st.error(f"❌ Guardando: {e}")
        return False

# ============ YAHOO FINANCE ============
@st.cache_data(ttl=300)
def obtener_precio_yahoo(ticker):
    try:
        tm = {'BTC': 'BTC-USD', 'ETH': 'ETH-USD'}
        yft = tm.get(ticker, ticker)
        info = yf.Ticker(yft).history(period="1d")
        return float(info['Close'].iloc[-1]) if not info.empty else None
    except:
        return None

@st.cache_data(ttl=3600)
def obtener_historico_yahoo(ticker, periodo='3mo'):
    try:
        tm = {'BTC': 'BTC-USD', 'ETH': 'ETH-USD'}
        yft = tm.get(ticker, ticker)
        return yf.Ticker(yft).history(period=periodo)
    except:
        return None

def actualizar_todos_precios_yahoo():
    act, fail = 0, []
    with st.spinner("🔄 Yahoo Finance..."):
        for i, pos in enumerate(st.session_state.posiciones):
            p = obtener_precio_yahoo(pos['ticker'])
            if p is not None:
                st.session_state.posiciones[i]['precio_actual'] = round(p, 2)
                st.session_state.posiciones[i]['ultima_actualizacion_precio'] = datetime.now().isoformat()
                act += 1
            else:
                fail.append(pos['ticker'])
    return act, fail

# ============ TRM DIVISAS ============
@st.cache_data(ttl=600)
def obtener_trm(par='USDCOP=X', periodo='1mo'):
    try:
        return yf.Ticker(par).history(period=periodo)
    except:
        return None

@st.cache_data(ttl=600)
def obtener_trm_actual():
    try:
        usd = yf.Ticker('USDCOP=X').history(period='5d')
        eur = yf.Ticker('EURCOP=X').history(period='5d')
        r = {}
        if not usd.empty and len(usd) >= 2:
            r['usd_actual'] = float(usd['Close'].iloc[-1])
            r['usd_anterior'] = float(usd['Close'].iloc[-2])
            r['usd_change'] = r['usd_actual'] - r['usd_anterior']
            r['usd_change_pct'] = (r['usd_change'] / r['usd_anterior']) * 100
        if not eur.empty and len(eur) >= 2:
            r['eur_actual'] = float(eur['Close'].iloc[-1])
            r['eur_anterior'] = float(eur['Close'].iloc[-2])
            r['eur_change'] = r['eur_actual'] - r['eur_anterior']
            r['eur_change_pct'] = (r['eur_change'] / r['eur_anterior']) * 100
        return r
    except:
        return {}

# ============ NOTICIAS ============
@st.cache_data(ttl=1800)
def obtener_noticias(categoria='mercados'):
    feeds = {
        'mercados': [
            ('Yahoo Finance', 'https://finance.yahoo.com/news/rssindex'),
            ('MarketWatch', 'https://feeds.marketwatch.com/marketwatch/topstories/'),
        ],
        'crypto': [
            ('CoinDesk', 'https://www.coindesk.com/arc/outboundfeeds/rss/'),
            ('Yahoo Crypto', 'https://finance.yahoo.com/news/rssindex'),
        ],
        'colombia': [
            ('Portafolio', 'https://www.portafolio.co/arc/outboundfeeds/rss/?outputType=xml'),
            ('La República', 'https://www.larepublica.co/rss'),
        ]
    }
    noticias = []
    for fuente, url in feeds.get(categoria, feeds['mercados']):
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                noticias.append({
                    'titulo': entry.get('title', 'Sin título'),
                    'link': entry.get('link', '#'),
                    'fuente': fuente,
                    'fecha': entry.get('published', '')
                })
        except:
            continue
    return noticias[:10]

# ============ ANÁLISIS ============
def analizar_buffett_graham(data):
    puntaje, pos, neg = 0, [], []
    if data.get('net_income', 0) > 0:
        puntaje += 15
        pos.append(f"✅ Genera ganancias (${data['net_income']:,.0f}M)")
    else:
        neg.append("❌ No genera ganancias")
    g = data.get('revenue_growth', 0)
    if g > 15:
        puntaje += 20; pos.append(f"🚀 Crecimiento alto ({g:.1f}%)")
    elif g > 8:
        puntaje += 10; pos.append(f"✅ Crecimiento sólido ({g:.1f}%)")
    elif g < 0:
        neg.append(f"❌ Crecimiento negativo")
    m = data.get('operating_margin', 0)
    if m > 25:
        puntaje += 15; pos.append(f"🏆 Márgenes excelentes ({m:.1f}%)")
    elif m > 15:
        puntaje += 10
    de = data.get('debt_to_equity', 1)
    if de < 0.3:
        puntaje += 15; pos.append(f"💪 Deuda baja ({de:.2f})")
    elif de < 0.6:
        puntaje += 8
    elif de > 1.5:
        neg.append(f"⚠️ Deuda alta")
    roe = data.get('roe', 0)
    if roe > 20:
        puntaje += 15; pos.append(f"🏆 ROE excelente ({roe:.1f}%)")
    elif roe > 12:
        puntaje += 10
    epsg = data.get('eps_growth', 0)
    if epsg > 15:
        puntaje += 10; pos.append(f"🚀 EPS creciendo {epsg:.1f}%")
    elif epsg > 5:
        puntaje += 5
    elif epsg < 0:
        neg.append(f"❌ EPS decreciendo")
    if data.get('cash_from_operations', 0) > 0:
        puntaje += 10; pos.append(f"✅ Cash flow positivo")
    if puntaje >= 75:
        d, e = "COMPRAR / MANTENER FUERTE", "🟢"
    elif puntaje >= 50:
        d, e = "MANTENER", "🟡"
    elif puntaje >= 30:
        d, e = "VIGILAR / REDUCIR", "🟠"
    else:
        d, e = "EVITAR / VENDER", "🔴"
    return {'puntaje': puntaje, 'decision': d, 'emoji': e, 'positivas': pos, 'negativas': neg}

def calcular_pyg_posicion(p):
    ct = p['shares'] * p['costo_promedio']
    va = p['shares'] * p.get('precio_actual', p['costo_promedio'])
    pyg = va - ct
    pct = (pyg / ct) * 100 if ct > 0 else 0
    return pyg, pct

def generar_alertas():
    a = {'urgentes': [], 'warnings': [], 'info': [], 'success': []}
    for pos in st.session_state.posiciones:
        pyg, pct = calcular_pyg_posicion(pos)
        if pct > 50:
            a['success'].append(f"🚀 {pos['ticker']} ({pos['cuenta']}): +{pct:.1f}% — CONSIDERAR VENTA PARCIAL")
        elif pct > 25:
            a['info'].append(f"📈 {pos['ticker']} ({pos['cuenta']}): +{pct:.1f}% — ganancias")
        if pct < -15:
            a['urgentes'].append(f"🔴 {pos['ticker']} ({pos['cuenta']}): {pct:.1f}% — REVISAR")
        elif pct < -8:
            a['warnings'].append(f"🟠 {pos['ticker']} ({pos['cuenta']}): {pct:.1f}% — vigilar")
    for o in st.session_state.ordenes:
        if o['precio_actual'] > 0:
            dist = abs(o['precio_actual'] - o['precio_limit']) / o['precio_actual'] * 100
            if dist < 2:
                t = "comprar" if o['tipo'] == 'BUY' else "vender"
                a['urgentes'].append(f"🎯 {o['ticker']} MUY CERCA de {t} ${o['precio_limit']} ({dist:.1f}%)")
            elif dist < 5:
                t = "comprar" if o['tipo'] == 'BUY' else "vender"
                a['warnings'].append(f"⏰ {o['ticker']} cerca de {t} ${o['precio_limit']} ({dist:.1f}%)")
    return a

def extraer_datos_pdf(pdf_file):
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_file)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() + "\n"
        datos = {}
        patterns = {
            'revenue': r'(?:Total Revenue|Revenue)[\s\S]{0,100}?([\d,]+\.?\d*)',
            'net_income': r'Net Income[\s\S]{0,100}?([\d,]+\.?\d*)',
            'eps': r'(?:Diluted.*?EPS|EPS)[\s\S]{0,100}?([\d]+\.\d+)',
            'operating_margin': r'Operating Margin[\s\S]{0,100}?([\d]+\.?\d*)',
            'roe': r'(?:ROE|Return on Equity)[\s\S]{0,100}?([\d]+\.?\d*)',
            'debt_to_equity': r'(?:Debt.*?Equity|D/E)[\s\S]{0,100}?([\d]+\.?\d*)',
        }
        for k, pat in patterns.items():
            m = re.search(pat, texto, re.IGNORECASE)
            if m:
                try:
                    datos[k] = float(m.group(1).replace(',', ''))
                except:
                    pass
        return datos, texto[:2000]
    except Exception as e:
        return {}, f"Error: {e}"

# ============ INIT ============
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False
if 'cambios_pendientes' not in st.session_state:
    st.session_state.cambios_pendientes = False
if 'posiciones' not in st.session_state:
    st.session_state.posiciones = []
if 'ordenes' not in st.session_state:
    st.session_state.ordenes = []
if 'analisis_globaldata' not in st.session_state:
    st.session_state.analisis_globaldata = {}
for k, v in [('inversion_inicial_a', 2500.0), ('inversion_inicial_b', 3000.0),
             ('cash_a', 793.34), ('cash_b', 2610.0),
             ('pyg_realizada_a', 42.73), ('pyg_realizada_b', 0.0)]:
    if k not in st.session_state:
        setattr(st.session_state, k, v)

if not st.session_state.datos_cargados:
    with st.spinner("🔄 Cargando..."):
        if cargar_datos():
            st.session_state.datos_cargados = True

# ============ SIDEBAR ============
st.sidebar.title("📊 Bolsa B-G v4.1")

if st.session_state.cambios_pendientes:
    st.sidebar.warning("⚠️ Cambios sin guardar")
    if st.sidebar.button("💾 GUARDAR TODO", type="primary"):
        with st.spinner("Guardando..."):
            if guardar_todo():
                st.sidebar.success("✅")
                st.rerun()
else:
    st.sidebar.success("✅ Sincronizado")

if st.sidebar.button("🔄 Recargar Sheets"):
    st.session_state.datos_cargados = False
    st.rerun()

if st.sidebar.button("🌐 Actualizar precios"):
    act, fail = actualizar_todos_precios_yahoo()
    st.sidebar.success(f"✅ {act}")
    st.session_state.cambios_pendientes = True
    st.rerun()

st.sidebar.markdown("---")

pagina = st.sidebar.radio("Navegación",
    ["🏠 Dashboard", "📰 Noticias", "💱 TRM Divisas", "🚨 Alertas",
     "💼 Mis Posiciones", "💱 Actualizar Precios", "📈 Gráficas Históricas",
     "📋 Órdenes Activas", "🔍 Análisis GlobalData", "📄 Subir PDF",
     "📥 Generar Reporte", "⚙️ Configuración"])

st.sidebar.markdown("---")
st.sidebar.caption(f"🕐 {datetime.now().strftime('%d/%m %H:%M')}")

# ============ DASHBOARD ============
if pagina == "🏠 Dashboard":
    st.markdown("""
    <div class="main-header">
        <h1>📊 Dashboard Bolsa Buffett-Graham v4.1</h1>
        <p>Yahoo + Alertas + Noticias + TRM | Sync Google Sheets</p>
    </div>
    """, unsafe_allow_html=True)
    
    pos_a = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan A']
    pos_b = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan B']
    valor_a = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_a) + st.session_state.cash_a
    valor_b = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_b) + st.session_state.cash_b
    valor_total = valor_a + valor_b
    pyg_a = sum(calcular_pyg_posicion(p)[0] for p in pos_a)
    pyg_b = sum(calcular_pyg_posicion(p)[0] for p in pos_b)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💼 Total", f"${valor_total:,.2f}", f"+${pyg_a + pyg_b:.2f}")
    col2.metric("🏆 Plan A", f"${valor_a:,.2f}", f"+${pyg_a:.2f}")
    col3.metric("🚀 Plan B", f"${valor_b:,.2f}", f"+${pyg_b:.2f}")
    ct = st.session_state.cash_a + st.session_state.cash_b
    col4.metric("💰 Cash", f"${ct:,.2f}", f"{(ct/valor_total*100):.1f}%" if valor_total > 0 else "0%")
    
    st.markdown("---")
    st.subheader("💱 Tasas de Cambio")
    trm = obtener_trm_actual()
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'usd_actual' in trm:
            col1.metric("🇺🇸 USD/COP", f"${trm['usd_actual']:,.2f}",
                       f"{trm['usd_change']:+.2f} ({trm['usd_change_pct']:+.2f}%)")
    with col2:
        if 'eur_actual' in trm:
            col2.metric("🇪🇺 EUR/COP", f"${trm['eur_actual']:,.2f}",
                       f"{trm['eur_change']:+.2f} ({trm['eur_change_pct']:+.2f}%)")
    with col3:
        if 'usd_actual' in trm:
            col3.metric("💰 Patrimonio COP", f"${valor_total * trm['usd_actual']:,.0f}")
    
    st.markdown("---")
    alertas = generar_alertas()
    ta = sum(len(v) for v in alertas.values())
    if ta > 0:
        with st.expander(f"🚨 {ta} alertas activas"):
            for a in alertas['urgentes'][:3]:
                st.markdown(f'<div class="alert-urgent">{a}</div>', unsafe_allow_html=True)
            for a in alertas['warnings'][:3]:
                st.markdown(f'<div class="alert-warning">{a}</div>', unsafe_allow_html=True)
    
    with st.expander("📰 Noticias del día"):
        noticias = obtener_noticias('mercados')
        for n in noticias[:5]:
            st.markdown(f"""
            <div class="news-item">
                <a href="{n['link']}" target="_blank">{n['titulo']}</a>
                <div class="news-source">📍 {n['fuente']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📈 Comparación Rendimiento")
    if st.session_state.posiciones:
        todos = [f"{p['ticker']} ({p['cuenta']})" for p in st.session_state.posiciones]
        col1, col2 = st.columns([3, 1])
        with col1:
            sel = st.multiselect("Acciones:", todos, default=todos)
        with col2:
            tipo = st.selectbox("Tipo", ["Barras", "Líneas"])
        if sel:
            data_c = []
            for pos in st.session_state.posiciones:
                lbl = f"{pos['ticker']} ({pos['cuenta']})"
                if lbl in sel:
                    pyg, pct = calcular_pyg_posicion(pos)
                    data_c.append({'Ticker': pos['ticker'], 'Cuenta': pos['cuenta'], 'Label': lbl,
                        'PyG $': pyg, 'PyG %': pct,
                        'Valor Actual': pos['shares'] * pos.get('precio_actual', pos['costo_promedio'])})
            df = pd.DataFrame(data_c)
            metrica = st.radio("Ver:", ["PyG %", "PyG $", "Valor Actual"], horizontal=True)
            if tipo == "Barras":
                fig = px.bar(df.sort_values(metrica, ascending=False),
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
                for c in ['Plan A', 'Plan B']:
                    df_c = df[df['Cuenta'] == c].sort_values(metrica)
                    if not df_c.empty:
                        fig.add_trace(go.Scatter(x=df_c['Ticker'], y=df_c[metrica],
                            mode='lines+markers', name=c,
                            line=dict(color='#2d5a3d' if c == 'Plan A' else '#2a4a7a', width=3)))
                fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Plan A")
        if pos_a:
            df = pd.DataFrame([{'Ticker': p['ticker'],
                'Valor': p['shares'] * p.get('precio_actual', p['costo_promedio'])} for p in pos_a])
            df.loc[len(df)] = ['Cash', st.session_state.cash_a]
            st.plotly_chart(px.pie(df, values='Valor', names='Ticker', hole=0.4), use_container_width=True)
    with col2:
        st.subheader("📊 Plan B")
        if pos_b:
            df = pd.DataFrame([{'Ticker': p['ticker'],
                'Valor': p['shares'] * p.get('precio_actual', p['costo_promedio'])} for p in pos_b])
            df.loc[len(df)] = ['Cash', st.session_state.cash_b]
            st.plotly_chart(px.pie(df, values='Valor', names='Ticker', hole=0.4), use_container_width=True)

# ============ NOTICIAS ============
elif pagina == "📰 Noticias":
    st.title("📰 Noticias Financieras")
    st.caption("Mercados USA + Crypto + Colombia")
    
    cat = st.radio("Categoría", ["📈 Mercados", "₿ Crypto", "🇨🇴 Colombia"], horizontal=True)
    cm = {"📈 Mercados": "mercados", "₿ Crypto": "crypto", "🇨🇴 Colombia": "colombia"}
    
    with st.spinner("Cargando..."):
        noticias = obtener_noticias(cm[cat])
    
    if noticias:
        st.caption(f"{len(noticias)} noticias (actualizadas cada 30 min)")
        for n in noticias:
            st.markdown(f"""
            <div class="news-item">
                <a href="{n['link']}" target="_blank">🔗 {n['titulo']}</a>
                <div class="news-source">📍 {n['fuente']} | {n['fecha'][:16] if n['fecha'] else ''}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Sin noticias disponibles. Intenta en unos minutos.")
    
    if st.button("🔄 Recargar"):
        st.cache_data.clear()
        st.rerun()

# ============ TRM ============
elif pagina == "💱 TRM Divisas":
    st.title("💱 Tasas de Cambio")
    st.caption("USD/COP + EUR/COP con histórico")
    
    trm = obtener_trm_actual()
    col1, col2 = st.columns(2)
    with col1:
        if 'usd_actual' in trm:
            st.markdown(f"""
            <div class="trm-card">
                <div style="font-size:14px; color:#666;">🇺🇸 USD/COP</div>
                <div class="trm-value">${trm['usd_actual']:,.2f}</div>
                <div class="{'trm-change-up' if trm['usd_change'] >= 0 else 'trm-change-down'}">
                    {trm['usd_change']:+.2f} ({trm['usd_change_pct']:+.2f}%)
                </div>
            </div>
            """, unsafe_allow_html=True)
    with col2:
        if 'eur_actual' in trm:
            st.markdown(f"""
            <div class="trm-card">
                <div style="font-size:14px; color:#666;">🇪🇺 EUR/COP</div>
                <div class="trm-value">${trm['eur_actual']:,.2f}</div>
                <div class="{'trm-change-up' if trm['eur_change'] >= 0 else 'trm-change-down'}">
                    {trm['eur_change']:+.2f} ({trm['eur_change_pct']:+.2f}%)
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📈 Histórico")
    col1, col2 = st.columns(2)
    with col1:
        par_sel = st.radio("Par:", ["USD/COP", "EUR/COP", "EUR/USD"], horizontal=True)
    with col2:
        periodo = st.radio("Período:",
            ["1 semana", "1 mes", "Año corrido", "1 año", "5 años"], horizontal=True)
    
    par_map = {"USD/COP": "USDCOP=X", "EUR/COP": "EURCOP=X", "EUR/USD": "EURUSD=X"}
    per_map = {"1 semana": "5d", "1 mes": "1mo", "Año corrido": "ytd",
               "1 año": "1y", "5 años": "5y"}
    
    with st.spinner(f"Cargando {par_sel}..."):
        hist = obtener_trm(par_map[par_sel], per_map[periodo])
    
    if hist is not None and not hist.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'],
            mode='lines', name=par_sel,
            line=dict(color='#2d5a3d', width=2),
            fill='tozeroy', fillcolor='rgba(45,90,61,0.1)'))
        fig.update_layout(height=500, hovermode='x unified',
            title=f"{par_sel} - {periodo}",
            yaxis_title="Precio", xaxis_title="Fecha")
        st.plotly_chart(fig, use_container_width=True)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Actual", f"${hist['Close'].iloc[-1]:,.2f}")
        col2.metric("Máximo", f"${hist['Close'].max():,.2f}")
        col3.metric("Mínimo", f"${hist['Close'].min():,.2f}")
        vol = ((hist['Close'].max() - hist['Close'].min()) / hist['Close'].min()) * 100
        col4.metric("Rango", f"{vol:.1f}%")
        
        # Conversor rápido
        st.markdown("---")
        st.subheader("💰 Conversor rápido")
        col1, col2, col3 = st.columns(3)
        with col1:
            monto = st.number_input("Monto", value=100.0, format="%.2f")
        with col2:
            if 'usd_actual' in trm and par_sel == "USD/COP":
                st.metric("USD → COP", f"${monto * trm['usd_actual']:,.0f}")
            elif 'eur_actual' in trm and par_sel == "EUR/COP":
                st.metric("EUR → COP", f"${monto * trm['eur_actual']:,.0f}")
        with col3:
            if 'usd_actual' in trm and par_sel == "USD/COP":
                st.metric("COP → USD", f"${monto / trm['usd_actual']:,.2f}")
            elif 'eur_actual' in trm and par_sel == "EUR/COP":
                st.metric("COP → EUR", f"${monto / trm['eur_actual']:,.2f}")
    else:
        st.error("No pude obtener el histórico")

# ============ ALERTAS ============
elif pagina == "🚨 Alertas":
    st.title("🚨 Alertas Inteligentes")
    alertas = generar_alertas()
    if alertas['urgentes']:
        st.subheader("🔴 Urgentes")
        for a in alertas['urgentes']:
            st.markdown(f'<div class="alert-urgent">{a}</div>', unsafe_allow_html=True)
    if alertas['success']:
        st.subheader("🟢 Oportunidades")
        for a in alertas['success']:
            st.markdown(f'<div class="alert-success">{a}</div>', unsafe_allow_html=True)
    if alertas['warnings']:
        st.subheader("🟡 Vigilar")
        for a in alertas['warnings']:
            st.markdown(f'<div class="alert-warning">{a}</div>', unsafe_allow_html=True)
    if alertas['info']:
        st.subheader("ℹ️ Info")
        for a in alertas['info']:
            st.markdown(f'<div class="alert-info">{a}</div>', unsafe_allow_html=True)
    if sum(len(v) for v in alertas.values()) == 0:
        st.success("✅ Todo tranquilo")

# ============ POSICIONES ============
elif pagina == "💼 Mis Posiciones":
    st.title("💼 Mis Posiciones")
    tab1, tab2 = st.tabs(["➕ Agregar", "📋 Ver"])
    with tab1:
        st.caption("💡 Yahoo obtiene precio automático")
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Ticker").upper()
            shares = st.number_input("Shares", 0.0, format="%.6f")
            costo = st.number_input("Costo promedio ($)", 0.0, format="%.2f")
        with col2:
            cuenta = st.selectbox("Cuenta", ["Plan A", "Plan B"])
            sector = st.selectbox("Sector", ["Tech", "Semis", "Consumer", "Financial",
                                              "Energy", "Oro", "Crypto", "ETF", "Otro"])
            fecha_c = st.date_input("Fecha compra", datetime.now())
        if st.button("➕ Agregar", type="primary"):
            if ticker and shares > 0 and costo > 0:
                pi = obtener_precio_yahoo(ticker) or costo
                st.session_state.posiciones.append({
                    'ticker': ticker, 'shares': shares, 'costo_promedio': costo,
                    'precio_actual': pi, 'cuenta': cuenta, 'sector': sector,
                    'fecha_compra': fecha_c.strftime('%Y-%m-%d'),
                    'ultima_actualizacion_precio': datetime.now().isoformat() if pi != costo else ''
                })
                st.session_state.cambios_pendientes = True
                st.success(f"✅ {ticker} (Yahoo: ${pi:.2f})")
                st.rerun()
    with tab2:
        if st.session_state.posiciones:
            for cf in ["Plan A", "Plan B"]:
                pos_c = [p for p in st.session_state.posiciones if p['cuenta'] == cf]
                if pos_c:
                    badge = 'plan-a-badge' if cf == 'Plan A' else 'plan-b-badge'
                    st.markdown(f'<span class="{badge}">{cf}</span>', unsafe_allow_html=True)
                    data = []
                    for i, p in enumerate(st.session_state.posiciones):
                        if p['cuenta'] != cf:
                            continue
                        pyg, pct = calcular_pyg_posicion(p)
                        data.append({'#': i, 'Ticker': p['ticker'], 'Shares': f"{p['shares']:.4f}",
                            'Costo': f"${p['costo_promedio']:.2f}",
                            'Actual': f"${p.get('precio_actual', 0):.2f}",
                            'PyG $': f"${pyg:+.2f}", 'PyG %': f"{pct:+.1f}%"})
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                    st.markdown("---")
            with st.expander("🗑️ Eliminar"):
                idx = st.number_input("Índice", 0, len(st.session_state.posiciones)-1)
                if st.button("Eliminar"):
                    st.session_state.posiciones.pop(idx)
                    st.session_state.cambios_pendientes = True
                    st.rerun()

# ============ ACTUALIZAR PRECIOS ============
elif pagina == "💱 Actualizar Precios":
    st.title("💱 Actualizar Precios")
    col1, col2 = st.columns([2, 1])
    with col2:
        if st.button("🌐 TODO Yahoo", type="primary"):
            act, fail = actualizar_todos_precios_yahoo()
            st.success(f"✅ {act}")
            st.session_state.cambios_pendientes = True
            st.rerun()
    st.markdown("---")
    if st.session_state.posiciones:
        for cf in ["Plan A", "Plan B"]:
            pos_c = [(i, p) for i, p in enumerate(st.session_state.posiciones) if p['cuenta'] == cf]
            if pos_c:
                badge = 'plan-a-badge' if cf == 'Plan A' else 'plan-b-badge'
                st.markdown(f'<span class="{badge}">{cf}</span>', unsafe_allow_html=True)
                for idx, pos in pos_c:
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    with col1:
                        st.markdown(f"**{pos['ticker']}**")
                        st.caption(f"Costo: ${pos['costo_promedio']:.2f}")
                    with col2:
                        nuevo = st.number_input("P",
                            value=float(pos.get('precio_actual', pos['costo_promedio'])),
                            format="%.2f", key=f"p_{idx}", label_visibility="collapsed")
                    with col3:
                        pyg, pct = calcular_pyg_posicion({'shares': pos['shares'],
                            'costo_promedio': pos['costo_promedio'], 'precio_actual': nuevo})
                        c = "🟢" if pyg >= 0 else "🔴"
                        st.markdown(f"{c} **${pyg:+.2f}** ({pct:+.1f}%)")
                    with col4:
                        if st.button("🌐", key=f"y_{idx}"):
                            p = obtener_precio_yahoo(pos['ticker'])
                            if p:
                                st.session_state.posiciones[idx]['precio_actual'] = round(p, 2)
                                st.session_state.posiciones[idx]['ultima_actualizacion_precio'] = datetime.now().isoformat()
                                st.session_state.cambios_pendientes = True
                                st.rerun()

# ============ GRÁFICAS HISTÓRICAS ============
elif pagina == "📈 Gráficas Históricas":
    st.title("📈 Gráficas Históricas")
    if not st.session_state.posiciones:
        st.info("Sin posiciones")
    else:
        tickers = list(set([p['ticker'] for p in st.session_state.posiciones]))
        col1, col2 = st.columns([2, 1])
        with col1:
            ts = st.selectbox("Acción", tickers)
        with col2:
            per = st.selectbox("Período", ["1mo", "3mo", "6mo", "1y", "2y"])
        if ts:
            with st.spinner(f"Cargando {ts}..."):
                hist = obtener_historico_yahoo(ts, per)
            if hist is not None and not hist.empty:
                pos_t = [p for p in st.session_state.posiciones if p['ticker'] == ts]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'],
                    mode='lines', name=ts, line=dict(color='#2a4a7a', width=2)))
                for p in pos_t:
                    fig.add_hline(y=p['costo_promedio'], line_dash="dash", line_color="#27ae60",
                                 annotation_text=f"Costo ({p['cuenta']}): ${p['costo_promedio']}")
                ph = hist['Close'].iloc[-1]
                fig.add_hline(y=ph, line_dash="dot", line_color="#c0392b",
                             annotation_text=f"HOY: ${ph:.2f}")
                fig.update_layout(height=500, hovermode='x unified', title=f"{ts} - {per}")
                st.plotly_chart(fig, use_container_width=True)
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Hoy", f"${ph:.2f}")
                col2.metric("Máx", f"${hist['Close'].max():.2f}")
                col3.metric("Mín", f"${hist['Close'].min():.2f}")
                vol = ((hist['Close'].max() - hist['Close'].min()) / hist['Close'].min()) * 100
                col4.metric("Rango", f"{vol:.1f}%")

# ============ ÓRDENES ============
elif pagina == "📋 Órdenes Activas":
    st.title("📋 Órdenes GTC")
    tab1, tab2 = st.tabs(["➕ Agregar", "📋 Ver"])
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            to = st.text_input("Ticker").upper()
            tipo = st.selectbox("Tipo", ["BUY", "SELL"])
            precio = st.number_input("Precio LIMIT", 0.0, format="%.2f")
        with col2:
            cant = st.number_input("Cantidad", 0.0, format="%.4f")
            co = st.selectbox("Cuenta", ["Plan A", "Plan B"], key="co")
            pa = st.number_input("Precio mercado", 0.0, format="%.2f", key="pm")
        if st.button("➕ Agregar", type="primary"):
            if to and precio > 0:
                pact = pa or obtener_precio_yahoo(to) or 0
                st.session_state.ordenes.append({
                    'ticker': to, 'tipo': tipo, 'precio_limit': precio,
                    'cantidad': cant, 'cuenta': co,
                    'precio_actual': pact, 'fecha': datetime.now().strftime('%Y-%m-%d')})
                st.session_state.cambios_pendientes = True
                st.success("✅")
                st.rerun()
    with tab2:
        if st.session_state.ordenes:
            data = []
            for i, o in enumerate(st.session_state.ordenes):
                data.append({'#': i, 'Ticker': o['ticker'], 'Tipo': o['tipo'],
                    'Limit': f"${o['precio_limit']:.2f}",
                    'Actual': f"${o['precio_actual']:.2f}", 'Cuenta': o['cuenta']})
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            with st.expander("🗑️ Eliminar"):
                idx = st.number_input("Índice", 0, len(st.session_state.ordenes)-1)
                if st.button("Eliminar"):
                    st.session_state.ordenes.pop(idx)
                    st.session_state.cambios_pendientes = True
                    st.rerun()

# ============ ANÁLISIS GLOBALDATA ============
elif pagina == "🔍 Análisis GlobalData":
    st.title("🔍 Análisis Manual")
    tg = st.text_input("Ticker").upper()
    col1, col2, col3 = st.columns(3)
    with col1:
        ra = st.number_input("Revenue 2026 ($M)", 0.0)
        rp = st.number_input("Revenue 2025 ($M)", 0.0)
    with col2:
        ni = st.number_input("Net Income ($M)", 0.0)
        ea = st.number_input("EPS 2026", 0.0, format="%.2f")
    with col3:
        ep = st.number_input("EPS 2025", 0.0, format="%.2f")
        cf = st.number_input("Cash Ops ($M)", 0.0)
    col1, col2, col3 = st.columns(3)
    with col1:
        om = st.number_input("Op Margin %", 0.0, format="%.1f")
    with col2:
        roe = st.number_input("ROE %", 0.0, format="%.1f")
    with col3:
        de = st.number_input("Debt/Equity", 0.0, format="%.2f")
    if st.button("🔍 Analizar", type="primary"):
        if tg:
            rg = ((ra - rp) / rp * 100) if rp > 0 else 0
            eg = ((ea - ep) / ep * 100) if ep > 0 else 0
            data = {'ticker': tg, 'revenue': ra, 'revenue_growth': rg,
                'net_income': ni, 'eps': ea, 'eps_growth': eg,
                'operating_margin': om, 'roe': roe, 'debt_to_equity': de,
                'cash_from_operations': cf,
                'precio_actual': obtener_precio_yahoo(tg) or 0,
                'fecha_analisis': datetime.now().strftime('%Y-%m-%d')}
            an = analizar_buffett_graham(data)
            data['analisis'] = an
            data['puntaje'] = an['puntaje']
            data['decision'] = an['decision']
            st.session_state.analisis_globaldata[tg] = data
            st.session_state.cambios_pendientes = True
            st.markdown(f"## {an['emoji']} {tg} - {an['puntaje']}/100")
            st.markdown(f"### **{an['decision']}**")
            col1, col2 = st.columns(2)
            with col1:
                for p in an['positivas']:
                    st.markdown(f"- {p}")
            with col2:
                for n in an['negativas']:
                    st.markdown(f"- {n}")

# ============ SUBIR PDF ============
elif pagina == "📄 Subir PDF":
    st.title("📄 Subir PDF GlobalData")
    tp = st.text_input("Ticker").upper()
    pf = st.file_uploader("PDF", type=['pdf'])
    if pf and tp:
        if st.button("🔍 Extraer"):
            with st.spinner("Analizando..."):
                datos, _ = extraer_datos_pdf(pf)
            if datos:
                st.success(f"✅ {len(datos)} campos")
                st.json(datos)
                col1, col2 = st.columns(2)
                with col1:
                    rev = st.number_input("Revenue", value=float(datos.get('revenue', 0)))
                    ni = st.number_input("Net Income", value=float(datos.get('net_income', 0)))
                    eps = st.number_input("EPS", value=float(datos.get('eps', 0)), format="%.2f")
                with col2:
                    om = st.number_input("Op Margin", value=float(datos.get('operating_margin', 0)))
                    roe = st.number_input("ROE", value=float(datos.get('roe', 0)))
                    de = st.number_input("D/E", value=float(datos.get('debt_to_equity', 0)))
                if st.button("💾 Guardar", type="primary"):
                    d = {'ticker': tp, 'revenue': rev, 'revenue_growth': 0,
                        'net_income': ni, 'eps': eps, 'eps_growth': 0,
                        'operating_margin': om, 'roe': roe, 'debt_to_equity': de,
                        'cash_from_operations': 0,
                        'precio_actual': obtener_precio_yahoo(tp) or 0,
                        'fecha_analisis': datetime.now().strftime('%Y-%m-%d')}
                    an = analizar_buffett_graham(d)
                    d['analisis'] = an
                    d['puntaje'] = an['puntaje']
                    d['decision'] = an['decision']
                    st.session_state.analisis_globaldata[tp] = d
                    st.session_state.cambios_pendientes = True
                    st.markdown(f"## {an['emoji']} {an['puntaje']}/100 - {an['decision']}")

# ============ REPORTE ============
elif pagina == "📥 Generar Reporte":
    st.title("📥 Generar Reporte")
    f = st.radio("Formato", ["📊 JSON (Claude)", "📋 WhatsApp"])
    pos_a = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan A']
    pos_b = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan B']
    va = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_a) + st.session_state.cash_a
    vb = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_b) + st.session_state.cash_b
    if st.button("🚀 Generar", type="primary"):
        if f == "📊 JSON (Claude)":
            rep = {'fecha': datetime.now().isoformat(),
                'config': {k: getattr(st.session_state, k) for k in
                          ['inversion_inicial_a', 'inversion_inicial_b', 'cash_a',
                           'cash_b', 'pyg_realizada_a', 'pyg_realizada_b']},
                'posiciones': st.session_state.posiciones,
                'ordenes': st.session_state.ordenes,
                'analisis': st.session_state.analisis_globaldata,
                'alertas': generar_alertas()}
            js = json.dumps(rep, indent=2, ensure_ascii=False)
            st.code(js[:3000] + "..." if len(js) > 3000 else js)
            st.download_button("📥 Descargar", js, file_name=f"bolsa_{datetime.now().strftime('%Y%m%d')}.json")
        else:
            txt = f"""📊 *BOLSA - {datetime.now().strftime('%d/%m/%Y')}*

💼 Plan A: ${va:,.2f}
🚀 Plan B: ${vb:,.2f}
💰 TOTAL: ${va+vb:,.2f}

Posiciones: {len(st.session_state.posiciones)}
Órdenes: {len(st.session_state.ordenes)}
"""
            st.text_area("Copiar:", txt, height=250)

# ============ CONFIGURACIÓN ============
elif pagina == "⚙️ Configuración":
    st.title("⚙️ Configuración")
    st.info("💾 Click 'GUARDAR TODO' en sidebar")
    st.subheader("💰 Inversión Inicial")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.inversion_inicial_a = st.number_input(
            "Plan A ($)", value=float(st.session_state.inversion_inicial_a), format="%.2f")
    with col2:
        st.session_state.inversion_inicial_b = st.number_input(
            "Plan B ($)", value=float(st.session_state.inversion_inicial_b), format="%.2f")
    st.subheader("💵 Cash")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.cash_a = st.number_input(
            "Cash A ($)", value=float(st.session_state.cash_a), format="%.2f")
    with col2:
        st.session_state.cash_b = st.number_input(
            "Cash B ($)", value=float(st.session_state.cash_b), format="%.2f")
    st.subheader("💵 PyG Realizada")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.pyg_realizada_a = st.number_input(
            "PyG A ($)", value=float(st.session_state.pyg_realizada_a), format="%.2f")
    with col2:
        st.session_state.pyg_realizada_b = st.number_input(
            "PyG B ($)", value=float(st.session_state.pyg_realizada_b), format="%.2f")
    if st.button("Marcar cambios"):
        st.session_state.cambios_pendientes = True
        st.success("✅ Click GUARDAR TODO en sidebar")
