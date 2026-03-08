"""
Convocatorias & Proyectos SDP — Streamlit + Supabase
Schema Django exacto. Relación: contenido_proyecto.convocatoria_id → contenido_convocatorias.id
"""
import io, re, math
import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

st.set_page_config(page_title="Convocatorias & Proyectos SDP",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
section[data-testid="stSidebar"]>div:first-child{background:#f8f9fa!important;border-right:1px solid #196B24}
.stTabs [data-baseweb="tab-list"]{border-bottom:2px solid #196B24;gap:4px}
.stTabs [data-baseweb="tab"]{font-weight:600;font-size:.84rem;border-radius:6px 6px 0 0;padding:8px 18px;background:transparent;color:#333}
.stTabs [aria-selected="true"]{background:#196B24!important;color:#fff!important}
.stDownloadButton>button,.stButton>button[kind="primary"]{background:#196B24!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;padding:10px 24px!important}
</style>""", unsafe_allow_html=True)

# ── Credentials ───────────────────────────────────────────────────────────────
try:
    _URL = st.secrets["supabase"]["url"]
    _KEY = st.secrets["supabase"]["key"]
except Exception:
    _URL = "https://keoredvjrhcgvnrrvnfa.supabase.co"
    _KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtlb3JlZHZqcmhjZ3ZucnJ2bmZhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI1NzA0MDYsImV4cCI6MjA4ODE0NjQwNn0."
            "h9QNpcbiMXZfeheOAVHtYnC4-n8luCg92s-Xd_BFrZA")

GREENS = ["#196B24","#1e8c2e","#27b33b","#3ddb52","#57e368",
          "#7aeb87","#9df2a7","#b8f5c0","#2ec644","#4fc45a"]

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
        v=float(val)
        if v>=1e12: return f"${v/1e12:.1f}T"
        if v>=1e9:  return f"${v/1e9:.1f}B"
        if v>=1e6:  return f"${v/1e6:.1f}M"
        if v>=1e3:  return f"${v/1e3:.0f}K"
        return f"${v:,.0f}"
    except: return str(val)

# ── Charts ────────────────────────────────────────────────────────────────────
def _card(content, title=None):
    hdr = (f'<div style="font-family:\'DM Serif Display\',serif;font-size:.95rem;color:#333333;'
           f'margin-bottom:12px;padding-bottom:7px;border-bottom:2px solid #196B24">{title}</div>'
           if title else "")
    return (f'<div style="background:#ffffff;border:1px solid #e0e0e0;'
            f'border-radius:10px;padding:18px 20px 14px;box-shadow:0 2px 4px rgba(0,0,0,0.02)">{hdr}{content}</div>')

def bar_chart(data, title, max_bars=20, fmt_val=None):
    data = data.dropna().sort_values(ascending=False).head(max_bars)
    if data.empty: return ""
    mx = data.max() or 1
    rows = ""
    for i,(label,val) in enumerate(data.items()):
        pct = round(val/mx*100,1)
        alpha = max(0.4, 1-i*0.028)
        color = f"rgba(25,107,36,{alpha:.2f})"
        disp = fmt_val(val) if fmt_val else (f"{int(val):,}" if float(val)==int(float(val)) else f"{val:,.1f}")
        rows += (f'<div style="display:flex;align-items:center;margin-bottom:6px;gap:9px">'
                 f'<div style="width:175px;font-size:.73rem;color:#2e7d32;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0" title="{label}">{label}</div>'
                 f'<div style="flex:1;background:#f0f0f0;border-radius:3px;height:21px;position:relative">'
                 f'<div style="width:{pct}%;background:{color};height:100%;border-radius:3px"></div>'
                 f'<span style="position:absolute;right:7px;top:3px;font-size:.71rem;font-weight:700;color:#333333">{disp}</span>'
                 f'</div></div>')
    return _card(rows, title)

def donut_chart(data, title, top_n=8):
    data = data.dropna()
    total = data.sum()
    if total == 0: return ""
    top = data.sort_values(ascending=False).head(top_n)
    cx=cy=68; r=52; ir=28; angle=-90.0; paths=""
    for i,(_,val) in enumerate(top.items()):
        sw=(val/total)*360; end=angle+sw
        a1,a2=math.radians(angle),math.radians(end)
        x1,y1=cx+r*math.cos(a1),cy+r*math.sin(a1)
        x2,y2=cx+r*math.cos(a2),cy+r*math.sin(a2)
        ix1,iy1=cx+ir*math.cos(a2),cy+ir*math.sin(a2)
        ix2,iy2=cx+ir*math.cos(a1),cy+ir*math.sin(a1)
        lg=1 if sw>180 else 0; c=GREENS[i%len(GREENS)]
        paths+=(f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {lg},1 {x2:.1f},{y2:.1f} '
                f'L{ix1:.1f},{iy1:.1f} A{ir},{ir} 0 {lg},0 {ix2:.1f},{iy2:.1f} Z" '
                f'fill="{c}" stroke="#ffffff" stroke-width="2"/>')
        angle=end
    legend=""
    for i,(label,val) in enumerate(top.items()):
        pct=round(val/total*100,1)
        legend+=(f'<div style="display:flex;align-items:center;gap:5px;margin-bottom:4px">'
                 f'<div style="width:8px;height:8px;border-radius:50%;background:{GREENS[i%len(GREENS)]};flex-shrink:0"></div>'
                 f'<div style="font-size:.7rem;color:#555555;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="{label}">{label}</div>'
                 f'<div style="font-size:.7rem;font-weight:700;color:#196B24">{pct}%</div></div>')
    svg=(f'<svg width="136" height="136" viewBox="0 0 136 136">{paths}'
         f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-size="15" font-family="DM Serif Display" fill="#333333" font-weight="bold">{int(total)}</text>'
         f'<text x="{cx}" y="{cy+17}" text-anchor="middle" font-size="8" font-family="DM Sans" fill="#555555">total</text></svg>')
    inner=(f'<div style="display:flex;gap:14px;align-items:center">'
           f'<div style="flex-shrink:0">{svg}</div>'
           f'<div style="flex:1;overflow:hidden">{legend}</div></div>')
    return _card(inner, title)

def kpi(label, value, sub=""):
    return (f'<div style="background:#ffffff;border:1px solid #e0e0e0;border-left:4px solid #196B24;'
            f'border-radius:8px;padding:15px 17px;margin-bottom:6px;box-shadow:0 2px 4px rgba(0,0,0,0.02)">'
            f'<div style="font-size:.66rem;letter-spacing:.09em;text-transform:uppercase;color:#2e7d32;font-weight:600;margin-bottom:3px">{label}</div>'
            f'<div style="font-family:\'DM Serif Display\',serif;font-size:1.9rem;color:#333333;line-height:1">{value}</div>'
            f'<div style="font-size:.72rem;color:#555555;margin-top:3px">{sub}</div></div>')

def sec_title(text, sub=""):
    s=(f'<div style="font-family:\'DM Serif Display\',serif;font-size:1.28rem;'
       f'color:#333333;margin:22px 0 4px;padding-bottom:6px;border-bottom:2px solid #196B24">{text}</div>')
    if sub: s+=f'<div style="font-size:.77rem;color:#555555;margin-bottom:11px">{sub}</div>'
    return s

# ══════════════════════════════════════════════════════════════════════════════
# LOAD ALL DATA
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def load_all():
    # Lookups
    estados   = {r["id"]:r["estado"]             for r in _fetch("contenido_estado")}
    deps      = {r["id"]:r["dependencia"]         for r in _fetch("contenido_dependencia")}
    resps     = {r["id"]:r["responsable"]         for r in _fetch("contenido_responsable")}
    sectores  = {r["id"]:r["sector"]              for r in _fetch("contenido_sectores")}
    segmentos = {r["id"]:r["segmento"]            for r in _fetch("contenido_segmentos")}
    ubicacs   = {r["id"]:r["ubicacion"]           for r in _fetch("contenido_ubicacion")}
    municipios= {r["id"]:r["municipio"]           for r in _fetch("contenido_municipios")}
    clf_ben   = {r["id"]:r["tipo_beneficiario"]   for r in _fetch("contenido_clasificacionbeneficiario")}
    vigencias = {r["id"]:r["vigencia"]            for r in _fetch("contenido_clasificacionvigencia")}
    clf_ind   = {r["id"]:{
                    "codigo": r["codigo_indicador"], "nombre": r["nombre_indicador"],
                    "meta_c": float(r["meta_cuatrienio"] or 0),
                    "m2024":  r.get("meta_fisica_esperada_2024"),
                    "m2025":  r.get("meta_fisica_esperada_2025"),
                    "m2026":  r.get("meta_fisica_esperada_2026"),
                    "m2027":  r.get("meta_fisica_esperada_2027"),
                    "resp":   r.get("responsable",""),
                 } for r in _fetch("contenido_clasificacionindicadormga")}

    # M2M
    def m2m(table, fk, vk, vmap):
        d={}
        for r in _fetch(table):
            d.setdefault(r[fk],[]).append(vmap.get(r[vk], str(r[vk])))
        return d

    conv_sec = m2m("contenido_convocatorias_sectores",   "convocatorias_id","sectores_id",   sectores)
    conv_seg = m2m("contenido_convocatorias_segmento",   "convocatorias_id","segmentos_id",  segmentos)
    conv_ubi = m2m("contenido_convocatorias_ubicacion",  "convocatorias_id","ubicacion_id",  ubicacs)
    conv_dep = m2m("contenido_convocatorias_dependencia","convocatorias_id","dependencia_id",deps)
    proy_mun = m2m("contenido_proyecto_municipios",      "proyecto_id",     "municipios_id", municipios)

    # Beneficiarios
    ben_d={}
    for r in _fetch("contenido_beneficiarios"):
        pid=r.get("proyecto_id")
        if pid: ben_d.setdefault(pid,[]).append({"tipo":clf_ben.get(r.get("beneficiario_id"),"?"),"n":r.get("numero_beneficiarios",0)})

    # Indicadores MGA
    ind_d={}
    for r in _fetch("contenido_indicadormga"):
        pid=r.get("proyecto_id")
        if pid:
            clf=clf_ind.get(r.get("indicadores_id"),{})
            ind_d.setdefault(pid,[]).append({
                "codigo":clf.get("codigo",""), "nombre":clf.get("nombre",""),
                "vigencia":vigencias.get(r.get("vigencia_id"),""),
                "meta_proyecto":float(r.get("meta_proyecto") or 0),
                "meta_cuatrienio":clf.get("meta_c",0),
                "m2024":clf.get("m2024"),"m2025":clf.get("m2025"),
                "m2026":clf.get("m2026"),"m2027":clf.get("m2027"),
                "responsable_mga":clf.get("resp",""),
            })

    # CONVOCATORIAS
    conv_rows=_fetch("contenido_convocatorias")
    conv_list=[]
    for r in conv_rows:
        cid=r["id"]
        conv_list.append({
            "id":cid,
            "Convocatoria":       r["nombre_convocatoria"],
            "Estado":             estados.get(r.get("estado_id"),"—"),
            "Fecha apertura":     _fdate(r.get("fecha_apertura")),
            "Fecha cierre":       _fdate(r.get("fecha_cierre")),
            "Monto":              float(r.get("monto") or 0),
            "Contacto":           r.get("contacto",""),
            "Qué ofrece":         r.get("que_ofrece","") or "",
            "Quiénes participan": r.get("quienes_pueden_participar","") or "",
            "Público priorizado": r.get("publico_priorizado","") or "",
            "Sectores":           " · ".join(conv_sec.get(cid,[])),
            "Segmentos":          " · ".join(conv_seg.get(cid,[])),
            "Ubicación":          " · ".join(conv_ubi.get(cid,[])),
            "Dependencias":       " · ".join(conv_dep.get(cid,[])),
            "N° proyectos":       0,
        })
    df_conv = pd.DataFrame(conv_list) if conv_list else pd.DataFrame()

    # PROYECTOS
    proy_rows=_fetch("contenido_proyecto")
    proy_list=[]
    for r in proy_rows:
        pid=r["id"]
        bens=ben_d.get(pid,[])
        inds=ind_d.get(pid,[])
        proy_list.append({
            "id":pid,
            "convocatoria_id":    r.get("convocatoria_id"),
            "Proyecto":           r["nombre_proyecto"],
            "BPIN":               r.get("bpin",""),
            "Valor":              float(r.get("valor_proyecto") or 0),
            "Contrapartida":      float(r.get("monto_contrapartida") or 0),
            "Dependencia":        deps.get(r.get("dependencia_id"),"—"),
            "Responsable":        resps.get(r.get("responsable_id"),"—"),
            "Municipios":         " · ".join(proy_mun.get(pid,[])),
            "Total beneficiarios":sum(b["n"] for b in bens),
            "Tipos beneficiarios":", ".join(f"{b['tipo']} ({b['n']})" for b in bens),
            "N° indicadores MGA": len(inds),
            "Indicadores MGA":    "; ".join(f"{i['codigo']} – {i['nombre']}" for i in inds),
        })
    df_proy = pd.DataFrame(proy_list) if proy_list else pd.DataFrame()

    # Contar proyectos por convocatoria
    if not df_conv.empty and not df_proy.empty and "convocatoria_id" in df_proy.columns:
        cnt=df_proy.groupby("convocatoria_id")["id"].count().to_dict()
        df_conv["N° proyectos"]=df_conv["id"].map(cnt).fillna(0).astype(int)

    # INDICADORES (tabla plana)
    ind_rows=[]
    proy_names={r["id"]:r["nombre_proyecto"] for r in proy_rows}
    for pid,inds in ind_d.items():
        for i in inds:
            ind_rows.append({"Proyecto":proy_names.get(pid,"—"),"proyecto_id":pid,**i})
    df_ind = pd.DataFrame(ind_rows) if ind_rows else pd.DataFrame()

    # RELACIONES (join)
    if not df_proy.empty and not df_conv.empty and "convocatoria_id" in df_proy.columns:
        df_rel = df_proy.merge(
            df_conv[["id","Convocatoria","Estado","Monto","Sectores","Segmentos","Fecha apertura","Fecha cierre"]],
            left_on="convocatoria_id", right_on="id", how="left", suffixes=("","_c")
        ).rename(columns={"Monto":"Monto convocatoria","Estado":"Estado convocatoria"})
        df_rel["Cobertura (%)"] = df_rel.apply(
            lambda row: round(row["Valor"]/row["Monto convocatoria"]*100,1)
            if row.get("Monto convocatoria",0) else None, axis=1)
        df_rel = df_rel.drop(columns=["id_c"], errors="ignore")
    else:
        df_rel = pd.DataFrame()

    return df_conv, df_proy, df_rel, df_ind

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR HEADER
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div style="padding:12px 0 14px">'
        '<div style="font-family:\'DM Serif Display\',serif;font-size:1.28rem;color:#333333">SDP</div>'
        '<div style="color:#555555;font-size:.77rem;margin-top:2px">Convocatorias & Proyectos</div></div>'
        '<hr style="border-color:#196B24;margin-bottom:12px">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("Conectando con Supabase…"):
    try:
        df_conv, df_proy, df_rel, df_ind = load_all()
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        st.stop()

if df_conv.empty and df_proy.empty:
    st.warning("No se encontraron datos en Supabase.")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────────
estados_opts  = sorted(df_conv["Estado"].dropna().unique()) if not df_conv.empty else []
sectores_opts = sorted({s.strip() for row in df_conv["Sectores"] if row
                        for s in row.split(" · ") if s.strip()}) if not df_conv.empty else []
dep_opts      = sorted(df_proy["Dependencia"].dropna().unique()) if not df_proy.empty else []

with st.sidebar:
    st.markdown('<div style="font-size:.65rem;letter-spacing:.09em;text-transform:uppercase;color:#2e7d32;font-weight:600;margin-bottom:7px">Filtros</div>', unsafe_allow_html=True)
    sel_est  = st.multiselect("Estado convocatoria", estados_opts,  placeholder="Todos")
    sel_sec  = st.multiselect("Sector",              sectores_opts, placeholder="Todos")
    sel_dep  = st.multiselect("Dependencia",         dep_opts,      placeholder="Todas")
    st.markdown('<hr style="border-color:#e0e0e0;margin:11px 0 8px">', unsafe_allow_html=True)
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
if not df_i.empty and sel_dep: df_i = df_i[df_i["proyecto_id"].isin(df_p["id"])]

# ══════════════════════════════════════════════════════════════════════════════
# HERO + KPIs
# ══════════════════════════════════════════════════════════════════════════════
n_conv=df_c["id"].nunique() if not df_c.empty else 0
n_proy=df_p["id"].nunique() if not df_p.empty else 0
m_conv=df_c["Monto"].sum() if not df_c.empty else 0
v_proy=df_p["Valor"].sum() if not df_p.empty else 0
n_ind=len(df_i) if not df_i.empty else 0
conv_cp=df_c[df_c["N° proyectos"]>0]["id"].nunique() if not df_c.empty else 0
pct_cp=round(conv_cp/max(n_conv,1)*100)

st.markdown(
    '<div style="background:linear-gradient(135deg,#e8f5e9 0%,#c8e6c9 100%);border-radius:12px;padding:26px 34px 22px;margin-bottom:16px;border:1px solid #a5d6a7">'
    '<div style="font-family:\'DM Serif Display\',serif;font-size:1.7rem;color:#196B24;margin:0 0 4px">Convocatorias & Proyectos SDP</div>'
    '<div style="color:#2e7d32;font-size:.81rem;font-weight:500">Datos en tiempo real · Supabase · actualización cada 5 min</div></div>',
    unsafe_allow_html=True)

k1,k2,k3,k4,k5,k6 = st.columns(6)
k1.markdown(kpi("Convocatorias",   n_conv,           "registros"),            unsafe_allow_html=True)
k2.markdown(kpi("Proyectos",       n_proy,           "registros"),            unsafe_allow_html=True)
k3.markdown(kpi("Con proyectos",   f"{conv_cp}",     f"{pct_cp}% de conv."), unsafe_allow_html=True)
k4.markdown(kpi("Monto convoc.",   fmt_money(m_conv),"suma total"),           unsafe_allow_html=True)
k5.markdown(kpi("Valor proyectos", fmt_money(v_proy),"suma total"),           unsafe_allow_html=True)
k6.markdown(kpi("Indicadores MGA", n_ind,            "registros"),            unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "Convocatorias","Proyectos","Relaciones","Indicadores MGA","Reporte Excel"])

# ─── TAB 1 CONVOCATORIAS ──────────────────────────────────────────────────────
with tab1:
    st.markdown(sec_title("Convocatorias", f"{n_conv} registros"), unsafe_allow_html=True)
    if not df_c.empty:
        ca,cb = st.columns([3,2])
        with ca:
            st.markdown(bar_chart(df_c["Estado"].value_counts(),"Por estado"), unsafe_allow_html=True)
            sec_exp=(df_c["Sectores"].str.split(" · ").explode().str.strip().value_counts())
            sec_exp=sec_exp[sec_exp.index.str.len()>0]
            if not sec_exp.empty:
                st.markdown(bar_chart(sec_exp,"Por sector",max_bars=15), unsafe_allow_html=True)
        with cb:
            seg_exp=(df_c["Segmentos"].str.split(" · ").explode().str.strip().value_counts())
            seg_exp=seg_exp[seg_exp.index.str.len()>0]
            if not seg_exp.empty:
                st.markdown(donut_chart(seg_exp,"Por segmento"), unsafe_allow_html=True)
            ubi_exp=(df_c["Ubicación"].str.split(" · ").explode().str.strip().value_counts())
            ubi_exp=ubi_exp[ubi_exp.index.str.len()>0]
            if not ubi_exp.empty:
                st.markdown(donut_chart(ubi_exp,"Por ubicación"), unsafe_allow_html=True)
            st.markdown(bar_chart(df_c.groupby("Estado")["Monto"].sum().sort_values(ascending=False),
                "Monto por estado",fmt_val=fmt_money), unsafe_allow_html=True)

    st.markdown(sec_title("Listado"), unsafe_allow_html=True)
    lc=["Convocatoria","Estado","Fecha apertura","Fecha cierre","Monto","Sectores","Segmentos","Ubicación","N° proyectos","Contacto"]
    lc=[c for c in lc if c in df_c.columns]
    st.dataframe(df_c[lc].reset_index(drop=True), use_container_width=True, height=400, hide_index=True,
        column_config={"Convocatoria":st.column_config.TextColumn(width=280),
                       "Monto":st.column_config.NumberColumn("Monto $",format="$%,.0f"),
                       "N° proyectos":st.column_config.NumberColumn("Proyectos",width=90)})

    st.markdown(sec_title("Detalle convocatoria"), unsafe_allow_html=True)
    if not df_c.empty:
        sel=st.selectbox("Selecciona",df_c["Convocatoria"].tolist(),key="dc")
        if sel:
            row=df_c[df_c["Convocatoria"]==sel].iloc[0]
            d1,d2,d3,d4=st.columns(4)
            d1.metric("Estado",row["Estado"]); d2.metric("Monto",fmt_money(row["Monto"]))
            d3.metric("Proyectos",int(row["N° proyectos"])); d4.metric("Apertura",row["Fecha apertura"])
            with st.expander("Descripción completa"):
                for f in ["Qué ofrece","Quiénes participan","Público priorizado","Sectores","Segmentos","Ubicación","Dependencias","Contacto"]:
                    if f in row and str(row[f]).strip() and str(row[f]) not in ("—",""):
                        st.markdown(f"**{f}:** {row[f]}")
            proy_sub=df_p[df_p["convocatoria_id"]==int(row["id"])]
            if not proy_sub.empty:
                st.caption(f"{len(proy_sub)} proyecto(s) asociado(s)")
                pc=["Proyecto","BPIN","Valor","Dependencia","Responsable","Municipios"]
                pc=[c for c in pc if c in proy_sub.columns]
                st.dataframe(proy_sub[pc].reset_index(drop=True), use_container_width=True,
                    height=200, hide_index=True,
                    column_config={"Valor":st.column_config.NumberColumn("Valor $",format="$%,.0f")})

# ─── TAB 2 PROYECTOS ──────────────────────────────────────────────────────────
with tab2:
    st.markdown(sec_title("Proyectos", f"{n_proy} registros"), unsafe_allow_html=True)
    if not df_p.empty:
        pa,pb=st.columns([3,2])
        with pa:
            st.markdown(bar_chart(df_p["Dependencia"].value_counts(),"Por dependencia",max_bars=15), unsafe_allow_html=True)
            st.markdown(bar_chart(df_p.nlargest(15,"Valor").set_index("Proyecto")["Valor"],
                "Top 15 por valor",fmt_val=fmt_money), unsafe_allow_html=True)
        with pb:
            st.markdown(donut_chart(df_p["Responsable"].value_counts(),"Por responsable"), unsafe_allow_html=True)
            mun_exp=(df_p["Municipios"].str.split(" · ").explode().str.strip().value_counts())
            mun_exp=mun_exp[mun_exp.index.str.len()>0]
            if not mun_exp.empty:
                st.markdown(donut_chart(mun_exp,"Por municipio"), unsafe_allow_html=True)
            ben_dep=df_p.groupby("Dependencia")["Total beneficiarios"].sum()
            ben_dep=ben_dep[ben_dep>0]
            if not ben_dep.empty:
                st.markdown(bar_chart(ben_dep.sort_values(ascending=False),"Beneficiarios por dependencia"), unsafe_allow_html=True)

    st.markdown(sec_title("Listado"), unsafe_allow_html=True)
    ps=["Proyecto","BPIN","Valor","Contrapartida","Dependencia","Responsable","Municipios","Total beneficiarios","N° indicadores MGA"]
    ps=[c for c in ps if c in df_p.columns]
    st.dataframe(df_p[ps].reset_index(drop=True), use_container_width=True, height=420, hide_index=True,
        column_config={"Proyecto":st.column_config.TextColumn(width=280),
                       "Valor":st.column_config.NumberColumn("Valor $",format="$%,.0f"),
                       "Contrapartida":st.column_config.NumberColumn("Contrapartida",format="$%,.0f"),
                       "Total beneficiarios":st.column_config.NumberColumn("Beneficiarios",width=110),
                       "N° indicadores MGA":st.column_config.NumberColumn("Indicadores",width=100)})

    st.markdown(sec_title("Detalle proyecto"), unsafe_allow_html=True)
    if not df_p.empty:
        sel_p=st.selectbox("Selecciona",df_p["Proyecto"].tolist(),key="dp")
        if sel_p:
            rp=df_p[df_p["Proyecto"]==sel_p].iloc[0]
            p1,p2,p3,p4=st.columns(4)
            p1.metric("Valor",fmt_money(rp["Valor"])); p2.metric("Contrapartida",fmt_money(rp["Contrapartida"]))
            p3.metric("Beneficiarios",int(rp["Total beneficiarios"])); p4.metric("BPIN",rp["BPIN"])
            with st.expander("Detalles completos"):
                for f in ["Dependencia","Responsable","Municipios","Tipos beneficiarios","Indicadores MGA"]:
                    if f in rp and str(rp[f]).strip() and str(rp[f]) not in ("—","0",""):
                        st.markdown(f"**{f}:** {rp[f]}")
            ind_sub=df_i[df_i["proyecto_id"]==int(rp["id"])] if not df_i.empty else pd.DataFrame()
            if not ind_sub.empty:
                st.caption(f"{len(ind_sub)} indicador(es) MGA")
                ic=["codigo","nombre","vigencia","meta_proyecto","meta_cuatrienio","m2024","m2025","m2026","m2027"]
                ic=[c for c in ic if c in ind_sub.columns]
                st.dataframe(ind_sub[ic].reset_index(drop=True), use_container_width=True, height=200, hide_index=True)

# ─── TAB 3 RELACIONES ─────────────────────────────────────────────────────────
with tab3:
    st.markdown(sec_title("Relaciones Convocatoria → Proyecto",
        "contenido_proyecto.convocatoria_id → contenido_convocatorias.id"), unsafe_allow_html=True)
    if df_r.empty:
        st.info("No hay relaciones con los filtros actuales.")
    else:
        ra,rb=st.columns([3,2])
        with ra:
            pxc=df_r.groupby("Convocatoria")["id"].nunique().sort_values(ascending=False)
            st.markdown(bar_chart(pxc,"Proyectos por convocatoria",max_bars=20), unsafe_allow_html=True)
            vxd=df_r.groupby("Dependencia")["Valor"].sum().sort_values(ascending=False)
            st.markdown(bar_chart(vxd,"Valor por dependencia",fmt_val=fmt_money), unsafe_allow_html=True)
        with rb:
            vxc=df_r.groupby("Convocatoria")["Valor"].sum().sort_values(ascending=False)
            st.markdown(bar_chart(vxc.head(10),"Valor por convocatoria (top 10)",fmt_val=fmt_money), unsafe_allow_html=True)
            cob=df_r["Cobertura (%)"].dropna()
            if not cob.empty:
                cob_r=pd.cut(cob,bins=[0,25,50,75,100,float("inf")],labels=["0-25%","25-50%","50-75%","75-100%",">100%"])
                st.markdown(donut_chart(cob_r.value_counts(),"Distribución cobertura"), unsafe_allow_html=True)

        st.markdown(sec_title("Tabla de relaciones"), unsafe_allow_html=True)
        rc=["Convocatoria","Estado convocatoria","Sectores","Proyecto","BPIN","Valor",
            "Dependencia","Responsable","Fecha apertura","Fecha cierre","Cobertura (%)"]
        rc=[c for c in rc if c in df_r.columns]
        st.dataframe(df_r[rc].reset_index(drop=True), use_container_width=True, height=450, hide_index=True,
            column_config={"Convocatoria":st.column_config.TextColumn(width=230),
                           "Proyecto":st.column_config.TextColumn(width=210),
                           "Valor":st.column_config.NumberColumn("Valor $",format="$%,.0f"),
                           "Cobertura (%)":st.column_config.NumberColumn("Cob. %",format="%.1f%%")})

        sin=df_c[df_c["N° proyectos"]==0] if not df_c.empty else pd.DataFrame()
        if not sin.empty:
            with st.expander(f"{len(sin)} convocatoria(s) sin proyectos"):
                sc=["Convocatoria","Estado","Monto","Sectores"]
                sc=[c for c in sc if c in sin.columns]
                st.dataframe(sin[sc].reset_index(drop=True), use_container_width=True, hide_index=True)

# ─── TAB 4 INDICADORES MGA ────────────────────────────────────────────────────
with tab4:
    st.markdown(sec_title("Indicadores MGA",
        "contenido_indicadormga → contenido_clasificacionindicadormga + contenido_clasificacionvigencia"),
        unsafe_allow_html=True)
    if df_i.empty:
        st.info("No hay indicadores MGA con los filtros actuales.")
    else:
        ia,ib=st.columns([3,2])
        with ia:
            st.markdown(bar_chart(df_i["nombre"].value_counts().head(15),"Indicadores más usados"), unsafe_allow_html=True)
            meta_proy=df_i.groupby("nombre")["meta_proyecto"].sum().sort_values(ascending=False).head(12)
            meta_proy=meta_proy[meta_proy>0]
            if not meta_proy.empty:
                st.markdown(bar_chart(meta_proy,"Meta proyecto por indicador"), unsafe_allow_html=True)
        with ib:
            st.markdown(donut_chart(df_i["vigencia"].astype(str).value_counts(),"Por vigencia"), unsafe_allow_html=True)
            ixp=df_i.groupby("Proyecto")["codigo"].count().sort_values(ascending=False).head(10)
            st.markdown(bar_chart(ixp,"Indicadores por proyecto (top 10)"), unsafe_allow_html=True)

        st.markdown(sec_title("Tabla de indicadores"), unsafe_allow_html=True)
        ishow=["Proyecto","codigo","nombre","vigencia","meta_proyecto","meta_cuatrienio","m2024","m2025","m2026","m2027","responsable_mga"]
        ishow=[c for c in ishow if c in df_i.columns]
        st.dataframe(df_i[ishow].rename(columns={
            "codigo":"Código","nombre":"Indicador","vigencia":"Vigencia",
            "meta_proyecto":"Meta proy.","meta_cuatrienio":"Meta cuatrienio",
            "m2024":"2024","m2025":"2025","m2026":"2026","m2027":"2027",
            "responsable_mga":"Responsable MGA"}).reset_index(drop=True),
            use_container_width=True, height=420, hide_index=True,
            column_config={"Proyecto":st.column_config.TextColumn(width=230),
                           "Indicador":st.column_config.TextColumn(width=250)})

# ─── TAB 5 REPORTE EXCEL ──────────────────────────────────────────────────────
with tab5:
    st.markdown(sec_title("Reporte Excel","4 hojas: Convocatorias · Proyectos · Relaciones · Indicadores MGA"), unsafe_allow_html=True)
    opt=st.radio("Datos",["Todo (sin filtros)","Solo datos filtrados"],horizontal=True)
    ec=df_c if opt=="Solo datos filtrados" else df_conv
    ep=df_p if opt=="Solo datos filtrados" else df_proy
    er=df_r if opt=="Solo datos filtrados" else df_rel
    ei=df_i if opt=="Solo datos filtrados" else df_ind
    x1,x2,x3,x4=st.columns(4)
    x1.metric("Convocatorias",ec["id"].nunique() if not ec.empty else 0)
    x2.metric("Proyectos",    ep["id"].nunique() if not ep.empty else 0)
    x3.metric("Relaciones",   len(er) if not er.empty else 0)
    x4.metric("Indicadores",  len(ei) if not ei.empty else 0)
    st.markdown("<br>",unsafe_allow_html=True)
    if st.button("Generar reporte",type="primary"):
        with st.spinner("Construyendo Excel…"):
            H_FILL=PatternFill("solid",fgColor="196B24")
            H_FONT=Font(bold=True,color="FFFFFF",name="Arial",size=10)
            C_FONT=Font(name="Arial",size=9)
            WHITE=PatternFill("solid",fgColor="FFFFFF")
            THIN=Border(left=Side(style="thin",color="CCCCCC"),right=Side(style="thin",color="CCCCCC"),
                        top=Side(style="thin",color="CCCCCC"),bottom=Side(style="thin",color="CCCCCC"))
            wb=Workbook(); wb.remove(wb.active)
            sheets_def=[
                ("Convocatorias",ec,["Convocatoria","Estado","Fecha apertura","Fecha cierre","Monto","Sectores","Segmentos","Ubicación","Dependencias","N° proyectos","Contacto","Qué ofrece","Quiénes participan","Público priorizado"]),
                ("Proyectos",ep,["Proyecto","BPIN","Valor","Contrapartida","Dependencia","Responsable","Municipios","Total beneficiarios","Tipos beneficiarios","N° indicadores MGA","Indicadores MGA"]),
                ("Relaciones",er,["Convocatoria","Estado convocatoria","Sectores","Proyecto","BPIN","Valor","Dependencia","Responsable","Fecha apertura","Fecha cierre","Cobertura (%)"]),
                ("Indicadores MGA",ei,["Proyecto","codigo","nombre","vigencia","meta_proyecto","meta_cuatrienio","m2024","m2025","m2026","m2027","responsable_mga"]),
            ]
            COL_W={"Convocatoria":42,"Proyecto":42,"nombre":42,"Qué ofrece":50,"Quiénes participan":40,"Sectores":22,"Segmentos":20,"Municipios":22,"Tipos beneficiarios":30,"Indicadores MGA":40}
            for sname,df,cols in sheets_def:
                if df is None or df.empty: continue
                cols=[c for c in cols if c in df.columns]
                ws=wb.create_sheet(sname); ws.sheet_view.showGridLines=False
                for ci,col in enumerate(cols,1):
                    c=ws.cell(row=1,column=ci,value=col)
                    c.font=H_FONT; c.fill=H_FILL
                    c.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); c.border=THIN
                ws.row_dimensions[1].height=28
                for ri,(_,row) in enumerate(df[cols].iterrows(),2):
                    for ci,col in enumerate(cols,1):
                        val=row[col]
                        if pd.isna(val): val=""
                        c=ws.cell(row=ri,column=ci,value=val)
                        c.font=C_FONT; c.fill=WHITE; c.border=THIN
                        c.alignment=Alignment(horizontal="left",vertical="top",wrap_text=True)
                    ws.row_dimensions[ri].height=30
                for ci,col in enumerate(cols,1):
                    ws.column_dimensions[get_column_letter(ci)].width=COL_W.get(col,15)
                ws.freeze_panes="A2"
                tname="T_"+re.sub(r"[^A-Za-z0-9]","_",sname)
                tbl=Table(displayName=tname,ref=f"A1:{get_column_letter(len(cols))}{1+len(df)}")
                tbl.tableStyleInfo=TableStyleInfo(name="TableStyleMedium7",showRowStripes=False)
                ws.add_table(tbl)
            buf=io.BytesIO(); wb.save(buf)
        st.success("Listo.")
        st.download_button("Descargar Reporte_SDP.xlsx",data=buf.getvalue(),
            file_name="Reporte_SDP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
