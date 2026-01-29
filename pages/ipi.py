import textwrap
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.ipi_data import cargar_ipi_excel, procesar_serie_excel
from services.metrics import calc_var, fmt, obtener_nombre_mes

def fmt_es(x, dec=1):
    if pd.isna(x) or x is None:
        return "s/d"
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic"]


# ============================================================
# Helpers para bloques del Excel
# ============================================================
def _is_header_div(code_str: str) -> bool:
    s = str(code_str).strip()
    if not s or s.lower() == "nan":
        return False
    if s.isdigit() and len(s) == 2:
        return True
    if "-" in s:
        return True
    return False


def _build_div_blocks(codes: list[str]) -> tuple[list[int], dict[str, int]]:
    header_idxs = []
    code_to_idx = {}
    for i, c in enumerate(codes):
        if i < 3:
            continue
        if _is_header_div(c):
            header_idxs.append(i)
            code_to_idx[str(c).strip()] = i
    return header_idxs, code_to_idx


def _subcol_range_for_header(header_idx: int, header_idxs: list[int], total_cols: int) -> range:
    if header_idx not in header_idxs:
        return range(0, 0)
    pos = header_idxs.index(header_idx)
    next_h = header_idxs[pos + 1] if pos + 1 < len(header_idxs) else total_cols
    return range(header_idx + 1, next_h)


# ============================================================
# UI helpers
# ============================================================
def _inject_css():
    st.markdown(
        """
<style>
/* Cards */
.ipi-card{
  background:#ffffff;
  border:1px solid #e1e8ed;
  border-radius:14px;
  padding:14px 14px 12px 14px;
  box-shadow:0 4px 6px rgba(0,0,0,0.05);
}
.ipi-title{ font-weight:900; font-size:18px; color:#0f2a43; margin-bottom:8px; }
.ipi-row{ display:flex; justify-content:space-between; align-items:center; gap:12px; }
.ipi-label{ font-size:16px; font-weight:700; color:#526484; }
.ipi-big{ font-size:24px; font-weight:900; color:#0f2a43; }

/* Círculo (KPI) */
.ipi-badge{
  width:52px; height:52px; border-radius:999px;
  display:flex; align-items:center; justify-content:center;
  font-weight:900; font-size:18px;
  border:1px solid transparent;
}
.ipi-up{ background:rgba(22,163,74,.12); color:rgb(22,163,74); border-color:rgba(22,163,74,.25); }
.ipi-down{ background:rgba(220,38,38,.12); color:rgb(220,38,38); border-color:rgba(220,38,38,.25); }
.ipi-neutral{ background:rgba(100,116,139,.12); color:rgb(100,116,139); border-color:rgba(100,116,139,.22); }

/* Mini KPI en modal */
.ipi-mini-wrap{ display:flex; gap:12px; margin-bottom:6px; }
.ipi-mini{
  flex:1;
  border:1px solid #e6edf5;
  border-radius:12px;
  padding:10px 12px;
  background:#ffffff;
  text-align:center;
}
.ipi-mini-lbl{ font-size:16px; font-weight:800; color:#526484; margin-bottom:6px; }
.ipi-mini-val{ font-size:24px; font-weight:900; color:#0f2a43; }

/* Reduce padding de labels arriba de widgets */
.small-help{ color:#526484; font-size:12px; font-weight:700; margin-top:-6px; }

.ipi-mini-row{
  display:flex;
  justify-content:center;
}

.ipi-mini-val{
    font-size:22px;
    font-weight:700;
    color:#0f172a;
}

/* DOT */
.ipi-dot{
    width:52px;
    height:52px;
    border-radius:999px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:900;
    font-size:18px;
    border:1px solid transparent;
}

/* =========================
   CEU – KPI CARDS (shared)
   ========================= */

.emp-wrap{
  background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 100%);
  border: 1px solid #dfeaf6;
  border-radius: 22px;
  padding: 14px;
  box-shadow: 0 10px 24px rgba(15, 55, 100, 0.16),
              inset 0 0 0 1px rgba(255,255,255,0.55);
  margin-top: 10px;
}

.emp-title-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  margin-bottom: 10px;
  padding-left: 4px;
}

.emp-title-left{
  display:flex;
  align-items:center;
  gap:12px;
}

.emp-icon-badge{
  width: 64px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(180deg, #e7eef6 0%, #dfe7f1 100%);
  border: 1px solid rgba(15,23,42,0.10);
  display:flex;
  align-items:center;
  justify-content:center;
  box-shadow: 0 8px 14px rgba(15,55,100,0.12);
  font-size: 30px;
}

.emp-title{
  font-size: 23px;
  font-weight: 900;
  letter-spacing: -0.01em;
  color: #14324f;
  line-height: 1.0;
}

.emp-subtitle{
  font-size: 12px;
  font-weight: 800;
  color: rgba(20,50,79,0.78);
  margin-top: 2px;
}

.emp-card{
  background: rgba(255,255,255,0.94);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 18px;
  padding: 14px;
  box-shadow: 0 10px 18px rgba(15, 55, 100, 0.10);
}

.emp-kpi-grid{
  display:grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 26px;
}

.emp-kpi .emp-meta{
  font-size: 14px;
  font-weight: 800;
  color: #526484;
  margin-bottom: 6px;
}

.emp-value{
  font-size: 44px;
  font-weight: 900;
  color: #0f2a43;
  line-height: 1;
}

.emp-badge{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:6px 10px;
  border-radius:999px;
  font-size:12px;
  font-weight:800;
  margin-top:6px;
  border:1px solid transparent;
}

.emp-badge.red{
  background:rgba(220,38,38,.10);
  color:#b91c1c;
  border-color:rgba(220,38,38,.25);
}

.emp-badge.green{
  background:rgba(22,163,74,.12);
  color:#15803d;
  border-color:rgba(22,163,74,.25);
}

/* Responsive */
@media (max-width: 900px){
  .emp-kpi-grid{
    grid-template-columns: 1fr;
    gap: 14px;
  }
}
/* Link “Informe CEU” */
.emp-report a{
  display:inline-block;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid #e5e7eb;
  background:#ffffff;
  color:#0f172a;
  font-size:12px;
  font-weight:700;
  text-decoration:none;
  box-shadow:0 2px 4px rgba(0,0,0,0.06);
}
</style>
""",
        unsafe_allow_html=True,
    )


