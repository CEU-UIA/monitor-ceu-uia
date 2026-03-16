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

ID_IND_MIN = 101
ID_IND_MAX = 332
LABEL_IND  = "Industria manufacturera"


# ============================================================
# Loader — devuelve DOS dataframes
# ============================================================
@st.cache_data(show_spinner=False)
def load_mora():
    df = pd.read_excel(MORA_PATH, sheet_name="Monitor", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    df[COL_ID] = pd.to_numeric(df[COL_ID], errors="coerce")

    # Excluir fila id=0
    df = df[df[COL_ID].fillna(-1) != 0].copy()

    # Excluir Nombre NaN
    if COL_NOMBRE in df.columns:
        df = df[df[COL_NOMBRE].notna()].copy()
        df = df[df[COL_NOMBRE].astype(str).str.strip().str.lower() != "nan"].copy()

    # Normalizar tasa_mora
    def _parse(x):
        try:
            v = float(str(x).replace("%", "").replace(",", ".").strip())
            return v if v > 1 else v * 100
        except:
            return float("nan")
    df[COL_MORA] = df[COL_MORA].apply(_parse)

    for c in [COL_SALDO, COL_IRREG]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df[COL_SECTOR] = df[COL_SECTOR].astype(str).str.strip()
    df = df[~df[COL_SECTOR].str.lower().isin(["nan", "none", ""])].copy()

    # ── df_ext: filas NO industriales (id fuera de 101-332)
    df_ext = df[(df[COL_ID] < ID_IND_MIN) | (df[COL_ID] > ID_IND_MAX)].copy()

    # ── df_ind: filas industriales (id 101-332)
    #    COL_SECTOR aquí tiene el subsector industrial (Alimentos y bebidas, Textil, etc.)
    df_ind = df[(df[COL_ID] >= ID_IND_MIN) & (df[COL_ID] <= ID_IND_MAX)].copy()

    return df_ext, df_ind


# ============================================================
# Helper agrupación
# ============================================================
def _agrupar(df_in, col_grupo):
    g = (
        df_in.groupby(col_grupo, as_index=False)
        .agg(**{COL_SALDO: (COL_SALDO, "sum"), COL_IRREG: (COL_IRREG, "sum")})
    )
    g[COL_MORA] = g.apply(
        lambda r: (r[COL_IRREG] / r[COL_SALDO] * 100) if r[COL_SALDO] > 0 else float("nan"),
        axis=1,
    )
    return g

def _total_row(df_in, label):
    """Devuelve dict con saldo, irreg y mora para usar como fila 'Total'."""
    s = df_in[COL_SALDO].sum()
    i = df_in[COL_IRREG].sum()
    m = (i / s * 100) if s > 0 else float("nan")
    return {COL_SECTOR: label, COL_SALDO: s, COL_IRREG: i, COL_MORA: m}


# ============================================================
# Formato
# ============================================================
def fmt_pct(x, dec=1):
    try:
        return f"{float(x):.{dec}f}".replace(".", ",") + "%"
    except:
        return "—"


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

def _inject_panel(marker_id):
    st.markdown(f"<span id='{marker_id}'></span>", unsafe_allow_html=True)
    components.html(
        f"""<script>
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
        </script>""",
        height=0,
    )


# ============================================================
# Gráfico barras horizontales
# ============================================================
def _fig_barras(nombres, valores, sufijo, titulo, bold_label=None):
    pares = [(n, float(v)) for n, v in zip(nombres, valores)
             if v is not None and not np.isnan(float(v))]
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

    colores  = []
    y_labels = []
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
        margin=dict(t=40, b=20, l=290, r=90),
        xaxis=dict(range=[0, maxv * 1.20], showgrid=False,
                   showticklabels=False, showline=False, zeroline=False),
        yaxis=dict(tickfont=dict(size=10), automargin=True),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(360, n * 44 + 80),
        showlegend=False, bargap=0.28, dragmode=False,
    )
    return fig


