"""
Dashboard Bolsa Buffett-Graham - VERSIÓN 5
Rediseño UI/UX completo:
- Dark mode profesional (#121418 base)
- Grid 2x2 KPIs con tarjetas
- TRM como ticker horizontal
- Posiciones como cards interactivas
- Iconos Lucide SVG embebidos
- Bottom nav simulada con sidebar compacta
- Toolbar Plotly off en móvil
- Correcciones: patrimonio COP sin delta falso, sin alertas

Autor: Para David Lopez
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
import yfinance as yf
import time
import re
import feedparser

st.set_page_config(
    page_title="Bolsa B-G",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============ TEMA DARK MODE PROFESIONAL ============
st.markdown("""
<style>
    /* Base - Dark Mode */
    .stApp {
        background: #121418 !important;
        color: #E4E6EB !important;
    }
    [data-testid="stHeader"] { background: #121418 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden !important; }
    .viewerBadge_container__1QSob, [data-testid="stDecoration"] { display: none !important; }
    
    /* Sidebar oscura compacta */
    [data-testid="stSidebar"] {
        background: #181A20 !important;
        border-right: 1px solid #2B2E3A;
    }
    [data-testid="stSidebar"] * { color: #E4E6EB !important; }
    
    /* Tipografía más compacta */
    h1 { font-size: 1.5rem !important; font-weight: 700 !important; color: #E4E6EB !important; margin-top: 0 !important; }
    h2 { font-size: 1.2rem !important; font-weight: 600 !important; color: #E4E6EB !important; }
    h3 { font-size: 1rem !important; font-weight: 600 !important; color: #E4E6EB !important; }
    p, span, label { color: #E4E6EB !important; }
    
    /* Tarjetas KPI con grid */
    .kpi-card {
        background: #1E222D;
        border: 1px solid #2B2E3A;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        transition: all 0.2s;
    }
    .kpi-card:hover { border-color: #10B981; }
    .kpi-label {
        font-size: 12px; color: #9CA3AF; text-transform: uppercase;
        letter-spacing: 0.5px; margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 22px; font-weight: 700; color: #E4E6EB;
        margin-bottom: 4px;
    }
    .kpi-delta-positive { color: #10B981; font-weight: 600; font-size: 13px; }
    .kpi-delta-negative { color: #EF4444; font-weight: 600; font-size: 13px; }
    .kpi-delta-neutral { color: #9CA3AF; font-weight: 600; font-size: 13px; }
    
    /* Position cards */
    .position-card {
        background: #1E222D;
        border: 1px solid #2B2E3A;
        border-radius: 10px;
        padding: 14px;
        margin: 8px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .pos-ticker { font-size: 16px; font-weight: 700; color: #E4E6EB; }
    .pos-sub { font-size: 12px; color: #9CA3AF; }
    .pos-pyg-positive { color: #10B981; font-weight: 700; }
    .pos-pyg-negative { color: #EF4444; font-weight: 700; }
    
    /* TRM Ticker horizontal */
    .trm-ticker {
        background: #1E222D;
        border: 1px solid #2B2E3A;
        border-radius: 10px;
        padding: 12px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 8px 0;
    }
    .trm-flag { font-size: 20px; margin-right: 8px; }
    .trm-pair-label { font-size: 12px; color: #9CA3AF; }
    .trm-pair-value { font-size: 18px; font-weight: 700; color: #E4E6EB; }
    
    /* Badges */
    .badge-plan-a {
        background: #10B981; color: #121418; padding: 3px 10px;
        border-radius: 6px; font-weight: 700; font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .badge-plan-b {
        background: #3B82F6; color: #121418; padding: 3px 10px;
        border-radius: 6px; font-weight: 700; font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    
    /* News cards */
    .news-card {
        background: #1E222D;
        border: 1px solid #2B2E3A;
        border-left: 3px solid #10B981;
        border-radius: 8px;
        padding: 12px;
        margin: 6px 0;
    }
    .news-card a { color: #E4E6EB !important; font-weight: 600; text-decoration: none; font-size: 14px; }
    .news-card a:hover { color: #10B981 !important; }
    .news-source { font-size: 11px; color: #9CA3AF; margin-top: 4px; }
    
    /* Buttons */
    .stButton > button {
        background: #10B981 !important;
        color: #121418 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
    }
    .stButton > button:hover { background: #059669 !important; }
    
    /* Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
        background: #1E222D !important;
        color: #E4E6EB !important;
        border: 1px solid #2B2E3A !important;
        border-radius: 8px !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: #1E222D;
        border-radius: 10px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #9CA3AF !important;
        border-radius: 6px !important;
        padding: 8px 16px !important;
    }
    .stTabs [aria-selected="true"] {
        background: #10B981 !important;
        color: #121418 !important;
    }
    
    /* Radio como segmented control */
    .stRadio > div {
        background: #1E222D;
        border-radius: 10px;
        padding: 4px;
        gap: 2px;
    }
    .stRadio label {
        background: transparent;
        border-radius: 6px !important;
        padding: 6px 12px !important;
    }
    
    /* Dataframes */
    .stDataFrame { background: #1E222D !important; border-radius: 10px; }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: #1E222D !important;
        color: #E4E6EB !important;
        border-radius: 8px !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] { color: #E4E6EB !important; }
    [data-testid="stMetricLabel"] { color: #9CA3AF !important; }
    
    /* Header principal compacto */
    .main-header-compact {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        padding: 14px 18px;
        border-radius: 12px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .main-header-compact h3 {
        color: #121418 !important;
        margin: 0 !important;
        font-size: 18px !important;
    }
    .header-sub {
        color: #121418;
        font-size: 11px;
        opacity: 0.8;
    }
    
    /* Section headers */
    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 20px 0 12px 0;
    }
    .section-title {
        font-size: 14px;
        font-weight: 700;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# ============ ICONOS LUCIDE SVG ============
def icon(name, size=20, color="#10B981"):
    icons = {
        'home': '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
        'briefcase': '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
        'trending-up': '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
        'newspaper': '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6z"/>',
        'dollar': '<line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
        'settings': '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
        'refresh': '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
        'file-pdf': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
        'chart': '<line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/>',
        'search': '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
        'save': '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/>',
        'plus': '<path d="M5 12h14"/><path d="M12 5v14"/>',
        'bitcoin': '<path d="M11.767 19.089c4.924.868 6.14-6.025 1.216-6.894m-1.216 6.894L5.86 18.047m5.908 1.042-.347 1.97m1.563-8.864c4.924.869 6.14-6.025 1.215-6.893m-1.215 6.893-3.94-.694m5.155-6.199L8.29 4.26m5.908 1.042.348-1.97M7.48 20.364l3.126-17.727"/>',
    }
    svg = icons.get(name, icons['home'])
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{svg}</svg>'

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
        st.error(f"Error Sheets: {e}")
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
        st.error(f"Cargando: {e}")
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
        st.error(f"Guardando: {e}")
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
    for i, pos in enumerate(st.session_state.posiciones):
        p = obtener_precio_yahoo(pos['ticker'])
        if p is not None:
            st.session_state.posiciones[i]['precio_actual'] = round(p, 2)
            st.session_state.posiciones[i]['ultima_actualizacion_precio'] = datetime.now().isoformat()
            act += 1
        else:
            fail.append(pos['ticker'])
    return act, fail

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

@st.cache_data(ttl=600)
def obtener_trm_historico(par='USDCOP=X', periodo='1mo'):
    try:
        return yf.Ticker(par).history(period=periodo)
    except:
        return None

@st.cache_data(ttl=1800)
def obtener_noticias(categoria='mercados'):
    feeds = {
        'mercados': [('Yahoo Finance', 'https://finance.yahoo.com/news/rssindex'),
                     ('MarketWatch', 'https://feeds.marketwatch.com/marketwatch/topstories/')],
        'crypto': [('CoinDesk', 'https://www.coindesk.com/arc/outboundfeeds/rss/'),
                   ('Yahoo', 'https://finance.yahoo.com/news/rssindex')],
        'colombia': [('Portafolio', 'https://www.portafolio.co/arc/outboundfeeds/rss/?outputType=xml'),
                     ('La República', 'https://www.larepublica.co/rss')]
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

def calcular_pyg_posicion(p):
    ct = p['shares'] * p['costo_promedio']
    va = p['shares'] * p.get('precio_actual', p['costo_promedio'])
    pyg = va - ct
    pct = (pyg / ct) * 100 if ct > 0 else 0
    return pyg, pct

def analizar_buffett_graham(data):
    puntaje, pos, neg = 0, [], []
    if data.get('net_income', 0) > 0:
        puntaje += 15
        pos.append(f"Genera ganancias (${data['net_income']:,.0f}M)")
    g = data.get('revenue_growth', 0)
    if g > 15:
        puntaje += 20; pos.append(f"Crecimiento alto ({g:.1f}%)")
    elif g > 8:
        puntaje += 10; pos.append(f"Crecimiento sólido ({g:.1f}%)")
    elif g < 0:
        neg.append("Crecimiento negativo")
    m = data.get('operating_margin', 0)
    if m > 25:
        puntaje += 15; pos.append(f"Márgenes excelentes ({m:.1f}%)")
    elif m > 15:
        puntaje += 10
    de = data.get('debt_to_equity', 1)
    if de < 0.3:
        puntaje += 15; pos.append(f"Deuda baja ({de:.2f})")
    elif de < 0.6:
        puntaje += 8
    elif de > 1.5:
        neg.append("Deuda alta")
    roe = data.get('roe', 0)
    if roe > 20:
        puntaje += 15; pos.append(f"ROE excelente ({roe:.1f}%)")
    elif roe > 12:
        puntaje += 10
    if data.get('cash_from_operations', 0) > 0:
        puntaje += 10; pos.append("Cash flow positivo")
    if puntaje >= 75:
        return {'puntaje': puntaje, 'decision': "COMPRAR / MANTENER", 'color': '#10B981',
                'positivas': pos, 'negativas': neg}
    elif puntaje >= 50:
        return {'puntaje': puntaje, 'decision': "MANTENER", 'color': '#F59E0B',
                'positivas': pos, 'negativas': neg}
    else:
        return {'puntaje': puntaje, 'decision': "VIGILAR", 'color': '#EF4444',
                'positivas': pos, 'negativas': neg}

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
    with st.spinner("Cargando..."):
        if cargar_datos():
            st.session_state.datos_cargados = True

# ============ SIDEBAR COMPACTA ============
with st.sidebar:
    st.markdown(f"""
    <div style="padding: 12px 0; border-bottom: 1px solid #2B2E3A; margin-bottom: 16px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            {icon('briefcase', 24)}
            <span style="font-size: 18px; font-weight: 700;">Bolsa B-G</span>
        </div>
        <div style="font-size: 11px; color: #9CA3AF; margin-top: 4px;">Buffett-Graham v5</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.cambios_pendientes:
        st.warning("Cambios sin guardar")
        if st.button("💾 Guardar todo", use_container_width=True):
            with st.spinner("..."):
                if guardar_todo():
                    st.rerun()
    
    if st.button("🔄 Recargar + Yahoo", use_container_width=True):
        st.session_state.datos_cargados = False
        actualizar_todos_precios_yahoo()
        st.session_state.cambios_pendientes = True
        st.rerun()
    
    st.markdown("---")
    
    pagina = st.radio("", 
        ["Inicio", "Portafolio", "Mercados", "Herramientas", "Ajustes"],
        label_visibility="collapsed")
    
    st.markdown("---")
    st.caption(f"🕐 {datetime.now().strftime('%d/%m %H:%M')}")

# ============ HEADER COMPACTO ============
pos_a = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan A']
pos_b = [p for p in st.session_state.posiciones if p['cuenta'] == 'Plan B']
valor_a = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_a) + st.session_state.cash_a
valor_b = sum(p['shares'] * p.get('precio_actual', p['costo_promedio']) for p in pos_b) + st.session_state.cash_b
valor_total = valor_a + valor_b
pyg_a = sum(calcular_pyg_posicion(p)[0] for p in pos_a)
pyg_b = sum(calcular_pyg_posicion(p)[0] for p in pos_b)

st.markdown(f"""
<div class="main-header-compact">
    <div>
        <h3>Dashboard Bolsa</h3>
        <div class="header-sub">Buffett-Graham System</div>
    </div>
    <div style="text-align: right;">
        <div style="color: #121418; font-size: 20px; font-weight: 700;">${valor_total:,.2f}</div>
        <div style="color: #121418; font-size: 11px; opacity: 0.8;">Patrimonio total</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============ PÁGINA INICIO ============
if pagina == "Inicio":
    # Grid 2x2 KPIs
    st.markdown('<div class="section-header"><div class="section-title">Resumen</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    cash_total = st.session_state.cash_a + st.session_state.cash_b
    pyg_total = pyg_a + pyg_b
    
    with col1:
        delta_class = "kpi-delta-positive" if pyg_a >= 0 else "kpi-delta-negative"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Plan A</div>
            <div class="kpi-value">${valor_a:,.2f}</div>
            <div class="{delta_class}">{'+' if pyg_a >= 0 else ''}${pyg_a:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        delta_class = "kpi-delta-positive" if pyg_b >= 0 else "kpi-delta-negative"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Plan B</div>
            <div class="kpi-value">${valor_b:,.2f}</div>
            <div class="{delta_class}">{'+' if pyg_b >= 0 else ''}${pyg_b:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Cash Total</div>
            <div class="kpi-value">${cash_total:,.2f}</div>
            <div class="kpi-delta-neutral">{(cash_total/valor_total*100):.1f}% cartera</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        delta_class = "kpi-delta-positive" if pyg_total >= 0 else "kpi-delta-negative"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Ganancia Papel</div>
            <div class="kpi-value">${pyg_total:+.2f}</div>
            <div class="{delta_class}">{(pyg_total/(valor_total-pyg_total)*100):.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    # TRM Ticker horizontal
    st.markdown('<div class="section-header"><div class="section-title">Tasas de Cambio</div></div>', unsafe_allow_html=True)
    trm = obtener_trm_actual()
    
    if trm:
        col1, col2 = st.columns(2)
        with col1:
            if 'usd_actual' in trm:
                change_class = "pos-pyg-positive" if trm['usd_change'] >= 0 else "pos-pyg-negative"
                st.markdown(f"""
                <div class="trm-ticker">
                    <div>
                        <span class="trm-flag">🇺🇸</span>
                        <span class="trm-pair-label">USD / COP</span>
                        <div class="trm-pair-value">${trm['usd_actual']:,.2f}</div>
                    </div>
                    <div class="{change_class}">
                        {trm['usd_change_pct']:+.2f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
        with col2:
            if 'eur_actual' in trm:
                change_class = "pos-pyg-positive" if trm['eur_change'] >= 0 else "pos-pyg-negative"
                st.markdown(f"""
                <div class="trm-ticker">
                    <div>
                        <span class="trm-flag">🇪🇺</span>
                        <span class="trm-pair-label">EUR / COP</span>
                        <div class="trm-pair-value">${trm['eur_actual']:,.2f}</div>
                    </div>
                    <div class="{change_class}">
                        {trm['eur_change_pct']:+.2f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Patrimonio en COP (SIN delta falso)
        if 'usd_actual' in trm:
            st.markdown(f"""
            <div class="trm-ticker" style="justify-content: center;">
                <div style="text-align: center;">
                    <div class="trm-pair-label">Patrimonio en COP (ref)</div>
                    <div class="trm-pair-value">${valor_total * trm['usd_actual']:,.0f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Comparación rendimiento (barras horizontales)
    st.markdown('<div class="section-header"><div class="section-title">Comparación Rendimiento</div></div>', unsafe_allow_html=True)
    
    if st.session_state.posiciones:
        data_c = []
        for pos in st.session_state.posiciones:
            pyg, pct = calcular_pyg_posicion(pos)
            data_c.append({
                'Ticker': pos['ticker'], 'Cuenta': pos['cuenta'],
                'PyG %': pct, 'PyG $': pyg
            })
        df = pd.DataFrame(data_c).sort_values('PyG %', ascending=True)
        
        fig = px.bar(df, y='Ticker', x='PyG %', color='Cuenta', orientation='h',
                     color_discrete_map={'Plan A': '#10B981', 'Plan B': '#3B82F6'},
                     text='PyG %')
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(
            height=400, 
            plot_bgcolor='#121418',
            paper_bgcolor='#121418',
            font_color='#E4E6EB',
            yaxis=dict(gridcolor='#2B2E3A'),
            xaxis=dict(gridcolor='#2B2E3A'),
            margin=dict(l=0, r=0, t=20, b=0)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Distribución (pies con leyenda abajo)
    st.markdown('<div class="section-header"><div class="section-title">Distribución</div></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if pos_a:
            df = pd.DataFrame([{'Ticker': p['ticker'],
                'Valor': p['shares'] * p.get('precio_actual', p['costo_promedio'])} for p in pos_a])
            df.loc[len(df)] = ['Cash', st.session_state.cash_a]
            fig = px.pie(df, values='Valor', names='Ticker', hole=0.5, title='Plan A')
            fig.update_layout(
                height=340, plot_bgcolor='#121418', paper_bgcolor='#121418',
                font_color='#E4E6EB',
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                margin=dict(l=0, r=0, t=40, b=0)
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    with col2:
        if pos_b:
            df = pd.DataFrame([{'Ticker': p['ticker'],
                'Valor': p['shares'] * p.get('precio_actual', p['costo_promedio'])} for p in pos_b])
            df.loc[len(df)] = ['Cash', st.session_state.cash_b]
            fig = px.pie(df, values='Valor', names='Ticker', hole=0.5, title='Plan B')
            fig.update_layout(
                height=340, plot_bgcolor='#121418', paper_bgcolor='#121418',
                font_color='#E4E6EB',
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                margin=dict(l=0, r=0, t=40, b=0)
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ============ PÁGINA PORTAFOLIO ============
elif pagina == "Portafolio":
    tab1, tab2, tab3 = st.tabs(["Posiciones", "Órdenes", "Nueva"])
    
    with tab1:
        st.markdown('<div class="section-header"><div class="section-title">Mis Posiciones</div></div>', unsafe_allow_html=True)
        
        for cf in ["Plan A", "Plan B"]:
            pos_c = [(i, p) for i, p in enumerate(st.session_state.posiciones) if p['cuenta'] == cf]
            if pos_c:
                badge = 'badge-plan-a' if cf == 'Plan A' else 'badge-plan-b'
                st.markdown(f'<span class="{badge}">{cf}</span>', unsafe_allow_html=True)
                st.markdown("<div style='margin: 8px 0;'></div>", unsafe_allow_html=True)
                
                for idx, pos in pos_c:
                    pyg, pct = calcular_pyg_posicion(pos)
                    pyg_class = "pos-pyg-positive" if pyg >= 0 else "pos-pyg-negative"
                    
                    st.markdown(f"""
                    <div class="position-card">
                        <div>
                            <div class="pos-ticker">{pos['ticker']}</div>
                            <div class="pos-sub">{pos['shares']:.4f} × ${pos['costo_promedio']:.2f} = ${pos['shares']*pos['costo_promedio']:.2f}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #E4E6EB; font-weight: 700; font-size: 16px;">${pos.get('precio_actual', 0):.2f}</div>
                            <div class="{pyg_class}">{'+' if pyg >= 0 else ''}${pyg:.2f} ({pct:+.1f}%)</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)
        
        # Expander para editar
        with st.expander("Editar posiciones"):
            if st.session_state.posiciones:
                st.caption("Modifica precio actual de cada posición")
                for idx, pos in enumerate(st.session_state.posiciones):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown(f"**{pos['ticker']}** ({pos['cuenta']})")
                    with col2:
                        nuevo = st.number_input("", 
                            value=float(pos.get('precio_actual', pos['costo_promedio'])),
                            format="%.2f", key=f"ep_{idx}", label_visibility="collapsed")
                    with col3:
                        if st.button("Yahoo", key=f"ey_{idx}"):
                            p = obtener_precio_yahoo(pos['ticker'])
                            if p:
                                st.session_state.posiciones[idx]['precio_actual'] = round(p, 2)
                                st.session_state.posiciones[idx]['ultima_actualizacion_precio'] = datetime.now().isoformat()
                                st.session_state.cambios_pendientes = True
                                st.rerun()
                
                if st.button("Guardar precios manuales"):
                    for idx in range(len(st.session_state.posiciones)):
                        k = f"ep_{idx}"
                        if k in st.session_state:
                            st.session_state.posiciones[idx]['precio_actual'] = st.session_state[k]
                            st.session_state.posiciones[idx]['ultima_actualizacion_precio'] = datetime.now().isoformat()
                    st.session_state.cambios_pendientes = True
                    st.success("Marcado - click Guardar en sidebar")
        
        with st.expander("Eliminar posición"):
            if st.session_state.posiciones:
                idx = st.number_input("Índice", 0, len(st.session_state.posiciones)-1)
                if st.button("Confirmar eliminar"):
                    st.session_state.posiciones.pop(idx)
                    st.session_state.cambios_pendientes = True
                    st.rerun()
    
    with tab2:
        st.markdown('<div class="section-header"><div class="section-title">Órdenes GTC</div></div>', unsafe_allow_html=True)
        
        if st.session_state.ordenes:
            for i, o in enumerate(st.session_state.ordenes):
                tipo_color = "#10B981" if o['tipo'] == 'BUY' else "#EF4444"
                dist = ""
                if o['precio_actual'] > 0:
                    d = abs(o['precio_actual'] - o['precio_limit']) / o['precio_actual'] * 100
                    dist = f"({d:.1f}% dist)"
                st.markdown(f"""
                <div class="position-card">
                    <div>
                        <div class="pos-ticker">{o['ticker']}</div>
                        <div class="pos-sub">
                            <span style="color: {tipo_color}; font-weight: 700;">{o['tipo']}</span> 
                            @ ${o['precio_limit']:.2f} · {o['cuenta']}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: #9CA3AF; font-size: 12px;">Mercado</div>
                        <div style="color: #E4E6EB; font-weight: 600;">${o['precio_actual']:.2f} {dist}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with st.expander("Eliminar orden"):
                idx = st.number_input("Índice orden", 0, len(st.session_state.ordenes)-1)
                if st.button("Confirmar"):
                    st.session_state.ordenes.pop(idx)
                    st.session_state.cambios_pendientes = True
                    st.rerun()
        else:
            st.info("Sin órdenes activas")
    
    with tab3:
        sub1, sub2 = st.tabs(["Posición", "Orden"])
        
        with sub1:
            st.caption("Agregar nueva posición")
            col1, col2 = st.columns(2)
            with col1:
                ticker = st.text_input("Ticker", key="np_t").upper()
                shares = st.number_input("Shares", 0.0, format="%.6f", key="np_s")
                costo = st.number_input("Costo promedio ($)", 0.0, format="%.2f", key="np_c")
            with col2:
                cuenta = st.selectbox("Cuenta", ["Plan A", "Plan B"], key="np_cu")
                sector = st.selectbox("Sector", ["Tech", "Semis", "Consumer", "Financial",
                                                  "Energy", "Oro", "Crypto", "ETF", "Otro"], key="np_sc")
                fecha_c = st.date_input("Fecha compra", datetime.now(), key="np_f")
            
            if st.button("Agregar posición", use_container_width=True):
                if ticker and shares > 0 and costo > 0:
                    pi = obtener_precio_yahoo(ticker) or costo
                    st.session_state.posiciones.append({
                        'ticker': ticker, 'shares': shares, 'costo_promedio': costo,
                        'precio_actual': pi, 'cuenta': cuenta, 'sector': sector,
                        'fecha_compra': fecha_c.strftime('%Y-%m-%d'),
                        'ultima_actualizacion_precio': datetime.now().isoformat() if pi != costo else ''
                    })
                    st.session_state.cambios_pendientes = True
                    st.success(f"{ticker} agregado (Yahoo: ${pi:.2f})")
                    st.rerun()
        
        with sub2:
            st.caption("Agregar orden GTC")
            col1, col2 = st.columns(2)
            with col1:
                to = st.text_input("Ticker", key="no_t").upper()
                tipo = st.selectbox("Tipo", ["BUY", "SELL"], key="no_tp")
                precio = st.number_input("Precio LIMIT", 0.0, format="%.2f", key="no_p")
            with col2:
                cant = st.number_input("Cantidad", 0.0, format="%.4f", key="no_ca")
                co = st.selectbox("Cuenta", ["Plan A", "Plan B"], key="no_cu")
                pa = st.number_input("Precio mercado", 0.0, format="%.2f", key="no_pm")
            
            if st.button("Agregar orden", use_container_width=True):
                if to and precio > 0:
                    pact = pa or obtener_precio_yahoo(to) or 0
                    st.session_state.ordenes.append({
                        'ticker': to, 'tipo': tipo, 'precio_limit': precio,
                        'cantidad': cant, 'cuenta': co,
                        'precio_actual': pact, 'fecha': datetime.now().strftime('%Y-%m-%d')
                    })
                    st.session_state.cambios_pendientes = True
                    st.success("Agregada")
                    st.rerun()

# ============ PÁGINA MERCADOS ============
elif pagina == "Mercados":
    tab1, tab2, tab3 = st.tabs(["Noticias", "TRM Divisas", "Histórico Acción"])
    
    with tab1:
        cat = st.radio("", ["Mercados", "Crypto", "Colombia"], horizontal=True, label_visibility="collapsed")
        cm = {"Mercados": "mercados", "Crypto": "crypto", "Colombia": "colombia"}
        
        with st.spinner("Cargando..."):
            noticias = obtener_noticias(cm[cat])
        
        if noticias:
            for n in noticias:
                st.markdown(f"""
                <div class="news-card">
                    <a href="{n['link']}" target="_blank">{n['titulo']}</a>
                    <div class="news-source">{n['fuente']} · {n['fecha'][:16] if n['fecha'] else ''}</div>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        trm = obtener_trm_actual()
        
        # Ticker horizontal
        col1, col2 = st.columns(2)
        with col1:
            if 'usd_actual' in trm:
                cc = "pos-pyg-positive" if trm['usd_change'] >= 0 else "pos-pyg-negative"
                st.markdown(f"""
                <div class="trm-ticker">
                    <div>
                        <span class="trm-flag">🇺🇸</span>
                        <span class="trm-pair-label">USD / COP</span>
                        <div class="trm-pair-value">${trm['usd_actual']:,.2f}</div>
                    </div>
                    <div class="{cc}">{trm['usd_change_pct']:+.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
        with col2:
            if 'eur_actual' in trm:
                cc = "pos-pyg-positive" if trm['eur_change'] >= 0 else "pos-pyg-negative"
                st.markdown(f"""
                <div class="trm-ticker">
                    <div>
                        <span class="trm-flag">🇪🇺</span>
                        <span class="trm-pair-label">EUR / COP</span>
                        <div class="trm-pair-value">${trm['eur_actual']:,.2f}</div>
                    </div>
                    <div class="{cc}">{trm['eur_change_pct']:+.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-header"><div class="section-title">Histórico</div></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            par_sel = st.radio("Par:", ["USD/COP", "EUR/COP", "EUR/USD"], horizontal=True)
        with col2:
            periodo = st.radio("Período:", ["1 sem", "1 mes", "YTD", "1 año", "5 años"], horizontal=True)
        
        par_map = {"USD/COP": "USDCOP=X", "EUR/COP": "EURCOP=X", "EUR/USD": "EURUSD=X"}
        per_map = {"1 sem": "5d", "1 mes": "1mo", "YTD": "ytd", "1 año": "1y", "5 años": "5y"}
        
        with st.spinner(f"Cargando..."):
            hist = obtener_trm_historico(par_map[par_sel], per_map[periodo])
        
        if hist is not None and not hist.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'],
                mode='lines', name=par_sel,
                line=dict(color='#10B981', width=2),
                fill='tozeroy', fillcolor='rgba(16,185,129,0.1)'))
            fig.update_layout(
                height=400, hovermode='x unified',
                plot_bgcolor='#121418', paper_bgcolor='#121418',
                font_color='#E4E6EB',
                yaxis=dict(gridcolor='#2B2E3A'),
                xaxis=dict(gridcolor='#2B2E3A'),
                margin=dict(l=0, r=0, t=20, b=0)
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Actual", f"${hist['Close'].iloc[-1]:,.2f}")
            col2.metric("Máx", f"${hist['Close'].max():,.2f}")
            col3.metric("Mín", f"${hist['Close'].min():,.2f}")
            vol = ((hist['Close'].max() - hist['Close'].min()) / hist['Close'].min()) * 100
            col4.metric("Rango", f"{vol:.1f}%")
        
        # Conversor unificado
        st.markdown('<div class="section-header"><div class="section-title">Conversor</div></div>', unsafe_allow_html=True)
        monto = st.number_input("Monto", value=100.0, format="%.2f")
        
        if trm:
            col1, col2 = st.columns(2)
            with col1:
                if 'usd_actual' in trm:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">USD → COP</div>
                        <div class="kpi-value">${monto * trm['usd_actual']:,.0f}</div>
                        <div class="kpi-delta-neutral">COP → USD: ${monto / trm['usd_actual']:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
            with col2:
                if 'eur_actual' in trm:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">EUR → COP</div>
                        <div class="kpi-value">${monto * trm['eur_actual']:,.0f}</div>
                        <div class="kpi-delta-neutral">COP → EUR: ${monto / trm['eur_actual']:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    with tab3:
        if st.session_state.posiciones:
            tickers = list(set([p['ticker'] for p in st.session_state.posiciones]))
            col1, col2 = st.columns(2)
            with col1:
                ts = st.selectbox("Acción", tickers)
            with col2:
                per = st.radio("Período", ["1mo", "3mo", "6mo", "1y", "2y"], horizontal=True)
            
            if ts:
                with st.spinner("..."):
                    hist = obtener_historico_yahoo(ts, per)
                if hist is not None and not hist.empty:
                    pos_t = [p for p in st.session_state.posiciones if p['ticker'] == ts]
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'],
                        mode='lines', name=ts, line=dict(color='#10B981', width=2)))
                    for p in pos_t:
                        fig.add_hline(y=p['costo_promedio'], line_dash="dash", 
                                     line_color="#3B82F6",
                                     annotation_text=f"Costo ({p['cuenta']})")
                    ph = hist['Close'].iloc[-1]
                    fig.add_hline(y=ph, line_dash="dot", line_color="#EF4444",
                                 annotation_text=f"HOY: ${ph:.2f}")
                    fig.update_layout(
                        height=450, hovermode='x unified',
                        plot_bgcolor='#121418', paper_bgcolor='#121418',
                        font_color='#E4E6EB',
                        yaxis=dict(gridcolor='#2B2E3A'),
                        xaxis=dict(gridcolor='#2B2E3A'),
                        margin=dict(l=0, r=0, t=20, b=0)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Hoy", f"${ph:.2f}")
                    col2.metric("Máx", f"${hist['Close'].max():.2f}")
                    col3.metric("Mín", f"${hist['Close'].min():.2f}")
        else:
            st.info("Sin posiciones")

# ============ PÁGINA HERRAMIENTAS ============
elif pagina == "Herramientas":
    tab1, tab2, tab3 = st.tabs(["Análisis B-G", "Subir PDF", "Reporte"])
    
    with tab1:
        st.caption("Análisis Buffett-Graham manual")
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
        
        if st.button("Analizar", use_container_width=True):
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
                
                st.markdown(f"""
                <div class="kpi-card" style="border-left: 4px solid {an['color']};">
                    <div class="kpi-label">{tg}</div>
                    <div class="kpi-value" style="color: {an['color']};">{an['puntaje']}/100</div>
                    <div style="color: {an['color']}; font-weight: 700;">{an['decision']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Positivos**")
                    for p in an['positivas']:
                        st.markdown(f"✓ {p}")
                with col2:
                    st.markdown("**Negativos**")
                    for n in an['negativas']:
                        st.markdown(f"✗ {n}")
    
    with tab2:
        st.caption("Subir PDF GlobalData para extracción automática")
        tp = st.text_input("Ticker PDF").upper()
        pf = st.file_uploader("PDF", type=['pdf'])
        if pf and tp:
            if st.button("Extraer datos"):
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(pf)
                    texto = "".join([page.extract_text() + "\n" for page in reader.pages])
                    patterns = {
                        'revenue': r'(?:Total Revenue|Revenue)[\s\S]{0,100}?([\d,]+\.?\d*)',
                        'net_income': r'Net Income[\s\S]{0,100}?([\d,]+\.?\d*)',
                        'eps': r'(?:Diluted.*?EPS|EPS)[\s\S]{0,100}?([\d]+\.\d+)',
                    }
                    datos = {}
                    for k, pat in patterns.items():
                        m = re.search(pat, texto, re.IGNORECASE)
                        if m:
                            try:
                                datos[k] = float(m.group(1).replace(',', ''))
                            except:
                                pass
                    if datos:
                        st.success(f"{len(datos)} campos extraídos")
                        st.json(datos)
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with tab3:
        st.caption("Reporte en JSON para Claude")
        if st.button("Generar JSON", use_container_width=True):
            rep = {'fecha': datetime.now().isoformat(),
                'config': {k: getattr(st.session_state, k) for k in
                          ['inversion_inicial_a', 'inversion_inicial_b', 'cash_a',
                           'cash_b', 'pyg_realizada_a', 'pyg_realizada_b']},
                'posiciones': st.session_state.posiciones,
                'ordenes': st.session_state.ordenes,
                'analisis': st.session_state.analisis_globaldata}
            js = json.dumps(rep, indent=2, ensure_ascii=False)
            st.download_button("Descargar JSON", js,
                file_name=f"bolsa_{datetime.now().strftime('%Y%m%d')}.json",
                use_container_width=True)
            st.code(js[:2000] + "..." if len(js) > 2000 else js, language='json')

# ============ PÁGINA AJUSTES ============
elif pagina == "Ajustes":
    st.markdown('<div class="section-header"><div class="section-title">Configuración</div></div>', unsafe_allow_html=True)
    st.caption("Click Guardar en sidebar después de cambios")
    
    tab1, tab2 = st.tabs(["Capital", "Rendimiento"])
    
    with tab1:
        st.markdown("**Inversión Inicial**")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.inversion_inicial_a = st.number_input(
                "Plan A ($)", value=float(st.session_state.inversion_inicial_a), format="%.2f")
        with col2:
            st.session_state.inversion_inicial_b = st.number_input(
                "Plan B ($)", value=float(st.session_state.inversion_inicial_b), format="%.2f")
        
        st.markdown("**Cash Actual**")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.cash_a = st.number_input(
                "Cash A ($)", value=float(st.session_state.cash_a), format="%.2f")
        with col2:
            st.session_state.cash_b = st.number_input(
                "Cash B ($)", value=float(st.session_state.cash_b), format="%.2f")
    
    with tab2:
        st.markdown("**PyG Realizada**")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.pyg_realizada_a = st.number_input(
                "PyG A ($)", value=float(st.session_state.pyg_realizada_a), format="%.2f")
        with col2:
            st.session_state.pyg_realizada_b = st.number_input(
                "PyG B ($)", value=float(st.session_state.pyg_realizada_b), format="%.2f")
    
    if st.button("Marcar cambios para guardar", use_container_width=True):
        st.session_state.cambios_pendientes = True
        st.success("Click Guardar en sidebar")
