#!/usr/bin/env python
# coding: utf-8

# In[26]:


# import polars as pl


# In[25]:


# convocatorias = pl.read_excel("Convocatorias/Matriz de Convocatorias SDP.xlsx",table_name="SeguimientoConvocatorias").drop_nulls()


# convocatorias = convocatorias.with_columns(pl.col("SECTOR").str.split(by=" - ")).explode(columns=["SECTOR"])


# In[ ]:


import io
import re
import math
import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Convocatorias SDP",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

[data-testid="stSidebar"] {
    background: #0d1f12;
    border-right: 1px solid #196B24;
}
[data-testid="stSidebar"] * { color: #e8f5e9 !important; }
[data-testid="stSidebar"] label {
    color: #a5d6a7 !important;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 600;
}

.metric-card {
    background: white;
    border: 1px solid #e0ede0;
    border-left: 4px solid #196B24;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 8px;
}
.metric-card .label {
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #6a8c6a;
    font-weight: 600;
    margin-bottom: 4px;
}
.metric-card .value {
    font-family: 'DM Serif Display', serif;
    font-size: 2.2rem;
    color: #0d1f12;
    line-height: 1;
}
.metric-card .sub { font-size: 0.78rem; color: #8aab8a; margin-top: 4px; }

.section-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: #0d1f12;
    margin: 28px 0 4px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid #196B24;
}
.section-sub { font-size: 0.82rem; color: #6a8c6a; margin-bottom: 18px; }

.hero {
    background: linear-gradient(135deg, #0d1f12 0%, #196B24 100%);
    border-radius: 12px;
    padding: 36px 40px 32px;
    margin-bottom: 28px;
}
.hero h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: white;
    margin: 0 0 6px 0;
    line-height: 1.2;
}
.hero p { color: #a5d6a7; font-size: 0.88rem; margin: 0; font-weight: 300; }

.stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid #196B24; gap: 4px; }
.stTabs [data-baseweb="tab"] {
    font-weight: 600; font-size: 0.85rem;
    color: #6a8c6a; border-radius: 6px 6px 0 0; padding: 8px 18px;
}
.stTabs [aria-selected="true"] { background: #196B24 !important; color: white !important; }

.stDownloadButton > button {
    background: #196B24 !important; color: white !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; padding: 10px 22px !important;
}
.stDownloadButton > button:hover { background: #0d4a18 !important; }

[data-testid="stFileUploader"] {
    border: 2px dashed #196B24 !important;
    border-radius: 10px !important;
    background: #f0f9f0 !important;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
SECTOR_MAP = {
    "desarrollo-interior-planeación": "Desarrollo - Interior - Planeación",
    "desarrollo-interior-planeación-inclusion": "Desarrollo - Interior - Planeación - Inclusión",
    "desarrollo-interior": "Desarrollo - Interior",
    "Desarrollo - Interior - Planeacion": "Desarrollo - Interior - Planeación",
    "competitividad-planeacion": "Competitividad - Planeación",
    "Planeacion": "Planeación",
    "desarrollo - competitividad": "Desarrollo - Competitividad",
    "desarrollo-competitividad": "Desarrollo - Competitividad",
    "desarrollo - competitividad-INCLUSION": "Desarrollo - Competitividad - Inclusión",
    "COMPETITIVIDAD": "Competitividad",
    "competitividad-educacion-corposucre": "Competitividad - Educación",
    "desarrollo productivo, la competitividad, la innovación": "Desarrollo - Competitividad - Innovación",
    "inclusión - desarrollo": "Inclusión - Desarrollo",
    "inclusión-desarrollo-competitividad": "Inclusión - Desarrollo - Competitividad",
    "desarrollo -INCLUSION": "Desarrollo - Inclusión",
    "Desarrollo - Incluision": "Desarrollo - Inclusión",
    "inclusión": "Inclusión",
    "Inclusion": "Inclusión",
    "inclusión-mujer": "Inclusión - Mujer",
    "Inclusión, Desarrollo Productivo": "Inclusión - Desarrollo",
    "Salud, Inclusion, Educacion": "Salud - Inclusión - Educación",
    "educación- salud- desarrollo ambiente - inclusión": "Educación - Salud - Desarrollo - Inclusión",
    "Desarrollo": "Desarrollo",
    "Desarrollo ": "Desarrollo",
    "desarrollo": "Desarrollo",
    "Desarrollo y innovasion": "Desarrollo - Innovación",
    "Innovacion social": "Innovación Social",
    "Desarrollo del sector agropecuario y emprendimientos rurales": "Desarrollo - Agropecuario",
    "Desarrollo - Turismo": "Desarrollo - Turismo",
    "Desarrollo, Turismo": "Desarrollo - Turismo",
    "Desarrollo, cambio climatico": "Desarrollo - Medio Ambiente",
    "Desarrollo, medio ambiente y energias": "Desarrollo - Medio Ambiente - Energía",
    "Desarrollo, seguridad alimentaria": "Desarrollo - Seguridad Alimentaria",
    "Desarrollo económico, turismo, cultura, tic. ": "Desarrollo - Turismo - Cultura - TIC",
    "tic-educación": "TIC - Educación",
    "educación, fondo mixto, salud": "Educación - Salud - Fondo Mixto",
    "Educacion": "Educación",
    "Tecnologías de la Información y las Comunicaciones (TIC) / Transformación Digital Pública": "TIC",
    "salud": "Salud",
    "agua y saneamiento.": "Agua y Saneamiento",
    "Conservación ambiental\n\nAlimentación y agricultura\n\nSeguridad y soberanía alimentaria\n\nSalud pública": "Ambiente - Salud - Seguridad Alimentaria",
    "Energias": "Energía",
    "Energía,Transporte,Industria.": "Energía - Transporte - Industria",
    "Energía solar\nEquidad social y económica\nReducción de impacto ambiental\nComunidades marginadas": "Energía - Inclusión",
    "Ambiente y Desarrollo Sostenible": "Ambiente y Desarrollo Sostenible",
    "turismo": "Turismo",
    " Turismo": "Turismo",
    "Turismo y cultura": "Turismo - Cultura",
    "Cultura - juntas comunales": "Cultura",
    "Vivienda": "Vivienda",
    "Reincorporación – Vivienda y Hábitat (Construcción de Paz)": "Vivienda - Paz",
    "Transporte": "Transporte",
    "Fondo mixto": "Fondo Mixto",
    "Juridico, administrativo": "Jurídico - Administrativo",
    "Agua potable, saneamiento y alcantarillado\n\nSalud pública\n\nEducación pública\n\nInfraestructura de transporte\n\nEnergía\n\nBienes públicos rurales e infraestructura productiva\n\nAdaptación al cambio climático, gestión del riesgo, pago por servicios ambientales\n\nTecnologías de la información y comunicaciones\n\nInfraestructura cultural y deportiva\n\nSeguridad alimentaria y nutrición\n\nNegocios verdes": "Infraestructura - Agua - Educación - Energía - Salud",
    "Transporte, Agricultura y Desarrollo Rural, Vivienda, Ciudad y Territorio, Tecnologías de la Información y las Comunicaciones, Comercio, Industria y Turismo, Minas y Energía, Ambiente y Desarrollo Sostenible, Salud y Educación": "Varios",
    "Infraestructura vial\nAgua potable y saneamiento\nbásico\nEducación Pública\nEnergía\nSalud pública": "Infraestructura - Agua - Educación - Energía - Salud",
    "Derechos Humanos\n\nProtección y asistencia a víctimas\n\nLucha contra la trata de personas\n\nAtención humanitaria y social": "Derechos Humanos - Inclusión",
    "Restauración de ecosistemas alterados con visión de paisaje, que incluye:\n\nRestauración ecológica\n\nRestauración productiva\n\nRehabilitación funcional\n\nRestauración multifuncional del paisaje\n\nPagos por Servicios Ambientales (PSA) y otros incentivos a la conservación, orientados a reconocer y promover la protección de ecosistemas estratégicos.\n\nEconomías de la naturaleza, tales como:\n\nManejo forestal sostenible\n\nSistemas productivos sostenibles\n\nAprovechamiento responsable de productos del bosque\n\nArtesanías y economías propias con enfoque ambiental\n\nGobernanza ambiental, que incluye:\n\nParticipación comunitaria\n\nFortalecimiento organizativo\n\nVeedurías ciudadanas\n\nEducación y formación ambiental\n\nLiderazgo ambiental (con enfoque de género y étnico) ": "Ambiente y Desarrollo Sostenible",
    "Fortalecimiento de capacidades de centros:\nFortalecimiento de capacidades de Centros e Institutos de Investigación, Centros de Desarrollo Tecnológico y Centros de Ciencia existentes, independientemente de si cuentan o no con reconocimiento vigente por parte del Ministerio de Ciencia, Tecnología e Innovación.": "Ciencia y Tecnología",
    "formuladores-evaluadores": None,
    "verificar": None,
    "N/D": None,
    "No especifica": None,
    "VARIOS": "Varios",
}

COLS_REPORT = [
    "ID", "NOMBRE DE LA CONVOCATORIA", "SEGMENTO",
    "FECHA DE APERTURA", "FECHA DE CIERRE", "DÍAS DISPONIBLES",
    "ESTADO", "MONTO POR PROYECTO", "OBJETIVO",
    "CONTACTO", "QUIENES PUEDEN PARTICIPAR", "FUENTES",
]
COL_WIDTHS = {
    "ID": 6, "NOMBRE DE LA CONVOCATORIA": 38, "SEGMENTO": 22,
    "FECHA DE APERTURA": 18, "FECHA DE CIERRE": 18, "DÍAS DISPONIBLES": 12,
    "ESTADO": 10, "MONTO POR PROYECTO": 16, "OBJETIVO": 50,
    "CONTACTO": 35, "QUIENES PUEDEN PARTICIPAR": 30, "FUENTES": 20,
}


# ══════════════════════════════════════════════════════════════════════════════
# DATA PROCESSING
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def load_and_clean(file_bytes: bytes):
    raw = pd.read_excel(
        io.BytesIO(file_bytes),
        sheet_name="Consolidado Convocatorias",
        header=5,
    )
    raw["SECTOR_LIMPIO"] = raw["SECTOR"].map(
        lambda v: SECTOR_MAP.get(v, v) if pd.notna(v) else None
    )
    base = raw.dropna(subset=["SECTOR_LIMPIO"]).copy()

    exploded = base.copy()
    exploded["SECTOR_LIMPIO"] = exploded["SECTOR_LIMPIO"].str.split(" - ")
    exploded = exploded.explode("SECTOR_LIMPIO")
    exploded["SECTOR_LIMPIO"] = exploded["SECTOR_LIMPIO"].str.strip()
    return base, exploded


# ══════════════════════════════════════════════════════════════════════════════
# EXCEL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
def build_excel(exploded: pd.DataFrame) -> bytes:
    H_FILL = PatternFill("solid", fgColor="196B24")
    H_FONT = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    T_FONT = Font(bold=True, color="196B24", name="Arial", size=13)
    C_FONT = Font(name="Arial", size=9)
    THIN   = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )
    WHITE = PatternFill("solid", fgColor="FFFFFF")

    wb = Workbook()
    wb.remove(wb.active)
    sectores = sorted(exploded["SECTOR_LIMPIO"].unique())

    # ── Índice ──
    wi = wb.create_sheet("Índice")
    wi.sheet_view.showGridLines = False
    wi["A1"] = "Convocatorias por Sector"
    wi["A1"].font = Font(bold=True, color="196B24", name="Arial", size=15)
    for ci, label in enumerate(["SECTOR", "N° CONVOCATORIAS"], 1):
        c = wi.cell(row=3, column=ci, value=label)
        c.font = H_FONT; c.fill = H_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = THIN
    for i, s in enumerate(sectores, 4):
        n = exploded[exploded["SECTOR_LIMPIO"] == s]["ID"].nunique()
        for ci, val in enumerate([s, n], 1):
            c = wi.cell(row=i, column=ci, value=val)
            c.font = C_FONT; c.fill = WHITE; c.border = THIN
            c.alignment = Alignment(horizontal="center" if ci == 2 else "left", vertical="center")
    wi.column_dimensions["A"].width = 30
    wi.column_dimensions["B"].width = 20
    tbl_i = Table(displayName="Indice", ref=f"A3:B{3+len(sectores)}")
    tbl_i.tableStyleInfo = TableStyleInfo(name="TableStyleMedium7", showRowStripes=False)
    wi.add_table(tbl_i)

    # ── Per-sector sheets ──
    for sector in sectores:
        sname = sector[:31].replace("/", "-").replace("\\", "-").replace(":", "")
        ws = wb.create_sheet(sname)
        ws.sheet_view.showGridLines = False

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(COLS_REPORT))
        tc = ws.cell(row=1, column=1, value=f"Sector: {sector}")
        tc.font = T_FONT
        tc.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[1].height = 22

        subset = exploded[exploded["SECTOR_LIMPIO"] == sector][COLS_REPORT].reset_index(drop=True)
        nc = ws.cell(row=2, column=1, value=f"{len(subset)} convocatoria(s)")
        nc.font = Font(name="Arial", size=9, color="666666", italic=True)
        ws.row_dimensions[2].height = 14

        for ci, col in enumerate(COLS_REPORT, 1):
            c = ws.cell(row=3, column=ci, value=col)
            c.font = H_FONT; c.fill = H_FILL
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = THIN
        ws.row_dimensions[3].height = 30

        for ri, (_, row) in enumerate(subset.iterrows(), 4):
            for ci, col in enumerate(COLS_REPORT, 1):
                val = row[col]
                if pd.isna(val): val = ""
                c = ws.cell(row=ri, column=ci, value=val)
                c.font = C_FONT; c.fill = WHITE; c.border = THIN
                c.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws.row_dimensions[ri].height = 45

        for ci, col in enumerate(COLS_REPORT, 1):
            ws.column_dimensions[get_column_letter(ci)].width = COL_WIDTHS.get(col, 15)

        ws.freeze_panes = "A4"
        last_col = get_column_letter(len(COLS_REPORT))
        tname = "T_" + re.sub(r"[^A-Za-z0-9_]", "_", sector)[:28]
        tbl = Table(displayName=tname, ref=f"A3:{last_col}{3+len(subset)}")
        tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium7", showRowStripes=False)
        ws.add_table(tbl)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# CHART HELPERS
# ══════════════════════════════════════════════════════════════════════════════
GREENS = ["#196B24","#1a7a27","#1e8c2e","#22a034","#27b33b",
          "#2ec644","#3ddb52","#57e368","#7aeb87","#9df2a7"]

def bar_chart_html(data: pd.Series, title: str, max_bars: int = 20) -> str:
    data = data.sort_values(ascending=False).head(max_bars)
    max_val = data.max() or 1
    rows = ""
    for i, (label, val) in enumerate(data.items()):
        pct = (val / max_val) * 100
        color = GREENS[i % len(GREENS)]
        rows += f"""
        <div style="display:flex;align-items:center;margin-bottom:9px;gap:10px">
          <div style="width:170px;font-size:0.77rem;color:#2d4a2d;text-align:right;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0"
               title="{label}">{label}</div>
          <div style="flex:1;background:#f0f0f0;border-radius:4px;height:24px;position:relative">
            <div style="width:{pct}%;background:{color};height:100%;border-radius:4px"></div>
            <span style="position:absolute;right:8px;top:4px;font-size:0.73rem;
                         font-weight:700;color:#1a1a1a">{val}</span>
          </div>
        </div>"""
    return f"""
    <div style="background:white;border:1px solid #e0ede0;border-radius:10px;
                padding:24px 24px 20px;margin-bottom:16px">
      <div style="font-family:'DM Serif Display',serif;font-size:1rem;color:#0d1f12;
                  margin-bottom:16px;padding-bottom:8px;border-bottom:2px solid #196B24">{title}</div>
      {rows}
    </div>"""


def donut_html(data: pd.Series, title: str, top_n: int = 8) -> str:
    total = data.sum()
    if total == 0:
        return ""
    top = data.sort_values(ascending=False).head(top_n)
    cx, cy, r, ir = 75, 75, 60, 34
    angle = -90.0
    paths = ""
    for i, (_, val) in enumerate(top.items()):
        sweep = (val / total) * 360
        end = angle + sweep
        a1r, a2r = math.radians(angle), math.radians(end)
        x1,y1 = cx+r*math.cos(a1r), cy+r*math.sin(a1r)
        x2,y2 = cx+r*math.cos(a2r), cy+r*math.sin(a2r)
        ix1,iy1 = cx+ir*math.cos(a2r), cy+ir*math.sin(a2r)
        ix2,iy2 = cx+ir*math.cos(a1r), cy+ir*math.sin(a1r)
        large = 1 if sweep > 180 else 0
        color = GREENS[i % len(GREENS)]
        paths += f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {large},1 {x2:.1f},{y2:.1f} L{ix1:.1f},{iy1:.1f} A{ir},{ir} 0 {large},0 {ix2:.1f},{iy2:.1f} Z" fill="{color}" stroke="white" stroke-width="2"/>'
        angle = end

    legend = ""
    for i, (label, val) in enumerate(top.items()):
        pct = round(val / total * 100, 1)
        legend += f"""
        <div style="display:flex;align-items:center;gap:7px;margin-bottom:5px">
          <div style="width:9px;height:9px;border-radius:50%;background:{GREENS[i % len(GREENS)]};flex-shrink:0"></div>
          <div style="font-size:0.74rem;color:#2d4a2d;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
               title="{label}">{label}</div>
          <div style="font-size:0.74rem;font-weight:700;color:#196B24">{pct}%</div>
        </div>"""

    svg = f"""<svg width="150" height="150" viewBox="0 0 150 150">
      {paths}
      <text x="{cx}" y="{cy+5}" text-anchor="middle"
            font-size="17" font-family="DM Serif Display" fill="#0d1f12" font-weight="bold">{total}</text>
      <text x="{cx}" y="{cy+18}" text-anchor="middle"
            font-size="8.5" font-family="DM Sans" fill="#6a8c6a">total</text>
    </svg>"""

    return f"""
    <div style="background:white;border:1px solid #e0ede0;border-radius:10px;
                padding:24px 24px 20px;margin-bottom:16px">
      <div style="font-family:'DM Serif Display',serif;font-size:1rem;color:#0d1f12;
                  margin-bottom:16px;padding-bottom:8px;border-bottom:2px solid #196B24">{title}</div>
      <div style="display:flex;gap:20px;align-items:center">
        <div style="flex-shrink:0">{svg}</div>
        <div style="flex:1;overflow:hidden">{legend}</div>
      </div>
    </div>"""


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 0 22px">
      <div style="font-family:'DM Serif Display',serif;font-size:1.4rem;color:white;line-height:1.25">
        📁 Convocatorias
      </div>
      <div style="color:#a5d6a7;font-size:0.82rem;font-weight:300;margin-top:4px">
        SDP · Reporte Interactivo
      </div>
    </div>
    <hr style="border-color:#196B24;margin-bottom:20px">
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Cargar archivo Excel",
        type=["xlsx"],
        help="Debe contener la hoja 'Consolidado Convocatorias'",
    )

    if uploaded:
        st.markdown("<hr style='border-color:#196B24;margin:20px 0 14px'>", unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;"
            "color:#a5d6a7;font-weight:600;margin-bottom:10px'>Filtros</div>",
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# LANDING (no file)
# ══════════════════════════════════════════════════════════════════════════════
if not uploaded:
    st.markdown("""
    <div class="hero">
      <h1>Reporte de Convocatorias</h1>
      <p>Carga el archivo Excel desde el panel lateral para generar el dashboard y el reporte por sector.</p>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    for col, lbl, sub in [
        (c1, "Dashboard", "Visualiza convocatorias por sector con gráficas interactivas"),
        (c2, "Explorador", "Navega y filtra el listado completo de convocatorias"),
        (c3, "Reporte Excel", "Genera un archivo con una hoja por cada sector"),
    ]:
        col.markdown(f"""
        <div class="metric-card">
          <div class="label">{lbl}</div>
          <div style="font-size:0.83rem;color:#6a8c6a;margin-top:6px">{sub}</div>
        </div>""", unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("Procesando datos…"):
    file_bytes = uploaded.read()
    base_df, exploded_df = load_and_clean(file_bytes)

sectores_all  = sorted(exploded_df["SECTOR_LIMPIO"].unique())
segmentos_all = sorted(base_df["SEGMENTO"].dropna().unique())
estados_all   = sorted(base_df["ESTADO"].dropna().unique())

# Sidebar filters
with st.sidebar:
    sel_sectores  = st.multiselect("Sector",   sectores_all,  placeholder="Todos")
    sel_segmentos = st.multiselect("Segmento", segmentos_all, placeholder="Todos")
    sel_estados   = st.multiselect("Estado",   estados_all,   placeholder="Todos")

# Apply filters
exp_f  = exploded_df.copy()
base_f = base_df.copy()

if sel_sectores:
    exp_f  = exp_f[exp_f["SECTOR_LIMPIO"].isin(sel_sectores)]
    base_f = base_f[base_f["ID"].isin(exp_f["ID"])]
if sel_segmentos:
    base_f = base_f[base_f["SEGMENTO"].isin(sel_segmentos)]
    exp_f  = exp_f[exp_f["ID"].isin(base_f["ID"])]
if sel_estados:
    base_f = base_f[base_f["ESTADO"].isin(sel_estados)]
    exp_f  = exp_f[exp_f["ID"].isin(base_f["ID"])]


# ══════════════════════════════════════════════════════════════════════════════
# HERO + KPIs
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="hero">
  <h1>Reporte de Convocatorias</h1>
  <p>{uploaded.name} &nbsp;·&nbsp; {len(base_df)} registros cargados &nbsp;·&nbsp;
     {len(sectores_all)} sectores identificados</p>
</div>
""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
n_vigentes  = len(base_f[base_f["ESTADO"].str.upper().str.contains("VIGENTE", na=False)])
n_sect_f    = exp_f["SECTOR_LIMPIO"].nunique()
n_seg_f     = base_f["SEGMENTO"].nunique()
pct_vig     = round(n_vigentes / max(len(base_f), 1) * 100)

for col, val, label, sub in [
    (k1, len(base_f),  "Convocatorias",   "en la selección actual"),
    (k2, n_vigentes,   "Vigentes",         f"{pct_vig}% del total filtrado"),
    (k3, n_sect_f,     "Sectores",         "categorías activas"),
    (k4, n_seg_f,      "Segmentos",        "tipos de convocatoria"),
]:
    col.markdown(f"""
    <div class="metric-card">
      <div class="label">{label}</div>
      <div class="value">{val}</div>
      <div class="sub">{sub}</div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["Dashboard", "Explorador", "Reporte Excel"])


# ───────────── TAB 1: DASHBOARD ──────────────────────────────────────────────
with tab1:
    sector_counts = exp_f.groupby("SECTOR_LIMPIO")["ID"].nunique().rename("n")

    st.markdown('<div class="section-title">Distribución por sector</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Número único de convocatorias asociadas a cada sector temático</div>', unsafe_allow_html=True)

    ca, cb = st.columns([3, 2])
    with ca:
        st.markdown(bar_chart_html(sector_counts, "Convocatorias por sector"), unsafe_allow_html=True)
    with cb:
        st.markdown(donut_html(sector_counts, "Top 8 sectores"), unsafe_allow_html=True)
        if not base_f.empty:
            seg_c = base_f["SEGMENTO"].value_counts()
            st.markdown(donut_html(seg_c, "Por segmento"), unsafe_allow_html=True)

    st.markdown('<div class="section-title">Estado de las convocatorias</div>', unsafe_allow_html=True)
    if not base_f.empty:
        est_c = base_f["ESTADO"].value_counts()
        st.markdown(bar_chart_html(est_c, "Por estado"), unsafe_allow_html=True)


# ───────────── TAB 2: EXPLORADOR ─────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-title">Listado de convocatorias</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-sub">{len(base_f)} convocatorias con los filtros aplicados</div>', unsafe_allow_html=True)

    show_cols = ["ID", "NOMBRE DE LA CONVOCATORIA", "SEGMENTO", "ESTADO",
                 "FECHA DE APERTURA", "FECHA DE CIERRE", "SECTOR_LIMPIO"]
    show_cols = [c for c in show_cols if c in base_f.columns]
    display_df = base_f[show_cols].rename(columns={"SECTOR_LIMPIO": "SECTOR"}).reset_index(drop=True)

    st.dataframe(
        display_df,
        use_container_width=True,
        height=440,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width=60),
            "NOMBRE DE LA CONVOCATORIA": st.column_config.TextColumn("Convocatoria", width=300),
            "SEGMENTO": st.column_config.TextColumn("Segmento", width=180),
            "ESTADO": st.column_config.TextColumn("Estado", width=100),
            "SECTOR": st.column_config.TextColumn("Sector", width=220),
        },
        hide_index=True,
    )

    st.markdown('<div class="section-title">Detalle por sector</div>', unsafe_allow_html=True)
    sel_det = st.selectbox("Selecciona un sector", sectores_all, key="det_sector")
    if sel_det:
        det = exploded_df[exploded_df["SECTOR_LIMPIO"] == sel_det]
        if sel_estados:
            det = det[det["ESTADO"].isin(sel_estados)]
        det_cols = [c for c in ["ID","NOMBRE DE LA CONVOCATORIA","SEGMENTO","ESTADO",
                                 "FECHA DE APERTURA","FECHA DE CIERRE","MONTO POR PROYECTO"]
                    if c in det.columns]
        st.caption(f"{len(det)} convocatoria(s) en el sector **{sel_det}**")
        st.dataframe(det[det_cols].reset_index(drop=True), use_container_width=True,
                     height=300, hide_index=True)


# ───────────── TAB 3: REPORTE EXCEL ──────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-title">Generar reporte Excel</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-sub">
      Una hoja por sector · Encabezados <span style="background:#196B24;color:white;
      padding:1px 8px;border-radius:4px;font-size:0.74rem">#196B24</span> ·
      Tablas de Excel nombradas por sector · Filas blancas
    </div>""", unsafe_allow_html=True)

    export_mode = st.radio(
        "Datos a exportar",
        ["Todos los registros", "Solo los registros filtrados"],
        horizontal=True,
    )
    export_df = exp_f if export_mode == "Solo los registros filtrados" else exploded_df

    preview = (
        export_df.groupby("SECTOR_LIMPIO")["ID"]
        .nunique().reset_index()
        .rename(columns={"SECTOR_LIMPIO": "Sector", "ID": "N° Convocatorias"})
        .sort_values("Sector")
    )
    with st.expander(
        f"Vista previa — {preview['Sector'].nunique()} hojas · "
        f"{preview['N° Convocatorias'].sum()} registros totales"
    ):
        st.dataframe(preview, use_container_width=True, hide_index=True, height=300)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Generar reporte", type="primary"):
        with st.spinner("Construyendo archivo Excel…"):
            excel_bytes = build_excel(export_df)
        st.success("Reporte generado correctamente.")
        st.download_button(
            label="Descargar Convocatorias_por_Sector.xlsx",
            data=excel_bytes,
            file_name="Convocatorias_por_Sector.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

