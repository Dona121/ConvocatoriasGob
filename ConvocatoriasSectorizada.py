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

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

section[data-testid="stSidebar"] > div:first-child {
    background: #0d1f12;
    border-right: 1px solid #196B24;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div { color: #e8f5e9 !important; }

.stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid #196B24; gap: 4px; }
.stTabs [data-baseweb="tab"] {
    font-weight: 600; font-size: 0.85rem;
    color: #6a8c6a; border-radius: 6px 6px 0 0; padding: 8px 20px;
}
.stTabs [aria-selected="true"] {
    background: #196B24 !important; color: white !important;
}

.stDownloadButton > button {
    background: #196B24 !important; color: white !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; padding: 10px 24px !important;
}
.stDownloadButton > button:hover { background: #0d4a18 !important; }

div[data-testid="stDataFrame"] thead tr th {
    background-color: #196B24 !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
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
GREEN = "#196B24"
GREENS = ["#196B24","#1a7a27","#1e8c2e","#22a034","#27b33b",
          "#2ec644","#3ddb52","#57e368","#7aeb87","#9df2a7"]


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data(file_bytes: bytes) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Expects a clean Excel file where SECTOR column already has
    standardized values like 'Desarrollo - Competitividad'.
    Returns (base_df, exploded_df).
    """
    df = pd.read_excel(io.BytesIO(file_bytes))

    # Accept either 'SECTOR' or 'SECTOR_LIMPIO' as the sector column
    if "SECTOR_LIMPIO" in df.columns and "SECTOR" not in df.columns:
        df = df.rename(columns={"SECTOR_LIMPIO": "SECTOR"})
    elif "SECTOR_LIMPIO" in df.columns:
        # Both exist — prefer SECTOR_LIMPIO as the clean one
        df["SECTOR"] = df["SECTOR_LIMPIO"]
        df = df.drop(columns=["SECTOR_LIMPIO"])

    base = df.dropna(subset=["SECTOR"]).copy()

    exploded = base.copy()
    exploded["SECTOR"] = exploded["SECTOR"].str.split(" - ")
    exploded = exploded.explode("SECTOR")
    exploded["SECTOR"] = exploded["SECTOR"].str.strip()

    return base, exploded


# ── Excel report builder ───────────────────────────────────────────────────────
def build_excel(exploded: pd.DataFrame) -> bytes:
    H_FILL = PatternFill("solid", fgColor="196B24")
    H_FONT = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    T_FONT = Font(bold=True, color="196B24", name="Arial", size=13)
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

    # Index sheet
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
        n = exploded[exploded["SECTOR"] == s]["ID"].nunique()
        for ci, val in enumerate([s, n], 1):
            c = wi.cell(row=i, column=ci, value=val)
            c.font = C_FONT; c.fill = WHITE; c.border = THIN
            c.alignment = Alignment(
                horizontal="center" if ci == 2 else "left", vertical="center"
            )
    wi.column_dimensions["A"].width = 30
    wi.column_dimensions["B"].width = 20
    tbl_i = Table(displayName="Indice", ref=f"A3:B{3 + len(sectores)}")
    tbl_i.tableStyleInfo = TableStyleInfo(name="TableStyleMedium7", showRowStripes=False)
    wi.add_table(tbl_i)

    # Per-sector sheets
    available_cols = [c for c in COLS_REPORT if c in exploded.columns]
    for sector in sectores:
        sname = sector[:31].replace("/", "-").replace("\\", "-").replace(":", "")
        ws = wb.create_sheet(sname)
        ws.sheet_view.showGridLines = False

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(available_cols))
        tc = ws.cell(row=1, column=1, value=f"Sector: {sector}")
        tc.font = T_FONT
        tc.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[1].height = 22

        subset = exploded[exploded["SECTOR"] == sector][available_cols].reset_index(drop=True)
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
        tbl = Table(displayName=tname, ref=f"A3:{last_col}{3 + len(subset)}")
        tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium7", showRowStripes=False)
        ws.add_table(tbl)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Chart helpers (pure HTML, rendered with st.markdown unsafe_allow_html) ─────
def bar_chart(data: pd.Series, title: str, max_bars: int = 25) -> str:
    data = data.sort_values(ascending=False).head(max_bars)
    max_val = data.max() or 1
    rows = ""
    for i, (label, val) in enumerate(data.items()):
        pct = round((val / max_val) * 100, 1)
        color = GREENS[i % len(GREENS)]
        rows += (
            f'<div style="display:flex;align-items:center;margin-bottom:8px;gap:10px">'
            f'<div style="width:175px;font-size:0.77rem;color:#2d4a2d;text-align:right;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0" '
            f'title="{label}">{label}</div>'
            f'<div style="flex:1;background:#f0f0f0;border-radius:4px;height:24px;position:relative">'
            f'<div style="width:{pct}%;background:{color};height:100%;border-radius:4px"></div>'
            f'<span style="position:absolute;right:8px;top:4px;font-size:0.73rem;'
            f'font-weight:700;color:#1a1a1a">{val}</span>'
            f'</div></div>'
        )
    return (
        f'<div style="background:white;border:1px solid #e0ede0;border-radius:10px;padding:22px 24px 18px">'
        f'<div style="font-family:\'DM Serif Display\',serif;font-size:1rem;color:#0d1f12;'
        f'margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #196B24">{title}</div>'
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
            f'fill="{color}" stroke="white" stroke-width="2"/>'
        )
        angle = end

    legend = ""
    for i, (label, val) in enumerate(top.items()):
        pct = round(val / total * 100, 1)
        color = GREENS[i % len(GREENS)]
        legend += (
            f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px">'
            f'<div style="width:9px;height:9px;border-radius:50%;background:{color};flex-shrink:0"></div>'
            f'<div style="font-size:0.74rem;color:#2d4a2d;flex:1;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis" title="{label}">{label}</div>'
            f'<div style="font-size:0.74rem;font-weight:700;color:#196B24">{pct}%</div>'
            f'</div>'
        )

    svg = (
        f'<svg width="150" height="150" viewBox="0 0 150 150">{paths}'
        f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-size="17" '
        f'font-family="DM Serif Display" fill="#0d1f12" font-weight="bold">{total}</text>'
        f'<text x="{cx}" y="{cy+18}" text-anchor="middle" font-size="8.5" '
        f'font-family="DM Sans" fill="#6a8c6a">total</text></svg>'
    )

    return (
        f'<div style="background:white;border:1px solid #e0ede0;border-radius:10px;padding:22px 24px 18px">'
        f'<div style="font-family:\'DM Serif Display\',serif;font-size:1rem;color:#0d1f12;'
        f'margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #196B24">{title}</div>'
        f'<div style="display:flex;gap:20px;align-items:center">'
        f'<div style="flex-shrink:0">{svg}</div>'
        f'<div style="flex:1;overflow:hidden">{legend}</div>'
        f'</div></div>'
    )


def metric_card(label: str, value, sub: str) -> str:
    return (
        f'<div style="background:white;border:1px solid #e0ede0;border-left:4px solid #196B24;'
        f'border-radius:8px;padding:20px 22px;margin-bottom:8px">'
        f'<div style="font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:#6a8c6a;font-weight:600;margin-bottom:4px">{label}</div>'
        f'<div style="font-family:\'DM Serif Display\',serif;font-size:2.1rem;'
        f'color:#0d1f12;line-height:1">{value}</div>'
        f'<div style="font-size:0.77rem;color:#8aab8a;margin-top:4px">{sub}</div>'
        f'</div>'
    )


def section_title(text: str, sub: str = "") -> str:
    sub_html = f'<div style="font-size:0.82rem;color:#6a8c6a;margin-bottom:16px">{sub}</div>' if sub else ""
    return (
        f'<div style="font-family:\'DM Serif Display\',serif;font-size:1.4rem;color:#0d1f12;'
        f'margin:28px 0 6px;padding-bottom:8px;border-bottom:2px solid #196B24">{text}</div>'
        f'{sub_html}'
    )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div style="padding:18px 0 20px">'
        '<div style="font-family:\'DM Serif Display\',serif;font-size:1.4rem;'
        'color:white;line-height:1.25">📁 Convocatorias</div>'
        '<div style="color:#a5d6a7;font-size:0.82rem;font-weight:300;margin-top:4px">'
        'SDP · Reporte Interactivo</div></div>'
        '<hr style="border-color:#196B24;margin-bottom:20px">',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Cargar archivo Excel",
        type=["xlsx"],
        help="Archivo con la columna SECTOR ya estandarizada",
    )

    if uploaded:
        st.markdown(
            '<hr style="border-color:#196B24;margin:18px 0 14px">'
            '<div style="font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;'
            'color:#a5d6a7;font-weight:600;margin-bottom:10px">Filtros</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════════════════
if not uploaded:
    st.markdown(
        '<div style="background:linear-gradient(135deg,#0d1f12 0%,#196B24 100%);'
        'border-radius:12px;padding:38px 42px 34px;margin-bottom:28px">'
        '<div style="font-family:\'DM Serif Display\',serif;font-size:2rem;'
        'color:white;margin:0 0 8px;line-height:1.2">Reporte de Convocatorias</div>'
        '<div style="color:#a5d6a7;font-size:0.88rem;font-weight:300">'
        'Carga el archivo Excel desde el panel lateral para generar el dashboard y el reporte por sector.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    for col, lbl, sub in [
        (c1, "Dashboard", "Gráficas de distribución por sector, segmento y estado"),
        (c2, "Explorador", "Tabla filtrable con detalle por sector"),
        (c3, "Reporte Excel", "Una hoja por sector, tablas con nombre, encabezados verdes"),
    ]:
        col.markdown(
            f'<div style="background:white;border:1px solid #e0ede0;border-left:4px solid #196B24;'
            f'border-radius:8px;padding:20px 22px">'
            f'<div style="font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;'
            f'color:#6a8c6a;font-weight:600;margin-bottom:6px">{lbl}</div>'
            f'<div style="font-size:0.83rem;color:#4a6a4a">{sub}</div></div>',
            unsafe_allow_html=True,
        )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("Procesando datos…"):
    file_bytes = uploaded.read()
    try:
        base_df, exploded_df = load_data(file_bytes)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()

if base_df.empty:
    st.warning("El archivo no contiene registros válidos en la columna SECTOR.")
    st.stop()

sectores_all  = sorted(exploded_df["SECTOR"].unique())
segmentos_all = sorted(base_df["SEGMENTO"].dropna().unique()) if "SEGMENTO" in base_df.columns else []
estados_all   = sorted(base_df["ESTADO"].dropna().unique()) if "ESTADO" in base_df.columns else []

# Filters
with st.sidebar:
    sel_sectores  = st.multiselect("Sector",   sectores_all,  placeholder="Todos")
    sel_segmentos = st.multiselect("Segmento", segmentos_all, placeholder="Todos") if segmentos_all else []
    sel_estados   = st.multiselect("Estado",   estados_all,   placeholder="Todos") if estados_all else []

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
# HERO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div style="background:linear-gradient(135deg,#0d1f12 0%,#196B24 100%);'
    f'border-radius:12px;padding:34px 40px 30px;margin-bottom:24px">'
    f'<div style="font-family:\'DM Serif Display\',serif;font-size:1.9rem;'
    f'color:white;margin:0 0 6px;line-height:1.2">Reporte de Convocatorias</div>'
    f'<div style="color:#a5d6a7;font-size:0.87rem;font-weight:300">'
    f'{uploaded.name} &nbsp;·&nbsp; {len(base_df)} registros &nbsp;·&nbsp; '
    f'{len(sectores_all)} sectores</div></div>',
    unsafe_allow_html=True,
)

# KPIs
n_vigentes = len(base_f[base_f["ESTADO"].str.upper().str.contains("VIGENTE", na=False)]) if "ESTADO" in base_f.columns else 0
pct_vig    = round(n_vigentes / max(len(base_f), 1) * 100)

k1, k2, k3, k4 = st.columns(4)
k1.markdown(metric_card("Convocatorias", len(base_f), "en la selección actual"), unsafe_allow_html=True)
k2.markdown(metric_card("Vigentes", n_vigentes, f"{pct_vig}% del total filtrado"), unsafe_allow_html=True)
k3.markdown(metric_card("Sectores", exp_f["SECTOR"].nunique(), "categorías activas"), unsafe_allow_html=True)
k4.markdown(metric_card("Segmentos", base_f["SEGMENTO"].nunique() if "SEGMENTO" in base_f.columns else "—", "tipos de convocatoria"), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["Dashboard", "Explorador", "Reporte Excel"])


# ─── TAB 1: DASHBOARD ────────────────────────────────────────────────────────
with tab1:
    sector_counts = exp_f.groupby("SECTOR")["ID"].nunique().rename("n")

    st.markdown(section_title("Distribución por sector",
        "Número único de convocatorias asociadas a cada sector"), unsafe_allow_html=True)

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown(bar_chart(sector_counts, "Convocatorias por sector"), unsafe_allow_html=True)
    with col_b:
        st.markdown(donut_chart(sector_counts, "Top 8 sectores"), unsafe_allow_html=True)
        if "SEGMENTO" in base_f.columns and not base_f.empty:
            seg_c = base_f["SEGMENTO"].value_counts()
            st.markdown(donut_chart(seg_c, "Por segmento"), unsafe_allow_html=True)

    if "ESTADO" in base_f.columns and not base_f.empty:
        st.markdown(section_title("Estado de las convocatorias"), unsafe_allow_html=True)
        est_c = base_f["ESTADO"].value_counts()
        st.markdown(bar_chart(est_c, "Por estado"), unsafe_allow_html=True)


# ─── TAB 2: EXPLORADOR ───────────────────────────────────────────────────────
with tab2:
    st.markdown(section_title("Listado de convocatorias",
        f"{len(base_f)} registros con los filtros aplicados"), unsafe_allow_html=True)

    id_col = "ID" if "ID" in base_f.columns else base_f.columns[0]
    show_cols = [c for c in [
        id_col, "NOMBRE DE LA CONVOCATORIA", "SEGMENTO",
        "ESTADO", "FECHA DE APERTURA", "FECHA DE CIERRE", "SECTOR"
    ] if c in base_f.columns]

    st.dataframe(
        base_f[show_cols].reset_index(drop=True),
        use_container_width=True,
        height=440,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width=60),
            "NOMBRE DE LA CONVOCATORIA": st.column_config.TextColumn("Convocatoria", width=300),
            "SEGMENTO": st.column_config.TextColumn("Segmento", width=180),
            "ESTADO": st.column_config.TextColumn("Estado", width=100),
            "SECTOR": st.column_config.TextColumn("Sector", width=220),
        },
    )

    st.markdown(section_title("Detalle por sector"), unsafe_allow_html=True)
    sel_det = st.selectbox("Selecciona un sector", sectores_all, key="det_sector")
    if sel_det:
        det = exploded_df[exploded_df["SECTOR"] == sel_det]
        if sel_estados and "ESTADO" in det.columns:
            det = det[det["ESTADO"].isin(sel_estados)]
        det_cols = [c for c in [
            id_col, "NOMBRE DE LA CONVOCATORIA", "SEGMENTO", "ESTADO",
            "FECHA DE APERTURA", "FECHA DE CIERRE", "MONTO POR PROYECTO"
        ] if c in det.columns]
        st.caption(f"{len(det)} convocatoria(s) en el sector **{sel_det}**")
        st.dataframe(det[det_cols].reset_index(drop=True),
                     use_container_width=True, height=300, hide_index=True)


# ─── TAB 3: REPORTE EXCEL ────────────────────────────────────────────────────
with tab3:
    st.markdown(section_title("Generar reporte Excel",
        "Una hoja por sector · Encabezados #196B24 · Tablas nombradas · Filas blancas"),
        unsafe_allow_html=True)

    export_mode = st.radio(
        "Datos a exportar",
        ["Todos los registros", "Solo los registros filtrados"],
        horizontal=True,
    )
    export_df = exp_f if export_mode == "Solo los registros filtrados" else exploded_df

    preview = (
        export_df.groupby("SECTOR")["ID"]
        .nunique().reset_index()
        .rename(columns={"SECTOR": "Sector", "ID": "N° Convocatorias"})
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
