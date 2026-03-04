import io
import re
import math
import pandas as pd
import streamlit as st
from openpyxl import load_workbook
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Convocatorias SDP",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { 
    font-family: 'Plus Jakarta Sans', sans-serif; 
}

/* Sidebar */
section[data-testid="stSidebar"] > div:first-child {
    background: #0E1117 !important;
    border-right: 1px solid #1E293B;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 1px solid #1E293B; 
    gap: 32px;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 500; 
    font-size: 0.95rem;
    padding: 12px 0px;
    background: transparent;
    color: #94A3B8;
}
.stTabs [aria-selected="true"] {
    color: #4ADE80 !important;
    border-bottom: 2px solid #4ADE80 !important;
}

/* Download & Primary buttons */
.stDownloadButton > button, .stButton > button[kind="primary"] {
    background: #4ADE80 !important; 
    color: #064E3B !important;
    border: none !important; 
    border-radius: 6px !important;
    font-weight: 600 !important; 
    padding: 10px 24px !important;
    transition: all 0.2s ease-in-out;
}
.stDownloadButton > button:hover, .stButton > button[kind="primary"]:hover { 
    background: #22C55E !important; 
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.2);
}

/* Dataframe header styling override */
[data-testid="stDataFrame"] {
    border: 1px solid #1E293B;
    border-radius: 8px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
TABLE_NAME = "SeguimientoConvocatorias"
INVALID_SECTORS = {"", "none", "nan", "n/d", "no especifica",
                   "verificar", "formuladores-evaluadores", "varios"}

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
GREENS = ["#4ADE80", "#22C55E", "#16A34A", "#15803D", "#166534",
          "#14532D", "#064E3B", "#022C22", "#6EE7B7", "#A7F3D0"]


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
def _read_named_table(file_bytes: bytes, table_name: str) -> pd.DataFrame:
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    for ws in wb.worksheets:
        for tbl in ws.tables.values():
            if tbl.name == table_name:
                data = list(ws[tbl.ref])
                headers = [cell.value for cell in data[0]]
                rows = [[cell.value for cell in row] for row in data[1:]]
                return pd.DataFrame(rows, columns=headers)
    raise ValueError(
        f"No se encontró la tabla '{table_name}' en el archivo. "
        f"Verifica que el Excel contenga una tabla con ese nombre exacto."
    )


@st.cache_data(show_spinner=False)
def load_data(file_bytes: bytes):
    df = _read_named_table(file_bytes, TABLE_NAME)

    df["SECTOR"] = df["SECTOR"].astype(str).str.strip()
    df = df[~df["SECTOR"].str.lower().isin(INVALID_SECTORS)].copy()
    df = df.reset_index(drop=True)

    base = df.copy()

    exploded = base.copy()
    exploded["SECTOR"] = exploded["SECTOR"].str.split(" - ")
    exploded = exploded.explode("SECTOR")
    exploded["SECTOR"] = exploded["SECTOR"].str.strip()
    exploded = exploded[~exploded["SECTOR"].str.lower().isin(INVALID_SECTORS)]
    exploded = exploded.reset_index(drop=True)

    return base, exploded


# ══════════════════════════════════════════════════════════════════════════════
# EXCEL REPORT BUILDER
# ══════════════════════════════════════════════════════════════════════════════
def build_excel(exploded: pd.DataFrame) -> bytes:
    H_FILL = PatternFill("solid", fgColor="064E3B")
    H_FONT = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    T_FONT = Font(bold=True, color="064E3B", name="Arial", size=13)
    C_FONT = Font(name="Arial", size=9)
    WHITE  = PatternFill("solid", fgColor="FFFFFF")
    THIN   = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    wb = Workbook()
    wb.remove(wb.active)
    sectores = sorted(exploded["SECTOR"].unique())
    available_cols = [c for c in COLS_REPORT if c in exploded.columns]

    wi = wb.create_sheet("Índice")
    wi.sheet_view.showGridLines = False
    wi["A1"] = "Convocatorias por Sector"
    wi["A1"].font = Font(bold=True, color="064E3B", name="Arial", size=15)
    for ci, label in enumerate(["SECTOR", "N° CONVOCATORIAS"], 1):
        c = wi.cell(row=3, column=ci, value=label)
        c.font = H_FONT; c.fill = H_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = THIN
    for i, s in enumerate(sectores, 4):
        n = exploded[exploded["SECTOR"] == s]["ID"].nunique()
        for ci, val in enumerate([s, n], 1):
            c = wi.cell(row=i, column=ci, value=val)
            c.font = C_FONT; c.fill = WHITE; c.border = THIN
            c.alignment = Alignment(
                horizontal="center" if ci == 2 else "left", vertical="center"
            )
    wi.column_dimensions["A"].width = 32
    wi.column_dimensions["B"].width = 20
    tbl_i = Table(displayName="Indice", ref=f"A3:B{3 + len(sectores)}")
    tbl_i.tableStyleInfo = TableStyleInfo(name="TableStyleMedium7", showRowStripes=False)
    wi.add_table(tbl_i)

    for sector in sectores:
        sname = sector[:31].replace("/", "-").replace("\\", "-").replace(":", "")
        ws = wb.create_sheet(sname)
        ws.sheet_view.showGridLines = False

        ws.merge_cells(start_row=1, start_column=1,
                       end_row=1, end_column=len(available_cols))
        tc = ws.cell(row=1, column=1, value=f"Sector: {sector}")
        tc.font = T_FONT
        tc.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[1].height = 22

        subset = (exploded[exploded["SECTOR"] == sector][available_cols]
                  .reset_index(drop=True))
        nc = ws.cell(row=2, column=1, value=f"{len(subset)} convocatoria(s)")
        nc.font = Font(name="Arial", size=9, color="666666", italic=True)
        ws.row_dimensions[2].height = 14

        for ci, col in enumerate(available_cols, 1):
            c = ws.cell(row=3, column=ci, value=col)
            c.font = H_FONT; c.fill = H_FILL
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = THIN
        ws.row_dimensions[3].height = 30

        for ri, (_, row) in enumerate(subset.iterrows(), 4):
            for ci, col in enumerate(available_cols, 1):
                val = row[col]
                if pd.isna(val): val = ""
                c = ws.cell(row=ri, column=ci, value=val)
                c.font = C_FONT; c.fill = WHITE; c.border = THIN
                c.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws.row_dimensions[ri].height = 45

        for ci, col in enumerate(available_cols, 1):
            ws.column_dimensions[get_column_letter(ci)].width = COL_WIDTHS.get(col, 15)

        ws.freeze_panes = "A4"
        last_col = get_column_letter(len(available_cols))
        tname = "T_" + re.sub(r"[^A-Za-z0-9_]", "_", sector)[:28]
        tbl = Table(displayName=tname,
                    ref=f"A3:{last_col}{3 + len(subset)}")
        tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium7", showRowStripes=False)
        ws.add_table(tbl)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# HTML CHART HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def bar_chart(data: pd.Series, title: str, max_bars: int = 25) -> str:
    data = data.sort_values(ascending=False).head(max_bars)
    max_val = data.max() or 1
    rows = ""
    for i, (label, val) in enumerate(data.items()):
        pct = round((val / max_val) * 100, 1)
        intensity = max(0.6, 1 - i * 0.03)
        color = f'rgba(74, 222, 128, {intensity:.2f})'
        rows += (
            '<div style="display:flex;align-items:center;margin-bottom:12px;gap:16px">'
            '<div style="width:180px;font-size:0.8rem;color:#94A3B8;text-align:right;'
            'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0" '
            f'title="{label}">{label}</div>'
            '<div style="flex:1;background:#0F172A;border-radius:4px;height:20px;position:relative">'
            f'<div style="width:{pct}%;background:{color};height:100%;border-radius:4px; transition: width 1s ease;"></div>'
            '<span style="position:absolute;right:8px;top:2px;font-size:0.75rem;'
            f'font-weight:600;color:#F8FAFC">{val}</span>'
            '</div></div>'
        )
    return (
        '<div style="background:#111827;border:1px solid #1E293B;border-radius:12px;padding:24px;box-shadow:0 4px 6px -1px rgba(0, 0, 0, 0.1);">'
        '<div style="font-size:1.1rem;color:#F8FAFC;font-weight:600;'
        f'margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid #1E293B">{title}</div>'
        f'{rows}</div>'
    )


def donut_chart(data: pd.Series, title: str, top_n: int = 8) -> str:
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
        x1, y1 = cx + r * math.cos(a1r), cy + r * math.sin(a1r)
        x2, y2 = cx + r * math.cos(a2r), cy + r * math.sin(a2r)
        ix1, iy1 = cx + ir * math.cos(a2r), cy + ir * math.sin(a2r)
        ix2, iy2 = cx + ir * math.cos(a1r), cy + ir * math.sin(a1r)
        large = 1 if sweep > 180 else 0
        color = GREENS[i % len(GREENS)]
        paths += (
            f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {large},1 {x2:.1f},{y2:.1f} '
            f'L{ix1:.1f},{iy1:.1f} A{ir},{ir} 0 {large},0 {ix2:.1f},{iy2:.1f} Z" '
            f'fill="{color}" stroke="#111827" stroke-width="2"/>'
        )
        angle = end

    legend = ""
    for i, (label, val) in enumerate(top.items()):
        pct = round(val / total * 100, 1)
        color = GREENS[i % len(GREENS)]
        legend += (
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
            f'<div style="width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0"></div>'
            '<div style="font-size:0.8rem;color:#94A3B8;flex:1;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis" title="{label}">{label}</div>'
            f'<div style="font-size:0.8rem;font-weight:600;color:#F8FAFC">{pct}%</div>'
            '</div>'
        )

    svg = (
        f'<svg width="150" height="150" viewBox="0 0 150 150">{paths}'
        f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" font-size="20" '
        f'fill="#F8FAFC" font-weight="700">{total}</text>'
        f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" font-size="9" '
        f'fill="#64748B" font-weight="500">TOTAL</text></svg>'
    )

    return (
        '<div style="background:#111827;border:1px solid #1E293B;border-radius:12px;padding:24px;box-shadow:0 4px 6px -1px rgba(0, 0, 0, 0.1);">'
        '<div style="font-size:1.1rem;color:#F8FAFC;font-weight:600;'
        f'margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid #1E293B">{title}</div>'
        '<div style="display:flex;gap:24px;align-items:center">'
        f'<div style="flex-shrink:0">{svg}</div>'
        f'<div style="flex:1;overflow:hidden">{legend}</div>'
        '</div></div>'
    )


def metric_card(label: str, value, sub: str) -> str:
    return (
        '<div style="background:#111827;border:1px solid #1E293B;border-left:4px solid #4ADE80;'
        'border-radius:10px;padding:24px;box-shadow:0 2px 4px rgba(0,0,0,0.05);">'
        '<div style="font-size:0.75rem;letter-spacing:0.05em;text-transform:uppercase;'
        f'color:#94A3B8;font-weight:600;margin-bottom:8px">{label}</div>'
        '<div style="font-size:2.2rem;font-weight:700;'
        f'color:#F8FAFC;line-height:1">{value}</div>'
        f'<div style="font-size:0.8rem;color:#64748B;margin-top:8px;font-weight:500;">{sub}</div>'
        '</div>'
    )


def section_title(text: str, sub: str = "") -> str:
    sub_html = (
        f'<div style="font-size:0.9rem;color:#94A3B8;margin-bottom:24px">{sub}</div>'
        if sub else ""
    )
    return (
        f'<div style="font-size:1.5rem;color:#F8FAFC;font-weight:600;'
        f'margin:32px 0 8px;padding-bottom:12px;border-bottom:1px solid #1E293B;">{text}</div>'
        f'{sub_html}'
    )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div style="padding:10px 0 24px">'
        '<div style="font-size:1.4rem;font-weight:700;'
        'color:#F8FAFC;line-height:1.25">Convocatorias</div>'
        '<div style="color:#64748B;font-size:0.85rem;font-weight:500;margin-top:6px">'
        'SDP · Reporte Interactivo</div></div>'
        '<hr style="border-color:#1E293B;margin-bottom:24px">',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Cargar archivo Excel",
        type=["xlsx"],
        help=(
            "Debe contener la tabla 'SeguimientoConvocatorias' "
            "con la columna SECTOR ya estandarizada."
        ),
    )

    if uploaded:
        st.markdown(
            '<hr style="border-color:#1E293B;margin:24px 0 16px">'
            '<div style="font-size:0.75rem;letter-spacing:0.05em;text-transform:uppercase;'
            'color:#94A3B8;font-weight:600;margin-bottom:12px">Filtros de Análisis</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════════════════
if not uploaded:
    st.markdown(
        '<div style="background:#111827;border:1px solid #1E293B;'
        'border-radius:16px;padding:48px;margin-bottom:32px;text-align:center;">'
        '<div style="font-size:2.2rem;font-weight:700;'
        'color:#F8FAFC;margin:0 0 12px;line-height:1.2">Reporte de Convocatorias</div>'
        '<div style="color:#94A3B8;font-size:1rem;font-weight:400;max-width:600px;margin:0 auto;">'
        'Carga el archivo Excel con la tabla SeguimientoConvocatorias '
        'para generar el dashboard analítico y el reporte automatizado por sector.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    
    c1, c2, c3 = st.columns(3)
    for col, lbl, sub in [
        (c1, "Dashboard",     "Gráficas de distribución por sector, segmento y estado."),
        (c2, "Explorador",    "Tabla de datos interactiva filtrable con detalle por sector."),
        (c3, "Reporte Excel", "Generación de hojas por sector con formato profesional."),
    ]:
        col.markdown(
            '<div style="background:#111827;border:1px solid #1E293B;border-top:4px solid #4ADE80;'
            'border-radius:10px;padding:24px;height:100%;">'
            '<div style="font-size:0.85rem;letter-spacing:0.05em;text-transform:uppercase;'
            f'color:#F8FAFC;font-weight:700;margin-bottom:8px">{lbl}</div>'
            f'<div style="font-size:0.9rem;color:#94A3B8;line-height:1.5;">{sub}</div></div>',
            unsafe_allow_html=True,
        )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("Procesando datos..."):
    file_bytes = uploaded.read()
    try:
        base_df, exploded_df = load_data(file_bytes)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Error inesperado al leer el archivo: {e}")
        st.stop()

if base_df.empty:
    st.warning("La tabla no contiene registros válidos en la columna SECTOR.")
    st.stop()

sectores_all  = sorted(exploded_df["SECTOR"].unique())
segmentos_all = sorted(base_df["SEGMENTO"].dropna().unique()) if "SEGMENTO" in base_df.columns else []
estados_all   = sorted(base_df["ESTADO"].dropna().unique())   if "ESTADO"   in base_df.columns else []

# ── Filtros en sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    sel_sectores  = st.multiselect("Sector Temático", sectores_all,  placeholder="Todos los sectores")
    sel_segmentos = st.multiselect("Segmento", segmentos_all, placeholder="Todos los segmentos") if segmentos_all else []
    sel_estados   = st.multiselect("Estado",   estados_all,   placeholder="Todos los estados") if estados_all   else []

exp_f  = exploded_df.copy()
base_f = base_df.copy()

if sel_sectores:
    exp_f  = exp_f[exp_f["SECTOR"].isin(sel_sectores)]
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
st.markdown(
    '<div style="background:#111827;border:1px solid #1E293B;'
    'border-radius:12px;padding:32px 40px;margin-bottom:32px;display:flex;justify-content:space-between;align-items:center;">'
    '<div><div style="font-size:1.8rem;font-weight:700;'
    'color:#F8FAFC;margin:0 0 8px;line-height:1.2">Análisis de Convocatorias</div>'
    '<div style="color:#94A3B8;font-size:0.95rem;font-weight:400">'
    f'Fuente: {uploaded.name}</div></div>'
    f'<div style="text-align:right;"><div style="color:#4ADE80;font-weight:700;font-size:1.2rem;">{len(base_df)}</div>'
    '<div style="color:#64748B;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.05em;">Registros Totales</div></div></div>',
    unsafe_allow_html=True,
)

n_conv     = base_f['ID'].nunique() if 'ID' in base_f.columns else len(base_f)
n_vigentes = (
    len(base_f[base_f["ESTADO"].astype(str).str.upper().str.contains("VIGENTE", na=False)])
    if "ESTADO" in base_f.columns else 0
)
pct_vig    = round(n_vigentes / max(n_conv, 1) * 100)
n_sectores = exp_f["SECTOR"].nunique()  
n_segmentos = base_f["SEGMENTO"].nunique() if "SEGMENTO" in base_f.columns else 0

k1, k2, k3, k4 = st.columns(4)
k1.markdown(metric_card("Convocatorias", n_conv,     "Registros únicos evaluados"), unsafe_allow_html=True)
k2.markdown(metric_card("Vigentes",      n_vigentes, f"{pct_vig}% del total actual"), unsafe_allow_html=True)
k3.markdown(metric_card("Sectores",      n_sectores, "Categorías activas filtradas"), unsafe_allow_html=True)
k4.markdown(metric_card("Segmentos",     n_segmentos,"Tipos de convocatoria"), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["Dashboard General", "Explorador de Datos", "Exportación de Reportes"])


# ─── TAB 1: DASHBOARD ────────────────────────────────────────────────────────
with tab1:
    sector_counts = exp_f.groupby("SECTOR")["ID"].nunique()

    st.markdown(
        section_title("Distribución Temática",
                       "Análisis del volumen de convocatorias clasificado por sector"),
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns([1.5, 1])
    with col_a:
        st.markdown(bar_chart(sector_counts, "Volumen por Sector"), unsafe_allow_html=True)
    with col_b:
        st.markdown(donut_chart(sector_counts, "Distribución Principal (Top 8)"), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if "SEGMENTO" in base_f.columns and not base_f.empty:
            st.markdown(
                donut_chart(base_f["SEGMENTO"].value_counts(), "Proporción por Segmento"),
                unsafe_allow_html=True,
            )

    if "ESTADO" in base_f.columns and not base_f.empty:
        st.markdown(section_title("Monitoreo de Estado", "Condición actual operativa de los registros"), unsafe_allow_html=True)
        st.markdown(
            bar_chart(base_f["ESTADO"].value_counts(), "Conteo por Estado Actual"),
            unsafe_allow_html=True,
        )


# ─── TAB 2: EXPLORADOR ───────────────────────────────────────────────────────
with tab2:
    st.markdown(
        section_title("Base de Datos Filtrada",
                       f"Visualizando {len(base_f)} registros según los criterios seleccionados"),
        unsafe_allow_html=True,
    )

    id_col = "ID" if "ID" in base_f.columns else base_f.columns[0]
    show_cols = [c for c in [
        id_col, "NOMBRE DE LA CONVOCATORIA", "SEGMENTO",
        "ESTADO", "FECHA DE APERTURA", "FECHA DE CIERRE", "SECTOR",
    ] if c in base_f.columns]

    st.dataframe(
        base_f[show_cols].reset_index(drop=True),
        use_container_width=True,
        height=400,
        hide_index=True,
    )

    st.markdown(section_title("Análisis Detallado por Sector", "Profundiza en los datos de una categoría específica"), unsafe_allow_html=True)
    sel_det = st.selectbox("Seleccionar sector para inspección", sectores_all, key="det_sector")
    
    if sel_det:
        det = exploded_df[exploded_df["SECTOR"] == sel_det]
        if sel_estados and "ESTADO" in det.columns:
            det = det[det["ESTADO"].isin(sel_estados)]
        det_cols = [c for c in [
            id_col, "NOMBRE DE LA CONVOCATORIA", "SEGMENTO", "ESTADO",
            "FECHA DE APERTURA", "FECHA DE CIERRE", "MONTO POR PROYECTO",
        ] if c in det.columns]
        
        st.markdown(f'<div style="color:#94A3B8; font-size:0.9rem; margin-bottom:16px;">Mostrando <b>{len(det)}</b> registro(s) correspondientes a <b>{sel_det}</b></div>', unsafe_allow_html=True)
        
        st.dataframe(
            det[det_cols].reset_index(drop=True),
            use_container_width=True, height=300, hide_index=True,
        )


# ─── TAB 3: REPORTE EXCEL ────────────────────────────────────────────────────
with tab3:
    st.markdown(
        section_title(
            "Módulo de Exportación Excel",
            "Genera un reporte consolidado estructurando automáticamente una hoja por sector temático."
        ),
        unsafe_allow_html=True,
    )

    export_mode = st.radio(
        "Alcance de los datos a exportar",
        ["Exportar la base de datos completa", "Exportar únicamente registros filtrados"],
        horizontal=True,
    )
    
    export_df = exp_f if export_mode == "Exportar únicamente registros filtrados" else exploded_df

    preview = (
        export_df.groupby("SECTOR")["ID"]
        .nunique().reset_index()
        .rename(columns={"SECTOR": "Sector", "ID": "N° Convocatorias"})
        .sort_values("Sector")
    )
    
    with st.expander(
        f"Ver Estructura del Documento — {preview['Sector'].nunique()} hojas planificadas"
    ):
        st.dataframe(preview, use_container_width=True, hide_index=True, height=250)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Construir Documento Excel", type="primary"):
        with st.spinner("Estructurando y dando formato al archivo..."):
            excel_bytes = build_excel(export_df)
        st.success("El reporte se ha empaquetado y está listo para descargar.")
        st.download_button(
            label="Descargar Reporte (Convocatorias_por_Sector.xlsx)",
            data=excel_bytes,
            file_name="Convocatorias_por_Sector.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
