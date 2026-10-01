# 📊 Dashboard Bolsa Buffett-Graham

Sistema personal de gestión cartera dual (Plan A + Plan B) con análisis Buffett-Graham automático.

## 🚀 Instalación Rápida

### 1. Instalar Python (si no lo tienes)
Descargar de: https://www.python.org/downloads/

### 2. Instalar dependencias
```bash
cd bolsa-dashboard
pip install -r requirements.txt
```

### 3. Ejecutar la app
```bash
streamlit run app.py
```

Se abre automáticamente en: `http://localhost:8501`

---

## 📱 Cómo Usar

### Primera vez:
1. Ir a **⚙️ Configuración**
   - Meter inversión inicial Plan A y Plan B
   - Meter cash actual
   - Meter PyG realizada histórica

2. Ir a **💼 Mis Posiciones**
   - Agregar cada posición (ticker, shares, costo, cuenta)

3. Ir a **📋 Órdenes Activas**
   - Agregar cada orden GTC activa

### Uso Diario:
1. Actualizar precios actuales en posiciones (opcional, para ver PyG)
2. Ir a **🔍 Análisis GlobalData** cuando quieras analizar una acción:
   - Copiar datos de GlobalData
   - Pegar en el formulario
   - Click "Analizar"
   - Ver puntaje y decisión Buffett-Graham

### Generar Reportes:
1. Ir a **📄 Generar Reporte**
2. Elegir formato:
   - **PDF**: Para archivar o compartir
   - **JSON**: Para mandarme a Claude para análisis
   - **Texto WhatsApp**: Resumen rápido

---

## 🎯 Qué Analiza (Filtros Buffett-Graham)

El sistema evalúa cada acción con 7 filtros:

1. ✅ **Genera ganancias** (Net Income positivo)
2. 🚀 **Revenue growth** (>8% sólido, >15% excelente)
3. 🏆 **Operating Margin** (>15% bueno, >25% wide moat)
4. 💪 **Debt/Equity** (<0.3 excelente, <0.6 OK)
5. 🏆 **ROE** (>12% bueno, >20% excelente)
6. 🚀 **EPS Growth** (crecimiento ganancia por acción)
7. ✅ **Cash Flow positivo**

**Puntaje:**
- 75-100: 🟢 COMPRAR / MANTENER FUERTE
- 50-74: 🟡 MANTENER
- 30-49: 🟠 VIGILAR / REDUCIR
- 0-29: 🔴 EVITAR / VENDER

---

## 💾 Backup

En **⚙️ Configuración** puedes:
- Exportar backup (JSON con todo)
- Restaurar backup

**Recomendado:** Hacer backup semanal.

---

## 🤖 Integración con Claude

Para mandarme análisis:
1. Click **📄 Generar Reporte**
2. Elegir **📊 JSON**
3. Descargar
4. Mandarme el JSON por chat

Yo analizo todo y te doy recomendaciones.

---

## 🚀 Deploy Gratis (opcional)

Para usar la app desde cualquier lugar sin PC:

1. Subir código a GitHub
2. Ir a https://streamlit.io/cloud
3. Conectar repo
4. Deploy automático

URL permanente para usar en celular/PC.

---

**Hecho para David Lopez — Sistema Buffett-Graham Plan A + Plan B**
