"""
Convocatorias & Proyectos SDP — Streamlit + Supabase
Schema Django v2.
"""
import io, re, math
import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

st.set_page_config(
    page_title="Convocatorias & Proyectos SDP",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.block-container{
    padding-top:4.5rem!important;padding-left:2rem!important;
    padding-right:2rem!important;padding-bottom:2rem!important;max-width:100%!important;}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#47b1d5;border-radius:10px}
::-webkit-scrollbar-thumb:hover{background:#1754ab}
section[data-testid="stSidebar"]>div:first-child{
    background:#041e35!important;border-right:none!important;
    box-shadow:4px 0 15px rgba(0,0,0,.15);}
section[data-testid="stSidebar"] label{
    color:#ffffff!important;font-size:.8rem!important;
    text-transform:uppercase;letter-spacing:.05em;}
section[data-testid="stSidebar"] .stButton>button{
    background:#1754ab!important;color:#ffffff!important;
    border:none!important;transition:all .3s ease;border-radius:6px!important;}
section[data-testid="stSidebar"] .stButton>button:hover{
    background:#47b1d5!important;color:#041e35!important;}
.stTabs [data-baseweb="tab-list"]{border-bottom:1px solid #e0e0e0;gap:24px}
.stTabs [data-baseweb="tab"]{
    font-weight:600;font-size:.88rem;border-radius:0;
    padding:10px 4px;background:transparent!important;color:#888;border:none;}
.stTabs [aria-selected="true"]{
    background:transparent!important;color:#003d6c!important;
    border-bottom:3px solid #e68878!important;}
.stDownloadButton>button,.stButton>button[kind="primary"]{
    background:#17743d!important;color:white!important;border:none!important;
    border-radius:8px!important;font-weight:600!important;padding:10px 24px!important;
    transition:all .3s ease!important;}
.stDownloadButton>button:hover,.stButton>button[kind="primary"]:hover{
    background:#005931!important;transform:translateY(-2px);
    box-shadow:0 4px 10px rgba(0,89,49,.3)!important;}
[data-testid="stDataFrame"]{
    border-radius:8px;overflow:hidden;
    box-shadow:0 2px 8px rgba(0,0,0,.04);border:1px solid #e0e0e0;}
/* Ficha convocatoria en Relaciones */
.conv-ficha{
    background:#f8fbff;border:1px solid #cce0f5;
    border-left:5px solid #1754ab;border-radius:10px;
    padding:24px 28px;margin-bottom:20px;}
</style>""", unsafe_allow_html=True)

# ── Credentials ───────────────────────────────────────────────────────────────
# FIX #1: typo corregido 'keoredvjr' → 'keordvjr'
try:
    _URL = st.secrets["supabase"]["url"]
    _KEY = st.secrets["supabase"]["key"]
except Exception:
    _URL = "https://keordvjrhcgvnrrvnfa.supabase.co"
    _KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtlb3JlZHZqcmhjZ3ZucnJ2bmZhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI1NzA0MDYsImV4cCI6MjA4ODE0NjQwNn0."
            "h9QNpcbiMXZfeheOAVHtYnC4-n8luCg92s-Xd_BFrZA")

BRAND_COLORS = [
    "#17743d","#1754ab","#cf7000","#47b1d5","#d88c16",
    "#005931","#e68878","#003d6c","#d37e00","#9b5b1e",
]

# ── Supabase ──────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _sb():
    from supabase import create_client
    return create_client(_URL, _KEY)

def _fetch(table, select="*"):
    client = _sb()
    rows, start = [], 0
    while True:
        resp = client.table(table).select(select).range(start, start+999).execute()
        rows.extend(resp.data)
        if len(resp.data) < 1000: break
        start += 1000
    return rows

def _fdate(val):
    if not val: return "—"
    try: return pd.to_datetime(val).strftime("%d/%m/%Y")
    except: return str(val)

def fmt_money(val):
    try:
        v = float(val)
        if v >= 1e12: return f"${v/1e12:.1f}T"
        if v >= 1e9:  return f"${v/1e9:.1f}B"
        if v >= 1e6:  return f"${v/1e6:.1f}M"
        if v >= 1e3:  return f"${v/1e3:.0f}K"
        return f"${v:,.0f}"
    except: return str(val)

# ── UI helpers ────────────────────────────────────────────────────────────────
def _card(content, title=None):
    hdr = (f'<div style="font-family:\'DM Serif Display\',serif;font-size:1.1rem;color:#003d6c;'
           f'margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #e0e0e0">{title}</div>'
           if title else "")
    return (f'<div style="background:#ffffff;border:1px solid #e0e0e0;border-radius:10px;'
            f'padding:22px 24px;box-shadow:0 2px 8px rgba(0,0,0,.02)">{hdr}{content}</div>')

def empty_state(texto):
    return (f'<div style="padding:30px 20px;text-align:center;color:#003d6c;'
            f'background:#f0f8fb;border:1px dashed #47b1d5;border-radius:8px;margin:10px 0">'
            f'{texto}</div>')

def bar_chart(data, title, max_bars=20, fmt_val=None):
    data = data.dropna().sort_values(ascending=False).head(max_bars)
    if data.empty: return ""
    mx = data.max() or 1
    rows = ""
    for i, (label, val) in enumerate(data.items()):
        pct   = round(val/mx*100, 1)
        color = BRAND_COLORS[i % len(BRAND_COLORS)]
        disp  = fmt_val(val) if fmt_val else (f"{int(val):,}" if float(val)==int(float(val)) else f"{val:,.1f}")
        rows += (f'<div style="display:flex;align-items:center;margin-bottom:10px;gap:12px">'
                 f'<div style="width:175px;font-size:.75rem;color:#444;font-weight:500;text-align:right;'
                 f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0" title="{label}">{label}</div>'
                 f'<div style="flex:1;background:#f5f5f5;border-radius:4px;height:24px;position:relative">'
                 f'<div style="width:{pct}%;background:{color};height:100%;border-radius:4px"></div>'
                 f'<span style="position:absolute;right:8px;top:4px;font-size:.72rem;'
                 f'font-weight:700;color:#333">{disp}</span>'
                 f'</div></div>')
    return _card(rows, title)

def donut_chart(data, title, top_n=8):
    data  = data.dropna()
    total = data.sum()
    if total == 0: return ""
    top   = data.sort_values(ascending=False).head(top_n)
    cx = cy = 68; r = 52; ir = 28; angle = -90.0; paths = ""
    for i, (_, val) in enumerate(top.items()):
        sw = (val/total)*360; end = angle+sw
        a1, a2 = math.radians(angle), math.radians(end)
        x1,y1   = cx+r*math.cos(a1),   cy+r*math.sin(a1)
        x2,y2   = cx+r*math.cos(a2),   cy+r*math.sin(a2)
        ix1,iy1 = cx+ir*math.cos(a2),  cy+ir*math.sin(a2)
        ix2,iy2 = cx+ir*math.cos(a1),  cy+ir*math.sin(a1)
        lg = 1 if sw > 180 else 0
        c  = BRAND_COLORS[i % len(BRAND_COLORS)]
        paths += (f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {lg},1 {x2:.1f},{y2:.1f} '
                  f'L{ix1:.1f},{iy1:.1f} A{ir},{ir} 0 {lg},0 {ix2:.1f},{iy2:.1f} Z" '
                  f'fill="{c}" stroke="#ffffff" stroke-width="2"/>')
        angle = end
    legend = ""
    for i, (label, val) in enumerate(top.items()):
        pct = round(val/total*100, 1)
        legend += (f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
                   f'<div style="width:12px;height:12px;border-radius:50%;'
                   f'background:{BRAND_COLORS[i%len(BRAND_COLORS)]};flex-shrink:0"></div>'
                   f'<div style="font-size:.75rem;color:#555;flex:1;white-space:nowrap;overflow:hidden;'
                   f'text-overflow:ellipsis" title="{label}">{label}</div>'
                   f'<div style="font-size:.75rem;font-weight:700;color:#003d6c">{pct}%</div></div>')
    svg = (f'<svg width="100%" style="max-width:140px;height:auto" viewBox="0 0 136 136">{paths}'
           f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-size="18" '
           f'font-family="DM Serif Display" fill="#003d6c" font-weight="bold">{int(total)}</text>'
           f'<text x="{cx}" y="{cy+18}" text-anchor="middle" font-size="9" '
           f'font-family="DM Sans" fill="#888">total</text></svg>')
    inner = (f'<div style="display:flex;gap:20px;align-items:center">'
             f'<div style="flex-shrink:0">{svg}</div>'
             f'<div style="flex:1;overflow:hidden">{legend}</div></div>')
    return _card(inner, title)

def kpi(label, value, sub="", style="white", border_color="#47b1d5", flex="1"):
    if style == "dark-blue":
        bg,tc,lc,sc,bs = "#003d6c","#ffffff","#47b1d5","#a5d6a7","border:none;"
    elif style == "dark-green":
        bg,tc,lc,sc,bs = "#005931","#ffffff","#7aeb87","#a5d6a7","border:none;"
    else:
        bg,tc,lc,sc = "#ffffff","#003d6c","#1754ab","#777"
        bs = f"border:1px solid #e0e0e0;border-left:5px solid {border_color};"
    return (f'<div style="flex:{flex};min-width:130px;background:{bg};{bs}'
            f'border-radius:10px;padding:18px 16px;box-shadow:0 3px 8px rgba(0,0,0,.04);'
            f'display:flex;flex-direction:column;justify-content:center;">'
            f'<div style="font-size:.65rem;letter-spacing:.08em;text-transform:uppercase;'
            f'color:{lc};font-weight:700;margin-bottom:4px">{label}</div>'
            f'<div style="font-family:\'DM Serif Display\',serif;font-size:2.1rem;'
            f'color:{tc};line-height:1.1">{value}</div>'
            f'<div style="font-size:.7rem;color:{sc};margin-top:6px">{sub}</div></div>')

def sec_title(text, sub=""):
    s = (f'<div style="font-family:\'DM Serif Display\',serif;font-size:1.45rem;color:#003d6c;'
         f'margin:32px 0 8px;padding-bottom:10px;border-bottom:2px solid #17743d">{text}</div>')
    if sub: s += f'<div style="font-size:.85rem;color:#666;margin-bottom:16px">{sub}</div>'
    return s

def badge(text, color="#1754ab"):
    return (f'<span style="display:inline-block;background:{color}18;color:{color};'
            f'border:1px solid {color}44;border-radius:20px;padding:2px 10px;'
            f'font-size:.72rem;font-weight:600;margin:2px 3px 2px 0">{text}</span>')

def field_row(label, value):
    v = str(value).strip()
    if not v or v in ("", "—", "0", "None"): return ""
    return (f'<div style="display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #f0f0f0">'
            f'<div style="width:160px;flex-shrink:0;font-size:.78rem;font-weight:600;color:#555">{label}</div>'
            f'<div style="flex:1;font-size:.82rem;color:#222">{v}</div></div>')

# ══════════════════════════════════════════════════════════════════════════════
# LOAD ALL DATA  — retorna también ind_d (dict raw pid→lista) para el tab 3
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def load_all():
    # ── Lookups ───────────────────────────────────────────────────────────────
    estados    = {r["id"]: r["estado"]            for r in _fetch("contenido_estado")}
    deps       = {r["id"]: r["dependencia"]       for r in _fetch("contenido_dependencia")}
    resps      = {r["id"]: r["responsable"]       for r in _fetch("contenido_responsable")}
    sectores   = {r["id"]: r["sector"]            for r in _fetch("contenido_sectores")}
    segmentos  = {r["id"]: r["segmento"]          for r in _fetch("contenido_segmentos")}
    ubicacs    = {r["id"]: r["ubicacion"]         for r in _fetch("contenido_ubicacion")}
    municipios = {r["id"]: r["municipio"]         for r in _fetch("contenido_municipios")}
    clf_ben    = {r["id"]: r["tipo_beneficiario"] for r in _fetch("contenido_clasificacionbeneficiario")}
    vigencias  = {r["id"]: r["vigencia"]          for r in _fetch("contenido_clasificacionvigencia")}

    # FIX #2 y #3: aliados con su clasificación
    clf_aliados = {r["id"]: r["clasificacion_aliado"]
                   for r in _fetch("contenido_clasificacionaliados")}
    aliados_map = {r["id"]: f"{r['aliado']} ({clf_aliados.get(r.get('clasificacion_id'), '—')})"
                   for r in _fetch("contenido_aliados")}

    clf_ind = {r["id"]: {
        "codigo": r["codigo_indicador"],
        "nombre": r["nombre_indicador"],
        "meta_c": float(r["meta_cuatrienio"] or 0),
        "m2024":  r.get("meta_fisica_esperada_2024"),
        "m2025":  r.get("meta_fisica_esperada_2025"),
        "m2026":  r.get("meta_fisica_esperada_2026"),
        "m2027":  r.get("meta_fisica_esperada_2027"),
        "resp":   r.get("responsable", ""),
    } for r in _fetch("contenido_clasificacionindicadormga")}

    # ── M2M ───────────────────────────────────────────────────────────────────
    def m2m(table, fk, vk, vmap):
        d = {}
        for r in _fetch(table):
            d.setdefault(r[fk], []).append(vmap.get(r[vk], str(r[vk])))
        return d

    conv_sec  = m2m("contenido_convocatorias_sectores",   "convocatorias_id", "sectores_id",   sectores)
    conv_seg  = m2m("contenido_convocatorias_segmento",   "convocatorias_id", "segmentos_id",  segmentos)
    conv_ubi  = m2m("contenido_convocatorias_ubicacion",  "convocatorias_id", "ubicacion_id",  ubicacs)
    conv_dep  = m2m("contenido_convocatorias_dependencia","convocatorias_id", "dependencia_id",deps)
    proy_mun  = m2m("contenido_proyecto_municipios",      "proyecto_id",      "municipios_id", municipios)

    # FIX #3: aliados M2M
    conv_ali: dict = {}
    for r in _fetch("contenido_convocatorias_aliados"):
        cid = r["convocatorias_id"]
        conv_ali.setdefault(cid, []).append(aliados_map.get(r["aliados_id"], "—"))

    # ── Beneficiarios ─────────────────────────────────────────────────────────
    ben_d: dict = {}
    for r in _fetch("contenido_beneficiarios"):
        pid = r.get("proyecto_id")
        if pid:
            ben_d.setdefault(pid, []).append({
                "tipo": clf_ben.get(r.get("beneficiario_id"), "?"),
                "n":    r.get("numero_beneficiarios", 0),
            })

    # ── Indicadores MGA (también guardamos dict raw para Tab 3) ──────────────
    # FIX #5: retornamos ind_d como 5.º valor
    ind_d: dict = {}
    for r in _fetch("contenido_indicadormga"):
        pid = r.get("proyecto_id")
        if pid:
            clf = clf_ind.get(r.get("indicadores_id"), {})
            ind_d.setdefault(pid, []).append({
                "codigo":          clf.get("codigo", ""),
                "nombre":          clf.get("nombre", ""),
                "vigencia":        vigencias.get(r.get("vigencia_id"), ""),
                "meta_proyecto":   float(r.get("meta_proyecto") or 0),
                "meta_cuatrienio": clf.get("meta_c", 0),
                "m2024": clf.get("m2024"), "m2025": clf.get("m2025"),
                "m2026": clf.get("m2026"), "m2027": clf.get("m2027"),
                "responsable_mga": clf.get("resp", ""),
            })

    # ── CONVOCATORIAS ─────────────────────────────────────────────────────────
    conv_rows = _fetch("contenido_convocatorias")
    conv_list = []
    for r in conv_rows:
        cid = r["id"]
        conv_list.append({
            "id":                 cid,
            "Convocatoria":       r["nombre_convocatoria"],
            "Estado":             estados.get(r.get("estado_id"), "—"),
            "Fecha apertura":     _fdate(r.get("fecha_apertura")),
            "Fecha cierre":       _fdate(r.get("fecha_cierre")),
            "Monto":              float(r.get("monto") or 0),
            "Contacto":           r.get("contacto", ""),
            "Qué ofrece":         r.get("que_ofrece", "") or "",
            "Quiénes participan": r.get("quienes_pueden_participar", "") or "",
            "Público priorizado": r.get("publico_priorizado", "") or "",
            "Sectores":           " · ".join(conv_sec.get(cid, [])),
            "Segmentos":          " · ".join(conv_seg.get(cid, [])),
            "Ubicación":          " · ".join(conv_ubi.get(cid, [])),
            "Dependencias":       " · ".join(conv_dep.get(cid, [])),
            "Aliados":            " · ".join(conv_ali.get(cid, [])),  # FIX #2
            "N° proyectos":       0,
        })
    df_conv = pd.DataFrame(conv_list) if conv_list else pd.DataFrame()

    # ── PROYECTOS ─────────────────────────────────────────────────────────────
    proy_rows = _fetch("contenido_proyecto")
    proy_list = []
    for r in proy_rows:
        pid  = r["id"]
        bens = ben_d.get(pid, [])
        inds = ind_d.get(pid, [])
        proy_list.append({
            "id":                  pid,
            "convocatoria_id":     r.get("convocatoria_id"),
            "Proyecto":            r["nombre_proyecto"],
            "BPIN":                r.get("bpin", ""),
            "Valor":               float(r.get("valor_proyecto") or 0),
            "Contrapartida":       float(r.get("monto_contrapartida") or 0),
            "Dependencia":         deps.get(r.get("dependencia_id"), "—"),
            "Responsable":         resps.get(r.get("responsable_id"), "—"),
            "Municipios":          " · ".join(proy_mun.get(pid, [])),
            "Total beneficiarios": sum(b["n"] for b in bens),
            "Tipos beneficiarios": ", ".join(f"{b['tipo']} ({b['n']})" for b in bens),
            "N° indicadores MGA":  len(inds),
            "Indicadores MGA":     "; ".join(f"{i['codigo']} – {i['nombre']}" for i in inds),
        })
    df_proy = pd.DataFrame(proy_list) if proy_list else pd.DataFrame()

    # Contar proyectos por convocatoria
    if not df_conv.empty and not df_proy.empty and "convocatoria_id" in df_proy.columns:
        cnt = df_proy.groupby("convocatoria_id")["id"].count().to_dict()
        df_conv["N° proyectos"] = df_conv["id"].map(cnt).fillna(0).astype(int)

    # ── INDICADORES (tabla plana) ─────────────────────────────────────────────
    proy_names = {r["id"]: r["nombre_proyecto"] for r in proy_rows}
    ind_rows   = []
    for pid, inds in ind_d.items():
        for i in inds:
            ind_rows.append({"Proyecto": proy_names.get(pid, "—"), "proyecto_id": pid, **i})
    df_ind = pd.DataFrame(ind_rows) if ind_rows else pd.DataFrame()

    # ── RELACIONES (join enriquecido) ─────────────────────────────────────────
    # FIX #6: incluir todos los campos de texto de convocatoria para armar ficha en Tab 3
    if not df_proy.empty and not df_conv.empty and "convocatoria_id" in df_proy.columns:
        conv_cols = ["id","Convocatoria","Estado","Monto","Sectores","Segmentos",
                     "Ubicación","Dependencias","Aliados","Fecha apertura","Fecha cierre",
                     "Qué ofrece","Quiénes participan","Público priorizado","Contacto"]
        df_rel = df_proy.merge(
            df_conv[[c for c in conv_cols if c in df_conv.columns]],
            left_on="convocatoria_id", right_on="id",
            how="left", suffixes=("", "_conv")
        ).rename(columns={"Monto": "Monto convocatoria", "Estado": "Estado convocatoria"})
        # FIX WARN #2: limpiar columna duplicada de forma segura
        df_rel = df_rel.drop(columns=[c for c in df_rel.columns if c.endswith("_conv")], errors="ignore")
        df_rel["Cobertura (%)"] = df_rel.apply(
            lambda row: round(row["Valor"] / row["Monto convocatoria"] * 100, 1)
            if row.get("Monto convocatoria", 0) else None, axis=1)
    else:
        df_rel = pd.DataFrame()

    # FIX #5: retornar ind_d como 5.º valor
    return df_conv, df_proy, df_rel, df_ind, ind_d

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR HEADER
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div style="padding:16px 0 20px">'
        '<div style="font-family:\'DM Serif Display\',serif;font-size:1.8rem;color:#fff;line-height:1.1">SDP</div>'
        '<div style="color:#47b1d5;font-size:.85rem;font-weight:400;margin-top:6px">Convocatorias & Proyectos</div></div>'
        '<hr style="border-color:#1754ab;opacity:.3;margin-bottom:18px">',
        unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("Conectando con Supabase..."):
    try:
        df_conv, df_proy, df_rel, df_ind, _ind_d = load_all()
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        st.stop()

if df_conv.empty and df_proy.empty:
    st.markdown(empty_state("No se encontraron datos en Supabase."), unsafe_allow_html=True)
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────────
estados_opts  = sorted(df_conv["Estado"].dropna().unique())   if not df_conv.empty else []
sectores_opts = sorted({s.strip() for row in df_conv["Sectores"] if row
                        for s in row.split(" · ") if s.strip()}) if not df_conv.empty else []
dep_opts      = sorted(df_proy["Dependencia"].dropna().unique()) if not df_proy.empty else []

with st.sidebar:
    st.markdown('<div style="font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;'
                'color:#a5d6a7;font-weight:700;margin-bottom:10px">Filtros</div>',
                unsafe_allow_html=True)
    sel_est = st.multiselect("Estado convocatoria", estados_opts,  placeholder="Todos")
    sel_sec = st.multiselect("Sector",              sectores_opts, placeholder="Todos")
    sel_dep = st.multiselect("Dependencia",         dep_opts,      placeholder="Todas")
    st.markdown('<hr style="border-color:#1754ab;opacity:.3;margin:20px 0 16px">', unsafe_allow_html=True)
    if st.button("Refrescar", use_container_width=True):
        st.cache_data.clear(); st.rerun()

df_c = df_conv.copy(); df_p = df_proy.copy()
if sel_est:  df_c = df_c[df_c["Estado"].isin(sel_est)]
if sel_sec:  df_c = df_c[df_c["Sectores"].apply(lambda s: any(x in s for x in sel_sec))]
if sel_dep:  df_p = df_p[df_p["Dependencia"].isin(sel_dep)]
if sel_est or sel_sec: df_p = df_p[df_p["convocatoria_id"].isin(df_c["id"])]
if sel_dep:  df_c = df_c[df_c["id"].isin(df_p["convocatoria_id"])]

df_r = df_rel.copy()
if not df_r.empty:
    if sel_est: df_r = df_r[df_r["Estado convocatoria"].isin(sel_est)]
    if sel_dep: df_r = df_r[df_r["Dependencia"].isin(sel_dep)]
df_i = df_ind.copy()
if not df_i.empty and sel_dep:
    df_i = df_i[df_i["proyecto_id"].isin(df_p["id"])]

# ── Hero + KPIs ────────────────────────────────────────────────────────────────
n_conv  = df_c["id"].nunique() if not df_c.empty else 0
n_proy  = df_p["id"].nunique() if not df_p.empty else 0
m_conv  = df_c["Monto"].sum()  if not df_c.empty else 0
v_proy  = df_p["Valor"].sum()  if not df_p.empty else 0
n_ind   = len(df_i)            if not df_i.empty else 0
conv_cp = df_c[df_c["N° proyectos"] > 0]["id"].nunique() if not df_c.empty else 0
pct_cp  = round(conv_cp / max(n_conv, 1) * 100) if n_conv > 0 else 0

st.markdown(
    '<div style="background:linear-gradient(135deg,#003d6c 0%,#005931 100%);'
    'border-radius:12px;padding:34px 40px 30px;margin-bottom:24px;'
    'box-shadow:0 6px 15px rgba(0,0,0,.1)">'
    '<div style="font-family:\'DM Serif Display\',serif;font-size:2.2rem;color:#fff;margin:0 0 8px">'
    'Seguimiento de Convocatorias &amp; Proyectos</div>'
    '<div style="color:#a5d6a7;font-size:.9rem;font-weight:400;letter-spacing:.02em">'
    'Matriz de seguimiento SDP · Actualización automática cada 5 minutos</div></div>',
    unsafe_allow_html=True)

st.markdown(f"""
<div style="display:flex;gap:14px;margin-bottom:24px;align-items:stretch;flex-wrap:wrap;">
    {kpi("Total Convocatorias", n_conv,           "en filtros activos",  style="dark-blue",  flex="1.5")}
    {kpi("Proyectos",           n_proy,           "formulados",          style="dark-green", flex="1.5")}
    {kpi("Con proyectos",       f"{conv_cp}",     f"{pct_cp}% de conv.", border_color="#d88c16", flex="1")}
    {kpi("Monto convoc.",       fmt_money(m_conv),"suma total",          border_color="#cf7000", flex="1")}
    {kpi("Valor proy.",         fmt_money(v_proy),"suma total",          border_color="#47b1d5", flex="1")}
    {kpi("Indicadores MGA",     n_ind,            "registros",           border_color="#1754ab", flex="1")}
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
GEMINI_API_KEY = "AIzaSyDqHYMD79btZiRlXFHYXWU0SDaiNtIwGgA"
GEMINI_MODEL   = "gemini-3-flash-preview"

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Resumen general", "Proyectos formulados",
    "Relaciones matriciales", "✨ Asistente IA", "Exportar",
])

# ─── TAB 1: RESUMEN GENERAL ───────────────────────────────────────────────────
with tab1:
    st.markdown(sec_title("Convocatorias", f"{n_conv} registros activos en el tablero"),
                unsafe_allow_html=True)
    if not df_c.empty:
        ca, cb = st.columns([3, 2])
        with ca:
            st.markdown(bar_chart(df_c["Estado"].value_counts(), "Por estado"), unsafe_allow_html=True)
            sec_exp = df_c["Sectores"].str.split(" · ").explode().str.strip().value_counts()
            sec_exp = sec_exp[sec_exp.index.str.len() > 0]
            if not sec_exp.empty:
                st.markdown(bar_chart(sec_exp, "Por sector", max_bars=15), unsafe_allow_html=True)
            # WARN #3 fix: graficar dependencias de convocatorias
            dep_exp = df_c["Dependencias"].str.split(" · ").explode().str.strip().value_counts()
            dep_exp = dep_exp[dep_exp.index.str.len() > 0]
            if not dep_exp.empty:
                st.markdown(bar_chart(dep_exp, "Por dependencia responsable", max_bars=12),
                            unsafe_allow_html=True)
        with cb:
            seg_exp = df_c["Segmentos"].str.split(" · ").explode().str.strip().value_counts()
            seg_exp = seg_exp[seg_exp.index.str.len() > 0]
            if not seg_exp.empty:
                st.markdown(donut_chart(seg_exp, "Por segmento"), unsafe_allow_html=True)
            ubi_exp = df_c["Ubicación"].str.split(" · ").explode().str.strip().value_counts()
            ubi_exp = ubi_exp[ubi_exp.index.str.len() > 0]
            if not ubi_exp.empty:
                st.markdown(donut_chart(ubi_exp, "Por ubicación"), unsafe_allow_html=True)
            st.markdown(
                bar_chart(df_c.groupby("Estado")["Monto"].sum().sort_values(ascending=False),
                          "Monto por estado", fmt_val=fmt_money),
                unsafe_allow_html=True)

    st.markdown(sec_title("Matriz de convocatorias"), unsafe_allow_html=True)
    lc = ["Convocatoria","Estado","Fecha apertura","Fecha cierre","Monto",
          "Sectores","Segmentos","Ubicación","N° proyectos","Contacto"]
    lc = [c for c in lc if c in df_c.columns]
    st.dataframe(df_c[lc].reset_index(drop=True), use_container_width=True, height=400,
        hide_index=True,
        column_config={
            "Convocatoria": st.column_config.TextColumn(width=280),
            "Monto":        st.column_config.NumberColumn("Monto $", format="$%,.0f"),
            "N° proyectos": st.column_config.NumberColumn("Proyectos", width=90),
        })

    st.markdown(sec_title("Ficha de la convocatoria"), unsafe_allow_html=True)
    if not df_c.empty:
        sel = st.selectbox("Selecciona para expandir", df_c["Convocatoria"].tolist(), key="dc")
        if sel:
            row = df_c[df_c["Convocatoria"] == sel].iloc[0]
            d1,d2,d3,d4 = st.columns(4)
            d1.metric("Estado",    row["Estado"])
            d2.metric("Monto",     fmt_money(row["Monto"]))
            d3.metric("Proyectos", int(row["N° proyectos"]))
            d4.metric("Apertura",  row["Fecha apertura"])
            with st.expander("Ver descripción y requisitos completos"):
                for f in ["Qué ofrece","Quiénes participan","Público priorizado",
                           "Sectores","Segmentos","Ubicación","Dependencias","Aliados","Contacto"]:
                    if f in row and str(row[f]).strip() and str(row[f]) not in ("—",""):
                        st.markdown(f"**{f}:** {row[f]}")
            proy_sub = df_p[df_p["convocatoria_id"] == int(row["id"])]
            if not proy_sub.empty:
                st.caption(f"{len(proy_sub)} proyecto(s) asociado(s)")
                pc = ["Proyecto","BPIN","Valor","Dependencia","Responsable","Municipios"]
                pc = [c for c in pc if c in proy_sub.columns]
                st.dataframe(proy_sub[pc].reset_index(drop=True), use_container_width=True,
                    height=200, hide_index=True,
                    column_config={"Valor": st.column_config.NumberColumn("Valor $", format="$%,.0f")})

# ─── TAB 2: PROYECTOS FORMULADOS ──────────────────────────────────────────────
with tab2:
    st.markdown(sec_title("Proyectos", f"{n_proy} proyectos formulados en sistema"),
                unsafe_allow_html=True)
    if not df_p.empty:
        pa, pb = st.columns([3, 2])
        with pa:
            st.markdown(bar_chart(df_p["Dependencia"].value_counts(),
                "Por dependencia", max_bars=15), unsafe_allow_html=True)
            st.markdown(bar_chart(df_p.nlargest(15, "Valor").set_index("Proyecto")["Valor"],
                "Top 15 por valor", fmt_val=fmt_money), unsafe_allow_html=True)
        with pb:
            st.markdown(donut_chart(df_p["Responsable"].value_counts(),
                "Por responsable"), unsafe_allow_html=True)
            mun_exp = df_p["Municipios"].str.split(" · ").explode().str.strip().value_counts()
            mun_exp = mun_exp[mun_exp.index.str.len() > 0]
            if not mun_exp.empty:
                st.markdown(donut_chart(mun_exp, "Por municipio"), unsafe_allow_html=True)
            ben_dep = df_p.groupby("Dependencia")["Total beneficiarios"].sum()
            ben_dep = ben_dep[ben_dep > 0]
            if not ben_dep.empty:
                st.markdown(bar_chart(ben_dep.sort_values(ascending=False),
                    "Beneficiarios por dependencia"), unsafe_allow_html=True)

    st.markdown(sec_title("Matriz de proyectos"), unsafe_allow_html=True)
    ps = ["Proyecto","BPIN","Valor","Contrapartida","Dependencia","Responsable",
          "Municipios","Total beneficiarios","N° indicadores MGA"]
    ps = [c for c in ps if c in df_p.columns]
    st.dataframe(df_p[ps].reset_index(drop=True), use_container_width=True, height=420,
        hide_index=True,
        column_config={
            "Proyecto":            st.column_config.TextColumn(width=280),
            "Valor":               st.column_config.NumberColumn("Valor $",       format="$%,.0f"),
            "Contrapartida":       st.column_config.NumberColumn("Contrapartida", format="$%,.0f"),
            "Total beneficiarios": st.column_config.NumberColumn("Beneficiarios", width=110),
            "N° indicadores MGA":  st.column_config.NumberColumn("Indicadores",   width=100),
        })

    st.markdown(sec_title("Ficha del proyecto"), unsafe_allow_html=True)
    if not df_p.empty:
        sel_p = st.selectbox("Selecciona para expandir", df_p["Proyecto"].tolist(), key="dp")
        if sel_p:
            rp = df_p[df_p["Proyecto"] == sel_p].iloc[0]
            p1,p2,p3,p4 = st.columns(4)
            p1.metric("Valor",         fmt_money(rp["Valor"]))
            p2.metric("Contrapartida", fmt_money(rp["Contrapartida"]))
            p3.metric("Beneficiarios", int(rp["Total beneficiarios"]))
            p4.metric("BPIN",          rp["BPIN"])
            with st.expander("Ver variables complementarias"):
                for f in ["Dependencia","Responsable","Municipios",
                           "Tipos beneficiarios","Indicadores MGA"]:
                    if f in rp and str(rp[f]).strip() and str(rp[f]) not in ("—","0",""):
                        st.markdown(f"**{f}:** {rp[f]}")
            ind_sub = df_i[df_i["proyecto_id"] == int(rp["id"])] if not df_i.empty else pd.DataFrame()
            if not ind_sub.empty:
                st.caption(f"{len(ind_sub)} indicador(es) MGA integrados")
                ic = ["codigo","nombre","vigencia","meta_proyecto","meta_cuatrienio",
                      "m2024","m2025","m2026","m2027"]
                ic = [c for c in ic if c in ind_sub.columns]
                st.dataframe(ind_sub[ic].reset_index(drop=True),
                    use_container_width=True, height=200, hide_index=True)

# ─── TAB 3: RELACIONES MATRICIALES ────────────────────────────────────────────
with tab3:
    st.markdown(
        sec_title("Relaciones matriciales",
                  "Selecciona una convocatoria para ver su ficha completa y los proyectos asociados"),
        unsafe_allow_html=True)

    if df_r.empty:
        st.markdown(empty_state("No hay cruces relacionales con los filtros actuales."),
                    unsafe_allow_html=True)
    else:
        # ── Selector principal ────────────────────────────────────────────────
        opciones_rel = ["— Ver resumen general —"] + sorted(
            df_r["Convocatoria"].dropna().unique().tolist())
        sel_rel = st.selectbox("Convocatoria", opciones_rel, key="sel_rel",
                               label_visibility="collapsed")

        # ════════════════════════════════════════════════════════════════════
        # MODO A: RESUMEN GENERAL (todas las convocatorias)
        # ════════════════════════════════════════════════════════════════════
        if sel_rel == "— Ver resumen general —":
            ra, rb = st.columns([3, 2])
            with ra:
                pxc = df_r.groupby("Convocatoria")["id"].nunique().sort_values(ascending=False)
                st.markdown(bar_chart(pxc, "Proyectos por convocatoria", max_bars=20),
                            unsafe_allow_html=True)
                vxd = df_r.groupby("Dependencia")["Valor"].sum().sort_values(ascending=False)
                st.markdown(bar_chart(vxd, "Valor total por dependencia", fmt_val=fmt_money),
                            unsafe_allow_html=True)
            with rb:
                vxc = df_r.groupby("Convocatoria")["Valor"].sum().sort_values(ascending=False)
                st.markdown(bar_chart(vxc.head(10), "Valor por convocatoria (top 10)",
                            fmt_val=fmt_money), unsafe_allow_html=True)
                cob = df_r["Cobertura (%)"].dropna()
                if not cob.empty:
                    cob_r = pd.cut(cob, bins=[0,25,50,75,100,float("inf")],
                                   labels=["0–25%","25–50%","50–75%","75–100%",">100%"])
                    st.markdown(donut_chart(cob_r.value_counts(),
                        "Distribución de cobertura financiera"), unsafe_allow_html=True)

            st.markdown(sec_title("Matriz de trazabilidad"), unsafe_allow_html=True)
            rc = ["Convocatoria","Estado convocatoria","Sectores","Proyecto","BPIN","Valor",
                  "Dependencia","Responsable","Fecha apertura","Fecha cierre","Cobertura (%)"]
            rc = [c for c in rc if c in df_r.columns]
            st.dataframe(df_r[rc].reset_index(drop=True),
                use_container_width=True, height=450, hide_index=True,
                column_config={
                    "Convocatoria":  st.column_config.TextColumn(width=230),
                    "Proyecto":      st.column_config.TextColumn(width=210),
                    "Valor":         st.column_config.NumberColumn("Valor $",  format="$%,.0f"),
                    "Cobertura (%)": st.column_config.NumberColumn("Cob. %",   format="%.1f%%"),
                })

            sin = df_c[df_c["N° proyectos"] == 0] if not df_c.empty else pd.DataFrame()
            if not sin.empty:
                with st.expander(f"⚠️ {len(sin)} convocatoria(s) sin proyectos asociados"):
                    sc = ["Convocatoria","Estado","Monto","Sectores"]
                    sc = [c for c in sc if c in sin.columns]
                    st.dataframe(sin[sc].reset_index(drop=True),
                        use_container_width=True, hide_index=True)

        # ════════════════════════════════════════════════════════════════════
        # MODO B: DETALLE DE UNA CONVOCATORIA
        # ════════════════════════════════════════════════════════════════════
        else:
            df_r_sel   = df_r[df_r["Convocatoria"] == sel_rel]
            conv_match = df_c[df_c["Convocatoria"] == sel_rel]

            # ── Ficha de la convocatoria ──────────────────────────────────
            if not conv_match.empty:
                cr = conv_match.iloc[0]

                estado_color = "#17743d" if "vigente" in str(cr["Estado"]).lower() else "#cf7000"
                badges_html  = badge(cr["Estado"], estado_color)
                for s in str(cr.get("Sectores","")).split(" · "):
                    if s.strip(): badges_html += badge(s.strip(), "#1754ab")
                for s in str(cr.get("Segmentos","")).split(" · "):
                    if s.strip(): badges_html += badge(s.strip(), "#47b1d5")

                st.markdown(f"""
<div style="background:#f8fbff;border:1px solid #cce0f5;border-left:5px solid #1754ab;
border-radius:10px;padding:26px 30px;margin:16px 0 20px">
  <div style="font-family:'DM Serif Display',serif;font-size:1.5rem;color:#003d6c;margin-bottom:10px">
    {cr['Convocatoria']}
  </div>
  <div style="margin-bottom:16px">{badges_html}</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:18px;margin-bottom:18px">
    <div>
      <div style="font-size:.66rem;color:#888;text-transform:uppercase;letter-spacing:.06em">Monto disponible</div>
      <div style="font-size:1.5rem;font-family:'DM Serif Display',serif;color:#005931">{fmt_money(cr['Monto'])}</div>
    </div>
    <div>
      <div style="font-size:.66rem;color:#888;text-transform:uppercase;letter-spacing:.06em">Fecha apertura</div>
      <div style="font-size:1rem;color:#222;margin-top:4px">{cr['Fecha apertura']}</div>
    </div>
    <div>
      <div style="font-size:.66rem;color:#888;text-transform:uppercase;letter-spacing:.06em">Fecha cierre</div>
      <div style="font-size:1rem;color:#222;margin-top:4px">{cr['Fecha cierre']}</div>
    </div>
    <div>
      <div style="font-size:.66rem;color:#888;text-transform:uppercase;letter-spacing:.06em">Proyectos formulados</div>
      <div style="font-size:1.5rem;font-family:'DM Serif Display',serif;color:#1754ab">{int(cr['N° proyectos'])}</div>
    </div>
  </div>
  {field_row("Qué ofrece",         cr.get("Qué ofrece",""))}
  {field_row("Quiénes participan", cr.get("Quiénes participan",""))}
  {field_row("Público priorizado", cr.get("Público priorizado",""))}
  {field_row("Ubicación",          cr.get("Ubicación",""))}
  {field_row("Dependencias",       cr.get("Dependencias",""))}
  {field_row("Aliados",            cr.get("Aliados",""))}
  {field_row("Contacto",           cr.get("Contacto",""))}
</div>""", unsafe_allow_html=True)

            # ── KPIs de esta convocatoria ─────────────────────────────────
            n_p_sel   = df_r_sel["id"].nunique()
            v_total   = df_r_sel["Valor"].sum()
            mc_sel    = df_r_sel["Monto convocatoria"].iloc[0] \
                        if not df_r_sel.empty and "Monto convocatoria" in df_r_sel.columns else 0
            cob_total = round(v_total / mc_sel * 100, 1) if mc_sel else None
            n_deps    = df_r_sel["Dependencia"].nunique()

            st.markdown(f"""
<div style="display:flex;gap:14px;margin:0 0 24px;flex-wrap:wrap;">
    {kpi("Proyectos",           n_p_sel,               "en esta convocatoria",     border_color="#1754ab")}
    {kpi("Valor total",         fmt_money(v_total),    "suma de proyectos",        border_color="#17743d")}
    {kpi("Cobertura",           f"{cob_total}%" if cob_total else "—",
                                "valor / monto conv.",                             border_color="#cf7000")}
    {kpi("Dependencias",        n_deps,                "involucradas",             border_color="#47b1d5")}
</div>""", unsafe_allow_html=True)

            # ── Proyectos expandibles ─────────────────────────────────────
            st.markdown(
                sec_title(f"Proyectos asociados",
                          f"{n_p_sel} proyecto(s) formulado(s) · expande cada tarjeta para ver la ficha completa"),
                unsafe_allow_html=True)

            for _, pr in df_r_sel.iterrows():
                pid      = int(pr["id"])
                p_nombre = pr["Proyecto"]
                p_dep    = pr.get("Dependencia", "—")
                p_val    = fmt_money(pr["Valor"])
                p_cob    = (f"{pr['Cobertura (%)']:.1f}%"
                            if pd.notna(pr.get("Cobertura (%)")) else "—")
                p_bpin   = pr.get("BPIN", "—")

                with st.expander(
                    f"**{p_nombre}** · {p_dep} · {p_val} · Cob. {p_cob}"
                ):
                    e1, e2, e3, e4 = st.columns(4)
                    e1.metric("Valor proyecto",  fmt_money(pr["Valor"]))
                    e2.metric("Contrapartida",   fmt_money(pr.get("Contrapartida", 0)))
                    e3.metric("Beneficiarios",   int(pr.get("Total beneficiarios", 0)))
                    e4.metric("BPIN",            p_bpin)

                    # Campos descriptivos del proyecto
                    fields_html = ""
                    for f, lbl in [
                        ("Responsable",         "Responsable"),
                        ("Municipios",          "Municipios"),
                        ("Tipos beneficiarios", "Tipos de beneficiarios"),
                    ]:
                        val = pr.get(f, "")
                        if val and str(val).strip() not in ("", "—", "0", "None"):
                            fields_html += field_row(lbl, val)
                    if fields_html:
                        st.markdown(
                            f'<div style="background:#fafafa;border:1px solid #ececec;'
                            f'border-radius:8px;padding:14px 18px;margin:12px 0">'
                            f'{fields_html}</div>',
                            unsafe_allow_html=True)

                    # Indicadores MGA del proyecto (FIX #5: usa _ind_d)
                    inds_proy = _ind_d.get(pid, [])
                    if inds_proy:
                        st.markdown(
                            f'<div style="font-size:.78rem;font-weight:600;color:#1754ab;'
                            f'margin:14px 0 6px">📊 {len(inds_proy)} indicador(es) MGA</div>',
                            unsafe_allow_html=True)
                        df_ip = pd.DataFrame(inds_proy)
                        ic = ["codigo","nombre","vigencia","meta_proyecto",
                              "meta_cuatrienio","m2024","m2025","m2026","m2027"]
                        ic = [c for c in ic if c in df_ip.columns]
                        st.dataframe(
                            df_ip[ic].rename(columns={
                                "codigo":"Código","nombre":"Indicador","vigencia":"Vigencia",
                                "meta_proyecto":"Meta proy.","meta_cuatrienio":"Meta cuatrienio",
                                "m2024":"2024","m2025":"2025","m2026":"2026","m2027":"2027",
                            }).reset_index(drop=True),
                            use_container_width=True, height=min(180, 60+len(inds_proy)*40),
                            hide_index=True)
                    else:
                        st.caption("Sin indicadores MGA registrados para este proyecto.")

# ─── TAB 4: ASISTENTE IA (Gemini) ────────────────────────────────────────────
with tab4:
    st.markdown(sec_title("Asistente IA",
        "Consulta los datos de convocatorias y proyectos en lenguaje natural · Powered by Gemini"),
        unsafe_allow_html=True)

    # ── CSS extra para el chat ────────────────────────────────────────────────
    st.markdown("""
    <style>
    .chat-user {
        background:#e8f0fe;border-radius:16px 16px 4px 16px;
        padding:12px 16px;margin:6px 0 6px auto;
        max-width:80%;font-size:.88rem;color:#1a1a2e;
        border:1px solid #c5d5f5;
    }
    .chat-ai {
        background:#ffffff;border-radius:16px 16px 16px 4px;
        padding:14px 18px;margin:6px auto 6px 0;
        max-width:85%;font-size:.88rem;color:#1a1a1a;
        border:1px solid #e0e0e0;
        box-shadow:0 2px 6px rgba(0,0,0,.04);
    }
    .chat-ai-label {
        font-size:.68rem;color:#1754ab;font-weight:700;
        letter-spacing:.06em;text-transform:uppercase;margin-bottom:6px;
    }
    .chat-scroll {
        max-height:480px;overflow-y:auto;
        padding:16px;background:#f8f9fb;
        border:1px solid #e0e0e0;border-radius:10px;
        margin-bottom:16px;
    }
    .chip-btn {
        display:inline-block;background:#e8f0fe;color:#1754ab;
        border:1px solid #c5d5f5;border-radius:20px;
        padding:5px 14px;font-size:.78rem;font-weight:600;
        cursor:pointer;margin:4px 4px 4px 0;
        transition:background .2s;
    }
    </style>""", unsafe_allow_html=True)

    # ── Construir contexto de datos (se hace una vez y se cachea en session) ──
    @st.cache_data(ttl=300, show_spinner=False)
    def _build_context(conv_hash, proy_hash):
        """Serializa los DataFrames como texto CSV compacto para el prompt."""
        def _df_to_text(df, name, max_rows=300):
            if df is None or df.empty:
                return f"[{name}: sin datos]\n"
            cols = [c for c in df.columns if c not in ("id","convocatoria_id","proyecto_id")]
            sub  = df[cols].head(max_rows)
            return f"=== {name.upper()} ({len(df)} registros totales) ===\n{sub.to_csv(index=False)}\n"

        ctx  = _df_to_text(df_conv, "Convocatorias")
        ctx += _df_to_text(df_proy, "Proyectos")
        ctx += _df_to_text(df_rel,  "Relaciones (Convocatoria-Proyecto)")
        ctx += _df_to_text(df_ind,  "Indicadores MGA")
        return ctx

    # Hashes simples para invalidar caché cuando cambien los datos
    _ch = str(len(df_conv)) + str(df_conv["id"].sum() if not df_conv.empty else 0)
    _ph = str(len(df_proy)) + str(df_proy["id"].sum() if not df_proy.empty else 0)
    data_context = _build_context(_ch, _ph)

    SYSTEM_PROMPT = f"""Eres un asistente de análisis de datos especializado en convocatorias \
y proyectos de la Secretaría Distrital de Planeación (SDP) de Bogotá.

Tienes acceso a la base de datos completa cargada desde Supabase. Los datos actualizados son:

{data_context}

INSTRUCCIONES:
- Responde siempre en español, de forma clara y concisa.
- Cuando el usuario pregunte por conteos, listas o comparaciones, extrae la respuesta \
directamente de los datos anteriores.
- Si la respuesta incluye una tabla, fórmala en Markdown con columnas alineadas.
- Si la respuesta es un número o resumen corto, preséntalo con contexto.
- Si preguntan algo que no está en los datos, dilo honestamente.
- No inventes datos. Todo debe provenir de las tablas mostradas.
- Puedes hacer cálculos: sumas, promedios, porcentajes, rankings, filtros por sector/estado/dependencia.
- Respuestas máximo 400 palabras salvo que el usuario pida más detalle.
"""

    def _call_gemini(messages: list[dict]) -> str:
        """Llama a la API de Gemini con historial completo."""
        import urllib.request, json as _json
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}")
        # Formato Gemini: role user/model
        contents = []
        # Sistema como primer turno user+model
        contents.append({"role":"user",
                          "parts":[{"text": f"[CONTEXTO DEL SISTEMA]\n{SYSTEM_PROMPT}"}]})
        contents.append({"role":"model",
                          "parts":[{"text":"Entendido. Estoy listo para responder preguntas "
                                           "sobre las convocatorias y proyectos de la SDP."}]})
        for m in messages:
            contents.append({"role": m["role"], "parts":[{"text": m["content"]}]})
        body = _json.dumps({
            "contents": contents,
            "generationConfig": {
                "temperature":   0.3,
                "maxOutputTokens": 1500,
                "topP":          0.9,
            }
        }).encode()
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            
            if "not found" in err.lower() or "invalid" in err.lower():
                return f"⚠️ Error de API: {err[:300]}"
            return f"⚠️ Error HTTP {e.code}: {err[:300]}"
        except Exception as ex:
            return f"⚠️ Error al conectar con Gemini: {ex}"

    # ── Session state ─────────────────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []   # [{role, content}]

    # ── Sugerencias rápidas ───────────────────────────────────────────────────
    suggestions = [
        "¿Cuántas convocatorias hay vigentes?",
        "¿Cuál es el sector con más convocatorias?",
        "Lista los 5 proyectos de mayor valor",
        "¿Cuánto suman los proyectos por dependencia?",
        "¿Qué convocatorias no tienen proyectos?",
        "¿Cuál es el promedio de cobertura financiera?",
        "¿Cuáles son los indicadores MGA más usados?",
        "Resumen general de la base de datos",
    ]

    st.markdown('<div style="margin-bottom:10px;font-size:.8rem;color:#666;font-weight:600">'
                'Preguntas sugeridas:</div>', unsafe_allow_html=True)
    cols_s = st.columns(4)
    for idx, sug in enumerate(suggestions):
        if cols_s[idx % 4].button(sug, key=f"sug_{idx}", use_container_width=True):
            st.session_state.chat_history.append({"role":"user","content":sug})
            with st.spinner("Consultando Gemini..."):
                resp = _call_gemini(st.session_state.chat_history)
            st.session_state.chat_history.append({"role":"model","content":resp})
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Historial de mensajes ─────────────────────────────────────────────────
    if st.session_state.chat_history:
        chat_html = '<div class="chat-scroll">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += (f'<div style="display:flex;justify-content:flex-end;margin:8px 0">'
                              f'<div class="chat-user">👤 {msg["content"]}</div></div>')
            else:
                # Convertir markdown básico a HTML (negrita, listas, código)
                content = msg["content"]
                # Tablas markdown las dejamos como texto; st.markdown las renderiza
                chat_html += (f'<div style="display:flex;justify-content:flex-start;margin:8px 0">'
                              f'<div class="chat-ai">'
                              f'<div class="chat-ai-label">✨ Gemini · Asistente IA</div>'
                              f'<div style="white-space:pre-wrap">{content}</div>'
                              f'</div></div>')
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="background:#f0f8fb;border:1px dashed #47b1d5;border-radius:10px;'
            'padding:30px;text-align:center;color:#666;margin-bottom:16px">'
            '💬 Escribe una pregunta o usa las sugerencias para empezar</div>',
            unsafe_allow_html=True)

    # ── Input del usuario ─────────────────────────────────────────────────────
    col_inp, col_btn, col_clr = st.columns([6, 1, 1])
    with col_inp:
        user_input = st.text_input("Escribe tu pregunta", placeholder="Ej: ¿Cuál es el estado con más convocatorias?",
                                   key="chat_input", label_visibility="collapsed")
    with col_btn:
        send = st.button("Enviar", type="primary", use_container_width=True)
    with col_clr:
        if st.button("Limpiar", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    if send and user_input.strip():
        st.session_state.chat_history.append({"role":"user","content":user_input.strip()})
        with st.spinner("Consultando Gemini..."):
            resp = _call_gemini(st.session_state.chat_history)
        st.session_state.chat_history.append({"role":"model","content":resp})
        st.rerun()

    # ── Info de contexto ──────────────────────────────────────────────────────
    n_chars = len(data_context)
    st.markdown(
        f'<div style="font-size:.72rem;color:#aaa;margin-top:8px;text-align:right">'
        f'Contexto enviado a Gemini: {n_chars:,} caracteres · '
        f'{len(df_conv)} convocatorias · {len(df_proy)} proyectos · '
        f'{len(df_ind)} indicadores MGA</div>',
        unsafe_allow_html=True)

# ─── TAB 5: EXPORTAR ──────────────────────────────────────────────────────────
with tab5:
    st.markdown(sec_title("Exportar Reporte Maestro",
        "Generación de sábana de datos consolidada (.xlsx)"), unsafe_allow_html=True)

    opt = st.radio("Alcance de los datos a exportar",
                   ["Exportar universo completo (sin filtros)",
                    "Exportar selección actual (datos filtrados)"],
                   horizontal=True)
    ec = df_c if "filtrados" in opt else df_conv
    ep = df_p if "filtrados" in opt else df_proy
    er = df_r if "filtrados" in opt else df_rel
    ei = df_i if "filtrados" in opt else df_ind

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
<div style="display:flex;gap:14px;margin-bottom:24px;flex-wrap:wrap;">
    {kpi("Convocatorias", ec["id"].nunique() if not ec.empty else 0, "a exportar", border_color="#1754ab")}
    {kpi("Proyectos",     ep["id"].nunique() if not ep.empty else 0, "a exportar", border_color="#1754ab")}
    {kpi("Relaciones",    len(er) if not er.empty else 0,            "a exportar", border_color="#1754ab")}
    {kpi("Indicadores",   len(ei) if not ei.empty else 0,            "a exportar", border_color="#1754ab")}
</div>""", unsafe_allow_html=True)

    if st.button("Generar reporte de Excel", type="primary"):
        with st.spinner("Construyendo matriz Excel..."):
            H_FILL = PatternFill("solid", fgColor="003d6c")
            H_FONT = Font(bold=True, color="FFFFFF", name="Arial", size=10)
            C_FONT = Font(name="Arial", size=9)
            WHITE  = PatternFill("solid", fgColor="FFFFFF")
            THIN   = Border(
                left=Side(style="thin",   color="CCCCCC"),
                right=Side(style="thin",  color="CCCCCC"),
                top=Side(style="thin",    color="CCCCCC"),
                bottom=Side(style="thin", color="CCCCCC"),
            )
            wb = Workbook(); wb.remove(wb.active)
            sheets_def = [
                ("Convocatorias", ec, [
                    "Convocatoria","Estado","Fecha apertura","Fecha cierre","Monto",
                    "Sectores","Segmentos","Ubicación","Dependencias","Aliados",
                    "N° proyectos","Contacto","Qué ofrece","Quiénes participan","Público priorizado"]),
                ("Proyectos", ep, [
                    "Proyecto","BPIN","Valor","Contrapartida","Dependencia","Responsable",
                    "Municipios","Total beneficiarios","Tipos beneficiarios",
                    "N° indicadores MGA","Indicadores MGA"]),
                ("Relaciones", er, [
                    "Convocatoria","Estado convocatoria","Sectores","Proyecto","BPIN","Valor",
                    "Dependencia","Responsable","Fecha apertura","Fecha cierre","Cobertura (%)"]),
                ("Indicadores MGA", ei, [
                    "Proyecto","codigo","nombre","vigencia","meta_proyecto","meta_cuatrienio",
                    "m2024","m2025","m2026","m2027","responsable_mga"]),
            ]
            COL_W = {
                "Convocatoria":42,"Proyecto":42,"nombre":42,
                "Qué ofrece":50,"Quiénes participan":40,
                "Sectores":22,"Segmentos":20,"Municipios":22,
                "Tipos beneficiarios":30,"Indicadores MGA":40,
            }
            for sname, df, cols in sheets_def:
                if df is None or df.empty: continue
                cols = [c for c in cols if c in df.columns]
                ws   = wb.create_sheet(sname)
                ws.sheet_view.showGridLines = False
                for ci, col in enumerate(cols, 1):
                    c = ws.cell(row=1, column=ci, value=col)
                    c.font = H_FONT; c.fill = H_FILL
                    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    c.border = THIN
                ws.row_dimensions[1].height = 28
                for ri, (_, row) in enumerate(df[cols].iterrows(), 2):
                    for ci, col in enumerate(cols, 1):
                        val = row[col]
                        if pd.isna(val): val = ""
                        c = ws.cell(row=ri, column=ci, value=val)
                        c.font = C_FONT; c.fill = WHITE; c.border = THIN
                        c.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                    ws.row_dimensions[ri].height = 30
                for ci, col in enumerate(cols, 1):
                    ws.column_dimensions[get_column_letter(ci)].width = COL_W.get(col, 15)
                ws.freeze_panes = "A2"
                tname = "T_" + re.sub(r"[^A-Za-z0-9]", "_", sname)
                tbl = Table(displayName=tname,
                            ref=f"A1:{get_column_letter(len(cols))}{1+len(df)}")
                tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium7", showRowStripes=False)
                ws.add_table(tbl)
            buf = io.BytesIO(); wb.save(buf)
        st.success("La matriz ha sido generada con éxito.")
        st.download_button("⬇ Descargar Reporte_SDP.xlsx", data=buf.getvalue(),
            file_name="Reporte_SDP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown('<hr style="border-color:#e0e0e0;margin-top:40px;margin-bottom:10px">',
            unsafe_allow_html=True)
st.markdown('<div style="text-align:center;padding:10px;font-size:.85rem;color:#888">'
            'Secretaría Distrital de Planeación · Seguimiento de Convocatorias y Proyectos'
            '</div>', unsafe_allow_html=True)