# ============================================================
# RENDER PRINCIPAL
# ============================================================
def render_morosidad(go_to):

    st.markdown(CSS_PANEL, unsafe_allow_html=True)

    if st.button("← Volver"):
        go_to("home")

    try:
        df_ext, df_ind = load_mora()
    except Exception as e:
        st.error(f"⚠️ No se pudo cargar `{MORA_PATH}`\n\n`{e}`")
        return

    # ── Agregados globales ────────────────────
    df_todo = pd.concat([df_ext, df_ind], ignore_index=True)
    total_saldo = df_todo[COL_SALDO].sum()
    total_irreg = df_todo[COL_IRREG].sum()
    mora_global = (total_irreg / total_saldo * 100) if total_saldo > 0 else float("nan")

    # ── Sectores externos agrupados ───────────
    df_g_ext = _agrupar(df_ext, COL_SECTOR)

    # ── Industria total (una fila) ─────────────
    ind_total = _total_row(df_ind, LABEL_IND)
    df_g_ind_fila = pd.DataFrame([ind_total])

    # ── df para el gráfico de Tab 1 "Total sectores" ──
    # externos + una fila Industria manufacturera
    df_g1 = pd.concat([df_g_ext, df_g_ind_fila], ignore_index=True)

    # ── Subsectores de industria (col A agrupado) ──
    df_g_ind_sub = _agrupar(df_ind, COL_SECTOR)  # Alimentos, Textil, etc.

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
            <div style="font-size:36px;font-weight:950;color:#14324f;letter-spacing:-0.03em;line-height:1;">
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
            _inject_panel("mora_t1_marker")
            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

            opciones_t1 = ["Total sectores"] + sorted(df_g1[COL_SECTOR].tolist())

            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("<div class='fx-panel-title'>Seleccioná el sector</div>", unsafe_allow_html=True)
                sector_t1 = st.selectbox("", opciones_t1, index=0,
                                         key="t1_sector", label_visibility="collapsed")
            with c2:
                st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
                medida_t1 = st.selectbox(
                    "", ["Tasa de irregularidad", "Saldo irregular (en millones de pesos)"],
                    key="t1_medida", label_visibility="collapsed",
                )

            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

            usar_mm_t1 = medida_t1 == "Saldo irregular (en millones de pesos)"
            suf_t1     = "M" if usar_mm_t1 else "%"

            if sector_t1 == "Total sectores":
                # Un punto por sector (externos + industria como uno solo)
                nombres = df_g1[COL_SECTOR].tolist()
                if usar_mm_t1:
                    valores = (df_g1[COL_IRREG] / 1_000).tolist()
                else:
                    valores = df_g1[COL_MORA].tolist()
                bold   = LABEL_IND
                titulo = f"{'Saldo irregular (millones $)' if usar_mm_t1 else 'Tasa de irregularidad (%)'} — todos los sectores"

            elif sector_t1 == LABEL_IND:
                # Subsectores industriales (col A): Alimentos, Textil, etc. + total
                tot_val = (ind_total[COL_IRREG] / 1_000) if usar_mm_t1 else ind_total[COL_MORA]
                nombres = [f"Total {LABEL_IND}"] + df_g_ind_sub[COL_SECTOR].tolist()
                if usar_mm_t1:
                    valores = [tot_val] + (df_g_ind_sub[COL_IRREG] / 1_000).tolist()
                else:
                    valores = [tot_val] + df_g_ind_sub[COL_MORA].tolist()
                bold   = f"Total {LABEL_IND}"
                titulo = f"{'Saldo irregular (millones $)' if usar_mm_t1 else 'Tasa de irregularidad (%)'} — {sector_t1}"

            else:
                # Subsectores por col C (Nombre)
                df_sub = df_ext[df_ext[COL_SECTOR] == sector_t1].copy()
                df_sub_g = _agrupar(df_sub, COL_NOMBRE)
                tot      = _total_row(df_sub, f"Total {sector_t1}")
                tot_val  = (tot[COL_IRREG] / 1_000) if usar_mm_t1 else tot[COL_MORA]
                nombres  = [f"Total {sector_t1}"] + df_sub_g[COL_NOMBRE].tolist()
                if usar_mm_t1:
                    valores = [tot_val] + (df_sub_g[COL_IRREG] / 1_000).tolist()
                else:
                    valores = [tot_val] + df_sub_g[COL_MORA].tolist()
                bold   = f"Total {sector_t1}"
                titulo = f"{'Saldo irregular (millones $)' if usar_mm_t1 else 'Tasa de irregularidad (%)'} — {sector_t1}"

            with st.container(border=True):
                st.plotly_chart(
                    _fig_barras(nombres, valores, suf_t1, titulo, bold_label=bold),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="t1_chart",
                )

            st.caption("Fuente: BCRA — Central de deudores del sistema financiero")

    # ══════════════════════════════════════════
    # TAB 2 — LUPA EN INDUSTRIA
    # ══════════════════════════════════════════
    with tab_lupa:
        with st.container():
            _inject_panel("mora_t2_marker")
            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

            # Selector: subsectores industriales (Alimentos, Textil, etc.)
            subsectores_ind = sorted(df_g_ind_sub[COL_SECTOR].tolist())

            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("<div class='fx-panel-title'>Seleccioná el sector industrial</div>", unsafe_allow_html=True)
                subsector_t2 = st.selectbox(
                    "", subsectores_ind, index=0,
                    key="t2_subsector", label_visibility="collapsed",
                )
            with c2:
                st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
                medida_t2 = st.selectbox(
                    "", ["Tasa de irregularidad", "Saldo irregular (en millones de pesos)"],
                    key="t2_medida", label_visibility="collapsed",
                )

            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

            usar_mm_t2 = medida_t2 == "Saldo irregular (en millones de pesos)"
            suf_t2     = "M" if usar_mm_t2 else "%"

            # Filas del subsector seleccionado
            df_sub2  = df_ind[df_ind[COL_SECTOR] == subsector_t2].copy()
            df_sub2g = _agrupar(df_sub2, COL_NOMBRE)
            tot2     = _total_row(df_sub2, f"Total {subsector_t2}")
            tot2_val = (tot2[COL_IRREG] / 1_000) if usar_mm_t2 else tot2[COL_MORA]

            nombres2 = [f"Total {subsector_t2}"] + df_sub2g[COL_NOMBRE].tolist()
            if usar_mm_t2:
                valores2 = [tot2_val] + (df_sub2g[COL_IRREG] / 1_000).tolist()
            else:
                valores2 = [tot2_val] + df_sub2g[COL_MORA].tolist()

            titulo2 = f"{'Saldo irregular (millones $)' if usar_mm_t2 else 'Tasa de irregularidad (%)'} — {subsector_t2}"

            with st.container(border=True):
                st.plotly_chart(
                    _fig_barras(nombres2, valores2, suf_t2, titulo2,
                                bold_label=f"Total {subsector_t2}"),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="t2_chart",
                )

            st.caption("Fuente: BCRA — Central de deudores del sistema financiero")


# ============================================================
# Standalone
# ============================================================
if __name__ == "__main__":
    st.set_page_config(page_title="Morosidad – CEU UIA", layout="wide",
                       initial_sidebar_state="collapsed")
    render_morosidad(go_to=None)
