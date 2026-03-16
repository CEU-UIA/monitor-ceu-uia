import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import textwrap
import streamlit.components.v1 as components

# ============================================================
# Config
# ============================================================
MORA_PATH = "assets/mora_por_actividad.xlsx"

COL_SECTOR = "Sector_1_dígito"
COL_ID     = "id"
COL_NOMBRE = "Nombre"
COL_SALDO  = "saldo_total (miles de $)"
COL_IRREG  = "saldo_irregular (miles de $)"
COL_MORA   = "tasa_mora"

# ============================================================
# Loader
# ============================================================
@st.cache_data(show_spinner=False)
def load_mora():
    df = pd.read_excel(MORA_PATH, sheet_name="Monitor", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    # Excluir fila id=0 (agregado "Otros")
    if COL_ID in df.columns:
        df = df[pd.to_numeric(df[COL_ID], errors="coerce").fillna(-1) != 0].copy()

    # Excluir Nombre NaN
    if COL_NOMBRE in df.columns:
        df = df[df[COL_NOMBRE].notna()].copy()
        df = df[df[COL_NOMBRE].astype(str).str.strip().str.lower() != "nan"].copy()

    # Normalizar tasa_mora a float en %
    if COL_MORA in df.columns:
        def _parse(x):
            try:
                v = float(str(x).replace("%", "").replace(",", ".").strip())
                return v if v > 1 else v * 100
            except:
                return float("nan")
        df[COL_MORA] = df[COL_MORA].apply(_parse)

    # Numéricos
    for c in [COL_SALDO, COL_IRREG]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Limpiar sector
    if COL_SECTOR in df.columns:
        df[COL_SECTOR] = df[COL_SECTOR].astype(str).str.strip()
        df = df[~df[COL_SECTOR].str.lower().isin(["nan", "none", ""])].copy()

    return df


# ============================================================
# Helpers de formato
# ============================================================
def fmt_pct(x, dec=1):
    try:
        return f"{float(x):.{dec}f}".replace(".", ",") + "%"
    except:
        return "—"

def fmt_bn(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    v = float(x)
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:,.1f}B".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${v/1_000:,.0f}M".replace(",", ".")

def _arrow(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "", ""
    return ("▲", "fx-up") if v >= 0 else ("▼", "fx-down")


# ============================================================
# CSS
# ============================================================
CSS = textwrap.dedent("""
<style>
  .fx-wrap{
    background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 100%);
    border: 1px solid #dfeaf6;
    border-radius: 22px;
    padding: 12px;
    box-shadow:
      0 10px 24px rgba(15,55,100,0.16),
      inset 0 0 0 1px rgba(255,255,255,0.55);
  }
  .fx-title-row{
    display:flex; align-items:center; gap:12px;
    margin-bottom:8px; padding-left:4px;
  }
  .fx-icon-badge{
    width:64px; height:52px; border-radius:14px;
    background: linear-gradient(180deg,#e7eef6 0%,#dfe7f1 100%);
    border:1px solid rgba(15,23,42,0.10);
    display:flex; align-items:center; justify-content:center;
    box-shadow:0 8px 14px rgba(15,55,100,0.12);
    font-size:32px; flex:0 0 auto;
  }
  .fx-title{
    font-size:23px; font-weight:900; letter-spacing:-0.01em;
    color:#14324f; margin:0; line-height:1.0;
  }
  .fx-card{
    background:rgba(255,255,255,0.94);
    border:1px solid rgba(15,23,42,0.10);
    border-radius:18px; padding:14px 14px 12px 14px;
    box-shadow:0 10px 18px rgba(15,55,100,0.10);
  }
  .fx-kpi-grid{
    display:grid; grid-template-columns:repeat(3,1fr); gap:12px;
  }
  .fx-kpi{
    background:rgba(255,255,255,0.94);
    border:1px solid rgba(15,23,42,0.10);
    border-radius:18px; border-top:4px solid #1B2D6B;
    padding:14px 14px 12px 14px;
    box-shadow:0 10px 18px rgba(15,55,100,0.10);
  }
  .fx-kpi-label{
    font-size:10px; font-weight:700; text-transform:uppercase;
    letter-spacing:0.08em; color:#6b7a99; margin-bottom:6px;
  }
  .fx-kpi-value{
    font-size:28px; font-weight:950; letter-spacing:-0.02em;
    color:#14324f; line-height:1.0; margin-bottom:4px;
  }
  .fx-kpi-sub{ font-size:11px; color:#8a95a8; font-weight:500; }
  .fx-kpi-accent{ color:#c0392b; }
  .fx-row{
    display:grid; grid-template-columns:auto 1fr auto;
    align-items:center; column-gap:14px;
  }
  .fx-value{
    font-size:46px; font-weight:950; letter-spacing:-0.02em;
    color:#14324f; line-height:0.95;
  }
  .fx-meta{
    font-size:13px; color:#2b4660; font-weight:700;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  }
  .fx-meta .sep{ opacity:0.40; padding:0 6px; }
  .fx-pills{
    display:flex; gap:10px; justify-content:flex-end;
    align-items:center; white-space:nowrap;
  }
  .fx-pill{
    display:inline-flex; align-items:center; gap:8px;
    padding:7px 10px; border-radius:12px;
    border:1px solid rgba(15,23,42,0.10);
    font-size:13px; font-weight:700;
    box-shadow:0 6px 10px rgba(15,55,100,0.08);
  }
  .fx-pill .lab{ color:#2b4660; font-weight:900; }
  .fx-pill.red{
    background:linear-gradient(180deg,rgba(220,38,38,0.08) 0%,rgba(220,38,38,0.05) 100%);
  }
  .fx-pill.amber{
    background:linear-gradient(180deg,rgba(217,119,6,0.10) 0%,rgba(217,119,6,0.06) 100%);
  }
  .fx-up{ color:#168a3a; font-weight:900; }
  .fx-down{ color:#cc2e2e; font-weight:900; }
  .fx-arrow{ width:14px; text-align:center; font-weight:900; }
  .fx-panel-title{
    font-size:12px; font-weight:900;
    color:rgba(20,50,79,0.78); margin:0 0 6px 2px; letter-spacing:0.01em;
  }
  .fx-panel-gap{ height:16px; }
  .fx-panel-wrap{
    background:rgba(230,243,255,0.55);
    border:1px solid rgba(15,55,100,0.10);
    border-radius:22px; padding:16px 16px 26px 16px;
    box-shadow:0 10px 18px rgba(15,55,100,0.06);
    margin-top:10px;
  }
  .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"]{
    background:#0b2a55 !important;
    border:1px solid rgba(255,255,255,0.14) !important;
    box-shadow:0 10px 18px rgba(15,55,100,0.10) !important;
  }
  .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"] *{
    color:#8fc2ff !important; fill:#8fc2ff !important; font-weight:800 !important;
  }
</style>
""")


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
# Gráficos
# ============================================================
def _fig_barras_h(title, labels, values, suffix="%", highlight=None):
    pares = []
    for l, v in zip(labels, values):
        try:
            vf = float(v)
            if not np.isnan(vf):
                pares.append((l, vf))
        except:
            pass
    pares = sorted(pares, key=lambda x: x[1])
    names = [p[0] for p in pares]
    vals  = [p[1] for p in pares]
    n     = len(vals)
    if n == 0:
        return go.Figure()
    maxv = max(abs(v) for v in vals) or 1.0

    azul_osc = (27, 45, 107)
    azul_cla = (173, 198, 230)
    rojo     = (192, 57, 43)

    colores = []
    for i, nm in enumerate(names):
        if highlight and nm == highlight:
            colores.append(f"rgb{rojo}")
        else:
            t = i / max(n - 1, 1)
            r = int(azul_cla[0] + t * (azul_osc[0] - azul_cla[0]))
            g = int(azul_cla[1] + t * (azul_osc[1] - azul_cla[1]))
            b = int(azul_cla[2] + t * (azul_osc[2] - azul_cla[2]))
            colores.append(f"rgb({r},{g},{b})")

    fig = go.Figure(go.Bar(
        x=vals, y=names,
        orientation="h",
        marker_color=colores,
        text=[f"{v:.1f}{suffix}".replace(".", ",") for v in vals],
        textposition="outside",
        textfont=dict(size=11),
        cliponaxis=False,
        hovertemplate=f"<b>%{{y}}</b><br>%{{x:.1f}}{suffix}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13), x=0.01),
        margin=dict(t=40, b=20, l=220, r=70),
        xaxis=dict(range=[0, maxv * 1.18], showgrid=False,
                   showticklabels=False, showline=False, zeroline=False),
        yaxis=dict(tickfont=dict(size=10), automargin=True),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(340, n * 38 + 80),
        showlegend=False, bargap=0.28, dragmode=False,
    )
    return fig


def _fig_scatter(df_in, x_col, y_col, label_col, title, highlight=None):
    colors = []
    sizes  = []
    for _, row in df_in.iterrows():
        if highlight and row[label_col] == highlight:
            colors.append("rgba(192,57,43,0.85)")
            sizes.append(16)
        else:
            colors.append("rgba(27,45,107,0.72)")
            sizes.append(10)

    fig = go.Figure(go.Scatter(
        x=df_in[x_col], y=df_in[y_col],
        mode="markers+text",
        text=df_in[label_col],
        textposition="top center",
        textfont=dict(size=8),
        marker=dict(color=colors, size=sizes, line=dict(color="white", width=1)),
        hovertemplate="<b>%{text}</b><br>Saldo: $%{x:,.0f}k<br>Mora: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13), x=0.01),
        height=380,
        margin=dict(t=40, b=50, l=60, r=20),
        xaxis=dict(title="Saldo total (miles de $)", gridcolor="#F0F2F6", tickfont=dict(size=9)),
        yaxis=dict(title="Tasa de mora (%)", gridcolor="#F0F2F6",
                   tickfont=dict(size=9), ticksuffix="%"),
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False, dragmode=False,
    )
    return fig


# ============================================================
# RENDER PRINCIPAL
# ============================================================
def render_morosidad(go_to):

    st.markdown(CSS, unsafe_allow_html=True)

    if st.button("← Volver"):
        go_to("home")

    # Cargar datos
    try:
        df = load_mora()
    except Exception as e:
        st.error(f"⚠️ No se pudo cargar `{MORA_PATH}`\n\n`{e}`")
        return

    # KPIs globales
    total_saldo = df[COL_SALDO].sum() if COL_SALDO in df.columns else None
    total_irreg = df[COL_IRREG].sum() if COL_IRREG in df.columns else None
    mora_global = (total_irreg / total_saldo * 100) if (total_saldo and total_irreg and total_saldo > 0) else None

    # Agrupar por sector 1 dígito
    df_g1 = (
        df.groupby(COL_SECTOR, as_index=False)
        .agg(**{COL_SALDO: (COL_SALDO, "sum"), COL_IRREG: (COL_IRREG, "sum")})
    )
    df_g1[COL_MORA] = df_g1.apply(
        lambda r: (r[COL_IRREG] / r[COL_SALDO] * 100) if r[COL_SALDO] > 0 else float("nan"),
        axis=1,
    )

    # Sector con mayor mora
    peor = df_g1.dropna(subset=[COL_MORA]).sort_values(COL_MORA, ascending=False)
    peor_nombre = peor.iloc[0][COL_SECTOR] if not peor.empty else "—"
    peor_mora   = peor.iloc[0][COL_MORA]   if not peor.empty else None

    a_mora, cls_mora = _arrow(mora_global)

    # ── HEADER ────────────────────────────────
    st.markdown(f"""
    <div class="fx-wrap">
      <div class="fx-title-row">
        <div class="fx-icon-badge">⚠️</div>
        <div class="fx-title">Morosidad del sistema financiero</div>
      </div>
      <div class="fx-card">
        <div class="fx-row">
          <div class="fx-value">{fmt_pct(mora_global)}</div>
          <div class="fx-meta">
            Tasa de mora global
            <span class="sep">|</span>saldo irregular / saldo total
            <span class="sep">|</span>BCRA
          </div>
          <div class="fx-pills">
            <div class="fx-pill red">
              <span class="fx-arrow {cls_mora}">{a_mora}</span>
              <span class="{cls_mora}">{fmt_pct(mora_global)}</span>
              <span class="lab">mora global</span>
            </div>
            <div class="fx-pill amber">
              <span style="font-size:11px;">🔺</span>
              <span class="fx-down">{fmt_pct(peor_mora)}</span>
              <span class="lab">{peor_nombre[:16]}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

    # ── KPI CARDS ─────────────────────────────
    st.markdown(f"""
    <div class="fx-kpi-grid">
      <div class="fx-kpi">
        <div class="fx-kpi-label">Saldo total sistema</div>
        <div class="fx-kpi-value">{fmt_bn(total_saldo)}</div>
        <div class="fx-kpi-sub">miles de $</div>
      </div>
      <div class="fx-kpi">
        <div class="fx-kpi-label">Saldo irregular</div>
        <div class="fx-kpi-value fx-kpi-accent">{fmt_bn(total_irreg)}</div>
        <div class="fx-kpi-sub">miles de $</div>
      </div>
      <div class="fx-kpi">
        <div class="fx-kpi-label">Tasa de mora global</div>
        <div class="fx-kpi-value fx-kpi-accent">{fmt_pct(mora_global)}</div>
        <div class="fx-kpi-sub">irreg / total · todos los sectores</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────
    tab_total, tab_lupa = st.tabs(["📊 Total por sector", "🔍 Lupa en actividad"])

    # ══════════════════════════════════════════
    # TAB 1 — TOTAL
    # ══════════════════════════════════════════
    with tab_total:
        with st.container():
            _inject_panel("mora_total_marker")

            st.markdown("""
            <div class="fx-wrap">
              <div class="fx-title-row">
                <div class="fx-icon-badge">📊</div>
                <div class="fx-title">Vista general — sectores (1 dígito)</div>
              </div>
            </div>""", unsafe_allow_html=True)
            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("<div class='fx-panel-title'>Variable</div>", unsafe_allow_html=True)
                var_t = st.selectbox(
                    "", ["Tasa de mora (%)", "Saldo total", "Saldo irregular"],
                    key="mora_var_total", label_visibility="collapsed",
                )
            with c2:
                st.markdown("<div class='fx-panel-title'>Sector destacado</div>", unsafe_allow_html=True)
                sectores_lista = sorted(df_g1[COL_SECTOR].tolist())
                highlight_t = st.selectbox(
                    "", ["(ninguno)"] + sectores_lista,
                    key="mora_highlight_total", label_visibility="collapsed",
                )
                highlight_t = None if highlight_t == "(ninguno)" else highlight_t

            if var_t == "Tasa de mora (%)":
                labs, vals, suf = df_g1[COL_SECTOR].tolist(), df_g1[COL_MORA].tolist(), "%"
            elif var_t == "Saldo total":
                labs = df_g1[COL_SECTOR].tolist()
                vals = (df_g1[COL_SALDO] / 1_000_000).tolist()
                suf  = "B"
            else:
                labs = df_g1[COL_SECTOR].tolist()
                vals = (df_g1[COL_IRREG] / 1_000_000).tolist()
                suf  = "B"

            with st.container(border=True):
                st.plotly_chart(
                    _fig_barras_h(f"{var_t} por sector", labs, vals,
                                  suffix=suf, highlight=highlight_t),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="mora_chart_total_barras",
                )

            with st.container(border=True):
                st.plotly_chart(
                    _fig_scatter(
                        df_g1.dropna(subset=[COL_MORA, COL_SALDO]),
                        COL_SALDO, COL_MORA, COL_SECTOR,
                        "Tamaño vs mora — sectores",
                        highlight=highlight_t,
                    ),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="mora_chart_total_scatter",
                )

            st.markdown(
                "<div style='color:rgba(20,50,79,0.70);font-size:12px;'>"
                "Fuente: BCRA — Central de deudores del sistema financiero"
                "</div>", unsafe_allow_html=True,
            )

    # ══════════════════════════════════════════
    # TAB 2 — LUPA EN ACTIVIDAD
    # ══════════════════════════════════════════
    with tab_lupa:
        with st.container():
            _inject_panel("mora_lupa_marker")

            st.markdown("""
            <div class="fx-wrap">
              <div class="fx-title-row">
                <div class="fx-icon-badge">🔍</div>
                <div class="fx-title">Zoom por sector — actividades (2 dígitos)</div>
              </div>
            </div>""", unsafe_allow_html=True)
            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3, gap="large")

            with c1:
                st.markdown("<div class='fx-panel-title'>Sector</div>", unsafe_allow_html=True)
                sectores_disp = sorted(df[COL_SECTOR].dropna().unique().tolist())
                sector_sel = st.selectbox(
                    "", sectores_disp, key="mora_sector_lupa",
                    label_visibility="collapsed",
                )

            df_zoom = df[df[COL_SECTOR] == sector_sel].copy() if sector_sel else pd.DataFrame()

            with c2:
                st.markdown("<div class='fx-panel-title'>Variable</div>", unsafe_allow_html=True)
                var_l = st.selectbox(
                    "", ["Tasa de mora (%)", "Saldo total", "Saldo irregular"],
                    key="mora_var_lupa", label_visibility="collapsed",
                )

            with c3:
                st.markdown("<div class='fx-panel-title'>Actividad destacada</div>", unsafe_allow_html=True)
                acts_disp = sorted(df_zoom[COL_NOMBRE].dropna().tolist()) if not df_zoom.empty else []
                highlight_l = st.selectbox(
                    "", ["(ninguna)"] + acts_disp,
                    key="mora_highlight_lupa", label_visibility="collapsed",
                )
                highlight_l = None if highlight_l == "(ninguna)" else highlight_l

            if not df_zoom.empty:
                s_saldo = df_zoom[COL_SALDO].sum()
                s_irreg = df_zoom[COL_IRREG].sum()
                s_mora  = (s_irreg / s_saldo * 100) if s_saldo > 0 else float("nan")
                n_acts  = len(df_zoom)

                st.markdown(f"""
                <div class="fx-kpi-grid">
                  <div class="fx-kpi">
                    <div class="fx-kpi-label">Saldo total · {sector_sel[:28]}</div>
                    <div class="fx-kpi-value">{fmt_bn(s_saldo)}</div>
                    <div class="fx-kpi-sub">miles de $</div>
                  </div>
                  <div class="fx-kpi">
                    <div class="fx-kpi-label">Saldo irregular</div>
                    <div class="fx-kpi-value fx-kpi-accent">{fmt_bn(s_irreg)}</div>
                    <div class="fx-kpi-sub">miles de $</div>
                  </div>
                  <div class="fx-kpi">
                    <div class="fx-kpi-label">Tasa de mora sector</div>
                    <div class="fx-kpi-value fx-kpi-accent">{fmt_pct(s_mora)}</div>
                    <div class="fx-kpi-sub">{n_acts} actividades</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

                # Recalcular mora a nivel actividad
                df_zoom[COL_MORA] = df_zoom.apply(
                    lambda r: (r[COL_IRREG] / r[COL_SALDO] * 100)
                              if r[COL_SALDO] > 0 else float("nan"),
                    axis=1,
                )

                if var_l == "Tasa de mora (%)":
                    labs_l = df_zoom[COL_NOMBRE].tolist()
                    vals_l = df_zoom[COL_MORA].tolist()
                    suf_l  = "%"
                elif var_l == "Saldo total":
                    labs_l = df_zoom[COL_NOMBRE].tolist()
                    vals_l = (df_zoom[COL_SALDO] / 1_000_000).tolist()
                    suf_l  = "B"
                else:
                    labs_l = df_zoom[COL_NOMBRE].tolist()
                    vals_l = (df_zoom[COL_IRREG] / 1_000_000).tolist()
                    suf_l  = "B"

                with st.container(border=True):
                    st.plotly_chart(
                        _fig_barras_h(
                            f"{var_l} — {sector_sel}",
                            labs_l, vals_l, suffix=suf_l, highlight=highlight_l,
                        ),
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key="mora_chart_lupa_barras",
                    )

                with st.container(border=True):
                    st.plotly_chart(
                        _fig_scatter(
                            df_zoom.dropna(subset=[COL_MORA, COL_SALDO]),
                            COL_SALDO, COL_MORA, COL_NOMBRE,
                            f"Tamaño vs mora — {sector_sel}",
                            highlight=highlight_l,
                        ),
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key="mora_chart_lupa_scatter",
                    )
            else:
                st.info("No hay datos para el sector seleccionado.")

            st.markdown(
                "<div style='color:rgba(20,50,79,0.70);font-size:12px;'>"
                "Fuente: BCRA — Central de deudores del sistema financiero"
                "</div>", unsafe_allow_html=True,
            )


# ============================================================
# Standalone
# ============================================================
if __name__ == "__main__":
    st.set_page_config(
        page_title="Morosidad – CEU UIA",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render_morosidad(go_to=None)