def _dot_class(x: float) -> str:
    if x is None or pd.isna(x) or abs(float(x)) < 1e-12:
        return "ipi-neutral"
    return "ipi-up" if float(x) > 0 else "ipi-down"


def _fmt_pct_es(x: float, dec: int = 1) -> str:
    if x is None or pd.isna(x):
        return "s/d"
    return f"{float(x):.{dec}f}%".replace(".", ",")


# ============================================================
# MAIN
# ============================================================
def render_ipi(go_to):
    _inject_css()

    if st.button("← Volver"):
        go_to("home")

    # -------------------------
    # Session state del modal
    # -------------------------
    if "ipi_modal_open" not in st.session_state:
        st.session_state["ipi_modal_open"] = False
        st.session_state["ipi_modal_div_name"] = None
        st.session_state["ipi_modal_div_code"] = None
        st.session_state["ipi_modal_div_idx_c5"] = None

    def _open_modal(div_name: str, div_code: str, div_idx_c5: int):
        st.session_state["ipi_modal_open"] = True
        st.session_state["ipi_modal_div_name"] = div_name
        st.session_state["ipi_modal_div_code"] = div_code
        st.session_state["ipi_modal_div_idx_c5"] = div_idx_c5

    # -------------------------
    # Carga Excel INDEC
    # -------------------------
    df_c2, df_c5 = cargar_ipi_excel()
    if df_c2 is None or df_c5 is None:
        st.error("Error al descargar el Excel del INDEC.")
        return

    names_c2 = [str(x).strip() for x in df_c2.iloc[3].fillna("").tolist()]
    codes_c2 = [str(x).strip() for x in df_c2.iloc[2].fillna("").tolist()]
    names_c5 = [str(x).strip() for x in df_c5.iloc[3].fillna("").tolist()]
    codes_c5 = [str(x).strip() for x in df_c5.iloc[2].fillna("").tolist()]

    header_idxs_c2, code_to_header_idx_c2 = _build_div_blocks(codes_c2)

    # -------------------------
    # Nivel general
    # -------------------------
    ng_se = procesar_serie_excel(df_c5, 3)     # (s.e)
    ng_orig = procesar_serie_excel(df_c2, 3)   # original

    if ng_se is None or ng_se.empty or ng_orig is None or ng_orig.empty:
        st.warning("No se pudieron extraer series del Excel.")
        return

    m_se = calc_var(ng_se["valor"], 1)
    i_yoy = calc_var(ng_orig["valor"], 12)

    # =========================
    # IPI – render estilo CEU
    # =========================
    INFORME_CEU_URL = "https://uia.org.ar/centro-de-estudios/documentos/actualidad-industrial/?q=Industrial"

    mes_txt = obtener_nombre_mes(ng_se["fecha"].iloc[-1])
    m_pct = f"{fmt_es(m_se, 1)}%"
    i_pct = f"{fmt_es(i_yoy, 1)}%"

    # =========================================================================
    # REEMPLAZA SOLO ESTA DEFINICIÓN DE html_content
    # =========================================================================
    
    # Usamos textwrap.dedent y alineamos el HTML a la izquierda internamente 
    # para evitar que Markdown crea que es un bloque de código.
    html_content = textwrap.dedent(f"""
    <div class="emp-wrap" style="margin-top:14px;">
        <div class="emp-title-row">
            <div class="emp-title-left">
                <div class="emp-icon-badge">🏭</div>
                <div>
                    <div class="emp-title">IPI Manufacturero - {mes_txt}</div>
                    <div class="emp-subtitle">Fuente: INDEC</div>
                </div>
            </div>
            <div class="emp-report">
                <a href="{INFORME_CEU_URL}" target="_blank">
                    📄 Ver último Informe Industrial
                </a>
            </div>
            </div>
        
    <div class="emp-card">
            <div class="emp-kpi-grid" style="grid-template-columns: 1fr 1fr;">
                <div class="emp-kpi">
                    <div class="emp-meta">Variación mensual (s.e)</div>
                    <div class="emp-value">{m_pct}</div>
                </div>
                <div class="emp-kpi">
                    <div class="emp-meta">Variación interanual</div>
                    <div class="emp-value">{i_pct}</div>
                </div>
            </div>
    </div>
        
    <div class="emp-note" style="font-size: 11px">
        Nota: (s.e) = sin estacionalidad.
    </div>
    </div>
    """)

    st.markdown(html_content, unsafe_allow_html=True)

    # -------------------------
    # Divisiones (cards)
    # -------------------------
    st.markdown("### Divisiones industriales")
    st.caption("Hacé click en una división para abrir el detalle (subsectores + Gráfico).")

    divs_idxs = [
        i for i, n in enumerate(names_c5)
        if i >= 3 and i % 2 != 0 and n not in ("", "Período", "IPI Manufacturero")
    ]

    for start in range(0, len(divs_idxs), 3):
        cols = st.columns(3, vertical_alignment="top")

        for j, idx in enumerate(divs_idxs[start:start + 3]):
            name = names_c5[idx]
            div_code = str(codes_c5[idx]).strip()

            s_se = procesar_serie_excel(df_c5, idx)
            v_m = calc_var(s_se["valor"], 1) if (s_se is not None and not s_se.empty) else np.nan

            v_i = np.nan
            header_idx = code_to_header_idx_c2.get(div_code, None)
            if header_idx is not None:
                s_orig = procesar_serie_excel(df_c2, header_idx)
                if s_orig is not None and not s_orig.empty:
                    v_i = calc_var(s_orig["valor"], 12)

            # Usamos textwrap.dedent aquí también por seguridad
            card_html = textwrap.dedent(f"""
                <div class="ipi-card">
                  <div class="ipi-title">{name}</div>
                  <div class="ipi-row">
                    <div style="display:flex; gap:10px; align-items:center;">
                      <div class="ipi-badge {_dot_class(v_m)}">{_fmt_pct_es(v_m, 1)}</div>
                      <div><div class="ipi-label">Mensual (s.e)</div></div>
                    </div>
                    <div style="display:flex; gap:10px; align-items:center;">
                      <div class="ipi-badge {_dot_class(v_i)}">{_fmt_pct_es(v_i, 1)}</div>
                      <div><div class="ipi-label">Interanual</div></div>
                    </div>
                  </div>
                </div>
            """)

            with cols[j]:
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button("Abrir detalle", key=f"ipi_open_{idx}", width='stretch'):
                    if div_code and div_code.lower() != "nan":
                        _open_modal(name, div_code, idx)
                        st.rerun()
                    else:
                        st.warning("No se encontró el código de la división.")

    # -------------------------
    # MODAL
    # -------------------------
    if st.session_state.get("ipi_modal_open"):
        div_name = st.session_state.get("ipi_modal_div_name")
        div_code = st.session_state.get("ipi_modal_div_code")
        div_idx_c5 = st.session_state.get("ipi_modal_div_idx_c5")

        @st.dialog(f"{div_name}")
        def _modal():
            s_div_se = procesar_serie_excel(df_c5, int(div_idx_c5))
            v_m_div = calc_var(s_div_se["valor"], 1) if (s_div_se is not None and not s_div_se.empty) else np.nan

            header_idx = code_to_header_idx_c2.get(str(div_code).strip(), None)
            if header_idx is None:
                candidates = [i2 for i2 in header_idxs_c2 if names_c2[i2].strip() == str(div_name).strip()]
                if candidates:
                    header_idx = candidates[0]

            v_i_div = np.nan
            if header_idx is not None:
                s_div_orig = procesar_serie_excel(df_c2, header_idx)
                v_i_div = calc_var(s_div_orig["valor"], 12) if (s_div_orig is not None and not s_div_orig.empty) else np.nan

            # Usamos textwrap.dedent
            st.markdown(
                textwrap.dedent(f"""
                <div class="ipi-mini-wrap">
                    <div class="ipi-mini">
                        <div class="ipi-mini-lbl">Mensual (s.e)</div>
                        <div class="ipi-mini-row">
                        <div class="ipi-dot {_dot_class(v_m_div)}">
                            {_fmt_pct_es(v_m_div, 1)}
                        </div>
                        </div>
                    </div>
                    <div class="ipi-mini">
                        <div class="ipi-mini-lbl">Interanual</div>
                        <div class="ipi-mini-row">
                        <div class="ipi-dot {_dot_class(v_i_div)}">
                            {_fmt_pct_es(v_i_div, 1)}
                        </div>
                        </div>
                    </div>
                </div>
                """),
                unsafe_allow_html=True,
            )

            st.caption("Nota: **(s.e)** = sin estacionalidad.")
            tab1, tab2 = st.tabs(["🔎 Subsectores", "📈 Gráfico"])

            with tab1:
                st.caption("Variación interanual (%). Fuente: INDEC – IPI Manufacturero (Excel)")
                if header_idx is None:
                    st.warning("No se pudo ubicar la división en el Cuadro 2.")
                else:
                    subcols = list(_subcol_range_for_header(header_idx, header_idxs_c2, len(codes_c2)))
                    rows = []
                    for k in subcols:
                        nm = str(names_c2[k]).strip()
                        if nm in ("", "Período", "IPI Manufacturero"):
                            continue
                        s_sub = procesar_serie_excel(df_c2, k)
                        if s_sub is None or s_sub.empty:
                            continue
                        yoy = calc_var(s_sub["valor"], 12)
                        rows.append({"Subsector": nm, "Interanual (%)": yoy})

                    if not rows:
                        st.info("No hay desglose adicional disponible.")
                    else:
                        df_sub = pd.DataFrame(rows)
                        df_sub["Interanual (%)"] = pd.to_numeric(df_sub["Interanual (%)"], errors="coerce")
                        df_sub = df_sub.sort_values("Interanual (%)", ascending=False).reset_index(drop=True)
                        df_sub["Interanual"] = df_sub["Interanual (%)"].apply(lambda x: _fmt_pct_es(x, 1))

                        st.dataframe(
                            df_sub[["Subsector", "Interanual"]],
                            width='stretch',
                            height=520,
                            hide_index=True,
                            column_config={
                                "Subsector": st.column_config.TextColumn("Subsector"),
                                "Interanual": st.column_config.TextColumn("Interanual", help="Variación interanual (%)"),
                            },
                        )

            with tab2:
                st.caption("Serie (s.e). Fuente: INDEC – IPI Manufacturero (Excel)")
                if s_div_se is None or s_div_se.empty:
                    st.warning("No se pudo extraer la serie (s.e).")
                else:
                    s_div_se = s_div_se.copy()
                    s_div_se["fecha"] = pd.to_datetime(s_div_se["fecha"], errors="coerce")
                    s_div_se = s_div_se.dropna(subset=["fecha"]).sort_values("fecha")
                    
                    show_total = st.checkbox("Mostrar también el Total IPI (s.e)", value=True)
                    min_date = s_div_se["fecha"].min().date()
                    max_date = s_div_se["fecha"].max().date()
                    
                    try:
                        default_start = (pd.Timestamp(max_date) - pd.DateOffset(years=5)).date()
                        if default_start < min_date: default_start = min_date
                    except: default_start = min_date

                    d1, d2 = st.slider("Rango de fechas", min_value=min_date, max_value=max_date, value=(default_start, max_date))
                    s_div_plot = s_div_se[(s_div_se["fecha"].dt.date >= d1) & (s_div_se["fecha"].dt.date <= d2)]

                    fig = go.Figure()
                    if show_total:
                        ng_se2 = ng_se.copy()
                        ng_se2["fecha"] = pd.to_datetime(ng_se2["fecha"], errors="coerce")
                        ng_se2 = ng_se2.dropna(subset=["fecha"]).sort_values("fecha")
                        s_tot = ng_se2[(ng_se2["fecha"].dt.date >= d1) & (ng_se2["fecha"].dt.date <= d2)]
                        fig.add_trace(go.Scatter(x=s_tot["fecha"], y=s_tot["valor"], mode="lines", name="Total (s.e)", line=dict(width=2)))

                    fig.add_trace(go.Scatter(x=s_div_plot["fecha"], y=s_div_plot["valor"], mode="lines", name=f"{div_name} (s.e)", line=dict(width=3)))
                    fig.update_layout(template="plotly_white", height=420, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
                    st.plotly_chart(fig, width='stretch')

            if st.button("Cerrar", width='stretch'):
                st.session_state["ipi_modal_open"] = False
                st.rerun()

        _modal()