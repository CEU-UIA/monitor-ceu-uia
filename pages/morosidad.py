import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import streamlit.components.v1 as components

# ============================================================
# Config
# ============================================================
MORA_PATH  = "assets/mora_por_actividad.xlsx"
COL_SECTOR = "Sector_1_dígito"
COL_ID     = "id"
COL_NOMBRE = "Nombre"
COL_SALDO  = "saldo_total (miles de $)"
COL_IRREG  = "saldo_irregular (miles de $)"
COL_MORA   = "tasa_mora"

# IDs que pertenecen a Industria Manufacturera (101–332 inclusive)
ID_IND_MIN = 101
ID_IND_MAX = 332
LABEL_IND  = "Industria manufacturera"


# ============================================================
# Loader
# ============================================================
@st.cache_data(show_spinner=False)
def load_mora():
    df = pd.read_excel(MORA_PATH, sheet_name="Monitor", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    # Excluir fila id=0
    if COL_ID in df.columns:
        df[COL_ID] = pd.to_numeric(df[COL_ID], errors="coerce")
        df = df[df[COL_ID].fillna(-1) != 0].copy()

    # Excluir Nombre NaN
    if COL_NOMBRE in df.columns:
        df = df[df[COL_NOMBRE].notna()].copy()
        df = df[df[COL_NOMBRE].astype(str).str.strip().str.lower() != "nan"].copy()

    # Normalizar tasa_mora
    if COL_MORA in df.columns:
        def _parse(x):
            try:
                v = float(str(x).replace("%", "").replace(",", ".").strip())
                return v if v > 1 else v * 100
            except:
                return float("nan")
        df[COL_MORA] = df[COL_MORA].apply(_parse)

    for c in [COL_SALDO, COL_IRREG]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if COL_SECTOR in df.columns:
        df[COL_SECTOR] = df[COL_SECTOR].astype(str).str.strip()
        df = df[~df[COL_SECTOR].str.lower().isin(["nan", "none", ""])].copy()

    # Reclasificar ids 101–332 como Industria manufacturera
    mask_ind = (df[COL_ID] >= ID_IND_MIN) & (df[COL_ID] <= ID_IND_MAX)
    df.loc[mask_ind, COL_SECTOR] = LABEL_IND

    return df


# ============================================================
# Helpers
# ============================================================
def fmt_pct(x, dec=1):
    try:
        return f"{float(x):.{dec}f}".replace(".", ",") + "%"
    except:
        return "—"

def fmt_millon(x):
    try:
        # miles de $ → millones de $
        return f"${float(x)/1_000:,.0f}M".replace(",", ".")
    except:
        return "—"

def _agrupar(df_in, col_grupo):
    """Agrupa por col_grupo, suma saldo e irregular, recalcula mora."""
    g = (
        df_in.groupby(col_grupo, as_index=False)
        .agg(**{COL_SALDO: (COL_SALDO, "sum"), COL_IRREG: (COL_IRREG, "sum")})
    )
    g[COL_MORA] = g.apply(
        lambda r: (r[COL_IRREG] / r[COL_SALDO] * 100) if r[COL_SALDO] > 0 else float("nan"),
        axis=1,
    )
    return g


# ============================================================
# Panel celestito
# ============================================================
CSS_PANEL = """
<style>
  .fx-panel-wrap {
    background: rgba(230,243,255,0.55);
    border: 1px solid rgba(15,55,100,0.10);
    border-radius: 22px;
    padding: 16px 16px 26px 16px;
    box-shadow: 0 10px 18px rgba(15,55,100,0.06);
    margin-top: 10px;
  }
  .fx-panel-title {
    font-size: 12px; font-weight: 900;
    color: rgba(20,50,79,0.78); margin: 0 0 6px 2px; letter-spacing: 0.01em;
  }
  .fx-panel-gap { height: 16px; }
  .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"] {
    background: #0b2a55 !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
  }
  .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"] * {
    color: #8fc2ff !important; fill: #8fc2ff !important; font-weight: 800 !important;
  }
</style>
"""

def _inject_panel(marker_id: str):
    st.markdown(f"<span id='{marker_id}'></span>", unsafe_allow_html=True)
    components.html(
        f"""
        <script>
        (function() {{
          function apply() {{
            const m = window.parent.document.getElementById('{marker_id}');
            if (!m) return;
            const b = m.closest('div[data-testid="stVerticalBlock"]');
            if (b) b.classList.add('fx-panel-wrap');
          }}
          apply();
          let i=0; const t=setInterval(()=>{{ apply(); if(++i>=10) clearInterval(t); }},150);
          const obs=new MutationObserver(apply);
          obs.observe(window.parent.document.body,{{childList:true,subtree:true}});
          setTimeout(()=>obs.disconnect(),3000);
        }})();
        </script>
        """,
        height=0,
    )


# ============================================================
# Gráfico barras horizontales
# ============================================================
def _fig_barras(nombres, valores, sufijo, titulo, bold_label=None):
    """
    nombres: list[str], valores: list[float]
    bold_label: str — ese label aparece en negrita y con color acento
    Ordenado de menor a mayor (el mayor queda arriba).
    """
    pares = [(n, v) for n, v in zip(nombres, valores)
             if v is not None and not (isinstance(v, float) and np.isnan(v))]
    pares = sorted(pares, key=lambda x: x[1])

    names = [p[0] for p in pares]
    vals  = [p[1] for p in pares]
    n     = len(vals)
    if n == 0:
        return go.Figure()

    maxv     = max(abs(v) for v in vals) or 1.0
    azul_osc = (27, 45, 107)
    azul_cla = (173, 198, 230)
    rojo     = "rgb(192,57,43)"

    colores   = []
    y_labels  = []
    for i, nm in enumerate(names):
        t = i / max(n - 1, 1)
        r = int(azul_cla[0] + t * (azul_osc[0] - azul_cla[0]))
        g = int(azul_cla[1] + t * (azul_osc[1] - azul_cla[1]))
        b = int(azul_cla[2] + t * (azul_osc[2] - azul_cla[2]))

        if bold_label and nm == bold_label:
            colores.append(rojo)
            y_labels.append(f"<b>{nm}</b>")
        else:
            colores.append(f"rgb({r},{g},{b})")
            y_labels.append(nm)

    fig = go.Figure(go.Bar(
        x=vals, y=y_labels, orientation="h",
        marker_color=colores,
        text=[f"{v:.1f}{sufijo}".replace(".", ",") for v in vals],
        textposition="outside", textfont=dict(size=11),
        cliponaxis=False,
        customdata=names,
        hovertemplate=f"<b>%{{customdata}}</b><br>%{{x:.1f}}{sufijo}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=13), x=0.01),
        margin=dict(t=40, b=20, l=280, r=90),
        xaxis=dict(range=[0, maxv * 1.20], showgrid=False,
                   showticklabels=False, showline=False, zeroline=False),
        yaxis=dict(tickfont=dict(size=10), automargin=True),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(360, n * 44 + 80),
        showlegend=False, bargap=0.28, dragmode=False,
    )
    return fig


# ============================================================
# Bloque de selectores + gráfico (reutilizable)
# ============================================================
def _render_bloque(
    df,            # DataFrame completo (ya con LABEL_IND reclasificado)
    df_g1,         # DataFrame agrupado por sector (1 dígito)
    key_prefix,    # str — para keys únicos de widgets
    sector_default,# str — sector seleccionado por defecto
    allow_total,   # bool — si True incluye "Total sectores" en el selector
):
    """
    Renderiza:
    - Fila con 2 selectores iguales: Sector | Medida
    - Gráfico correspondiente
    """

    # ── Opciones de sector ──────────────────
    sectores_grafico = sorted(df_g1[COL_SECTOR].tolist())
    if allow_total:
        opciones_sector = ["Total sectores"] + sectores_grafico
    else:
        opciones_sector = sectores_grafico

    default_idx = (
        opciones_sector.index(sector_default)
        if sector_default in opciones_sector
        else 0
    )

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("<div class='fx-panel-title'>Seleccioná el sector</div>", unsafe_allow_html=True)
        sector_sel = st.selectbox(
            "", opciones_sector, index=default_idx,
            key=f"{key_prefix}_sector", label_visibility="collapsed",
        )

    with c2:
        st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
        medida_sel = st.selectbox(
            "", ["Tasa de irregularidad", "Saldo irregular (en millones de pesos)"],
            key=f"{key_prefix}_medida", label_visibility="collapsed",
        )

    st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

    # ── Preparar datos para el gráfico ──────
    usar_millones = medida_sel == "Saldo irregular (en millones de pesos)"
    col_val = "_irreg_mm" if usar_millones else COL_MORA
    sufijo  = "M" if usar_millones else "%"

    if sector_sel == "Total sectores" or sector_sel not in df[COL_SECTOR].unique():
        # Vista agregada: un punto por sector (1 dígito)
        df_plot = df_g1.copy()
        if usar_millones:
            df_plot["_irreg_mm"] = df_plot[COL_IRREG] / 1_000
        nombres = df_plot[COL_SECTOR].tolist()
        valores = df_plot[col_val].tolist()
        bold    = LABEL_IND
        titulo  = f"{'Saldo irregular (millones $)' if usar_millones else 'Tasa de irregularidad (%)'} — todos los sectores"

    elif sector_sel == LABEL_IND:
        # Industria: subsectores son los de Sector_1_dígito original
        # (los que tenían id 101–332, ahora todos dicen LABEL_IND en COL_SECTOR
        #  pero su Sector_1_dígito *original* está en COL_SECTOR también...
        #  necesitamos el sector original → usamos el campo antes de reclasificar)
        # Recargar para obtener sector original de industria
        df_ind_raw = _get_subsectores_industria(df)
        if usar_millones:
            df_ind_raw["_irreg_mm"] = df_ind_raw[COL_IRREG] / 1_000
        # Total industria primero
        tot_saldo = df_ind_raw[COL_SALDO].sum()
        tot_irreg = df_ind_raw[COL_IRREG].sum()
        tot_mora  = (tot_irreg / tot_saldo * 100) if tot_saldo > 0 else float("nan")
        tot_val   = tot_irreg / 1_000 if usar_millones else tot_mora

        nombres = [f"Total {LABEL_IND}"] + df_ind_raw[COL_SECTOR].tolist()
        valores = [tot_val] + df_ind_raw[col_val].tolist()
        bold    = f"Total {LABEL_IND}"
        titulo  = f"{'Saldo irregular (millones $)' if usar_millones else 'Tasa de irregularidad (%)'} — {sector_sel}"

    else:
        # Cualquier otro sector: subsectores por Nombre (col C)
        df_sub = df[df[COL_SECTOR] == sector_sel].copy()
        df_sub_g = _agrupar(df_sub, COL_NOMBRE)
        if usar_millones:
            df_sub_g["_irreg_mm"] = df_sub_g[COL_IRREG] / 1_000
        # Total del sector
        tot_saldo = df_sub[COL_SALDO].sum()
        tot_irreg = df_sub[COL_IRREG].sum()
        tot_mora  = (tot_irreg / tot_saldo * 100) if tot_saldo > 0 else float("nan")
        tot_val   = tot_irreg / 1_000 if usar_millones else tot_mora

        nombres = [f"Total {sector_sel}"] + df_sub_g[COL_NOMBRE].tolist()
        valores = [tot_val] + df_sub_g[col_val].tolist()
        bold    = f"Total {sector_sel}"
        titulo  = f"{'Saldo irregular (millones $)' if usar_millones else 'Tasa de irregularidad (%)'} — {sector_sel}"

    with st.container(border=True):
        st.plotly_chart(
            _fig_barras(nombres, valores, sufijo, titulo, bold_label=bold),
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"{key_prefix}_chart",
        )

    st.caption("Fuente: BCRA — Central de deudores del sistema financiero")


def _get_subsectores_industria(df):
    """
    Devuelve df agrupado por Sector_1_dígito ORIGINAL de las filas de industria.
    Como ya reclasificamos COL_SECTOR, necesitamos identificarlas por id 101-332.
    Agrupamos por el Sector_1_dígito *que tenían antes* — pero como ya lo pisamos,
    usamos el campo que SÍ preserva la categoría original: recargamos el Excel.
    """
    # Recargamos sin reclasificar para obtener el sector original
    df_raw = pd.read_excel(MORA_PATH, sheet_name="Monitor", engine="openpyxl")
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    df_raw[COL_ID] = pd.to_numeric(df_raw[COL_ID], errors="coerce")
    df_raw = df_raw[(df_raw[COL_ID] >= ID_IND_MIN) & (df_raw[COL_ID] <= ID_IND_MAX)].copy()
    for c in [COL_SALDO, COL_IRREG]:
        df_raw[c] = pd.to_numeric(df_raw[c], errors="coerce")
    df_raw[COL_SECTOR] = df_raw[COL_SECTOR].astype(str).str.strip()
    # Agrupar por sector 1 dígito original
    return _agrupar(df_raw, COL_SECTOR)


# ============================================================
# RENDER PRINCIPAL
# ============================================================
def render_morosidad(go_to):

    st.markdown(CSS_PANEL, unsafe_allow_html=True)

    if st.button("← Volver"):
        go_to("home")

    try:
        df = load_mora()
    except Exception as e:
        st.error(f"⚠️ No se pudo cargar `{MORA_PATH}`\n\n`{e}`")
        return

    # Agrupación por sector 1 dígito (ya con LABEL_IND)
    df_g1 = _agrupar(df, COL_SECTOR)

    # Mora global
    total_saldo = df_g1[COL_SALDO].sum()
    total_irreg = df_g1[COL_IRREG].sum()
    mora_global = (total_irreg / total_saldo * 100) if total_saldo > 0 else float("nan")

    # ── HEADER ────────────────────────────────
    st.markdown(
        f"""
        <div style="
          background: linear-gradient(180deg,#f7fbff 0%,#eef6ff 100%);
          border:1px solid #dfeaf6; border-radius:18px; padding:14px 20px;
          box-shadow:0 8px 20px rgba(15,55,100,0.12); margin-bottom:16px;
          display:flex; align-items:center; gap:20px;
        ">
          <div style="font-size:32px;">⚠️</div>
          <div>
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
              letter-spacing:0.08em;color:#6b7a99;margin-bottom:6px;">
              Morosidad del sistema financiero · BCRA
            </div>
            <div style="font-size:36px;font-weight:950;color:#14324f;
              letter-spacing:-0.03em;line-height:1;">
              {fmt_pct(mora_global)}
            </div>
            <div style="font-size:12px;color:#8a95a8;margin-top:3px;">
              tasa de irregularidad global · saldo irregular / saldo total
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── TABS ──────────────────────────────────
    tab_sectores, tab_lupa = st.tabs(["📊 Morosidad por sectores", "🔍 Lupa en Industria"])

    # ══════════════════════════════════════════
    # TAB 1 — MOROSIDAD POR SECTORES
    # ══════════════════════════════════════════
    with tab_sectores:
        with st.container():
            _inject_panel("mora_sectores_marker")
            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)
            _render_bloque(
                df, df_g1,
                key_prefix="tab1",
                sector_default="Total sectores",
                allow_total=True,
            )

    # ══════════════════════════════════════════
    # TAB 2 — LUPA EN INDUSTRIA
    # ══════════════════════════════════════════
    with tab_lupa:
        with st.container():
            _inject_panel("mora_lupa_marker")
            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)
            _render_bloque(
                df, df_g1,
                key_prefix="tab2",
                sector_default=LABEL_IND,
                allow_total=False,
            )


# ============================================================
# Standalone
# ============================================================
if __name__ == "__main__":
    st.set_page_config(page_title="Morosidad – CEU UIA", layout="wide",
                       initial_sidebar_state="collapsed")
    render_morosidad(go_to=None)
