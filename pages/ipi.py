# pages/ipi.py
import random
import textwrap
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from services.ipi_data import cargar_ipi_excel, procesar_serie_excel


# ============================================================
# Frases (loading) — mismas del page EMAE
# ============================================================
INDU_LOADING_PHRASES = [
    "La industria aporta más del 18% del valor agregado de la economía argentina.",
    "La industria es el segundo mayor empleador privado del país.",
    "Por cada empleo industrial directo se generan casi dos empleos indirectos.",
    "Los salarios industriales son 23% más altos que el promedio privado.",
    "Dos tercios de las exportaciones argentinas provienen de la industria.",
]

MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Link header (pedido)
INFORME_CEU_URL = "https://uia.org.ar/centro-de-estudios/documentos/actualidad-industrial/?q=Industrial"

# Rebase (pedido)
BASE_DT = pd.Timestamp("2023-04-01")  # abr-23 (MS)


# ============================================================
# Helpers (formato EMAE)
# ============================================================
def _fmt_pct_es(x: float, dec: int = 1) -> str:
    try:
        return f"{float(x):.{dec}f}".replace(".", ",")
    except Exception:
        return "—"


def _arrow_cls(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ("", "")
    return ("▲", "fx-up") if v >= 0 else ("▼", "fx-down")


def _month_label_es(dt: pd.Timestamp) -> str:
    if dt is None or pd.isna(dt):
        return "—"
    dt = pd.to_datetime(dt)
    return f"{MESES_ES[dt.month-1]}-{dt.year}"


def _compute_yoy_df(df: pd.DataFrame) -> pd.DataFrame:
    t = df.dropna(subset=["Date", "Value"]).sort_values("Date").copy()
    t["YoY"] = (t["Value"] / t["Value"].shift(12) - 1.0) * 100.0
    return t


def _compute_mom_df(df: pd.DataFrame) -> pd.DataFrame:
    t = df.dropna(subset=["Date", "Value"]).sort_values("Date").copy()
    t["MoM"] = (t["Value"] / t["Value"].shift(1) - 1.0) * 100.0
    return t


def _clean_series(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Date", "Value"])
    t = df.copy()
    t["Date"] = pd.to_datetime(t["Date"], errors="coerce")
    t["Value"] = pd.to_numeric(t["Value"], errors="coerce")
    return t.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)


def _rebase_100(df: pd.DataFrame, base_dt: pd.Timestamp) -> pd.DataFrame:
    """Rebase a 100 en base_dt si existe ese mes. Si no existe, devuelve igual."""
    if df is None or df.empty:
        return df
    t = df.copy()
    t["Date"] = pd.to_datetime(t["Date"], errors="coerce")
    t["Value"] = pd.to_numeric(t["Value"], errors="coerce")
    t = t.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)

    base_val = t.loc[t["Date"] == base_dt, "Value"]
    if base_val.empty:
        return t
    b = float(base_val.iloc[0])
    if b == 0 or np.isnan(b):
        return t

    t["Value"] = (t["Value"] / b) * 100.0
    return t


# ============================================================
# Helpers para detectar divisiones en Excel (igual lógica que tenías)
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


def _build_div_blocks(codes: List[str]) -> Tuple[List[int], Dict[str, int]]:
    header_idxs = []
    code_to_idx = {}
    for i, c in enumerate(codes):
        if i < 3:
            continue
        if _is_header_div(c):
            header_idxs.append(i)
            code_to_idx[str(c).strip()] = i
    return header_idxs, code_to_idx


# ============================================================
# CSS (COPIA del formato TASA / EMAE — NO MODIFICAR)
# + agrega estilo del link (pedido)
# ============================================================
def _inject_css_fx():
    st.markdown(
        textwrap.dedent(
            """
        <style>
          /* ===== HEADER ===== */
          .fx-wrap{
            background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 100%);
            border: 1px solid #dfeaf6;
            border-radius: 22px;
            padding: 12px;
            box-shadow:
              0 10px 24px rgba(15, 55, 100, 0.16),
              inset 0 0 0 1px rgba(255,255,255,0.55);
          }

          .fx-title-row{
            display:flex;
            align-items:center;
            gap: 12px;
            margin-bottom: 8px;
            padding-left: 4px;
          }

          .fx-icon-badge{
            width: 64px;
            height: 52px;
            border-radius: 14px;
            background: linear-gradient(180deg, #e7eef6 0%, #dfe7f1 100%);
            border: 1px solid rgba(15,23,42,0.10);
            display:flex;
            align-items:center;
            justify-content:center;
            box-shadow: 0 8px 14px rgba(15,55,100,0.12);
            font-size: 32px;
            flex: 0 0 auto;
          }

          .fx-title{
            font-size: 23px;
            font-weight: 900;
            letter-spacing: -0.01em;
            color: #14324f;
            margin: 0;
            line-height: 1.0;
          }

          .fx-card{
            background: rgba(255,255,255,0.94);
            border: 1px solid rgba(15, 23, 42, 0.10);
            border-radius: 18px;
            padding: 14px 14px 12px 14px;
            box-shadow: 0 10px 18px rgba(15, 55, 100, 0.10);
          }

          .fx-row{
            display: grid;
            grid-template-columns: auto 1fr auto;
            align-items: center;
            column-gap: 14px;
          }

          .fx-value{
            font-size: 46px;
            font-weight: 950;
            letter-spacing: -0.02em;
            color: #14324f;
            line-height: 0.95;
          }

          .fx-meta{
            font-size: 13px;
            color: #2b4660;
            font-weight: 700;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
          .fx-meta .sep{ opacity: 0.40; padding: 0 6px; }

          .fx-pills{
            display:flex;
            gap: 10px;
            justify-content: flex-end;
            align-items: center;
            white-space: nowrap;
          }

          .fx-pill{
            display:inline-flex;
            align-items:center;
            gap: 8px;
            padding: 7px 10px;
            border-radius: 12px;
            border: 1px solid rgba(15,23,42,0.10);
            font-size: 13px;
            font-weight: 700;
            box-shadow: 0 6px 10px rgba(15,55,100,0.08);
          }

          .fx-pill .lab{ color:#2b4660; font-weight: 900; }

          .fx-pill.red{
            background: linear-gradient(180deg, rgba(220,38,38,0.08) 0%, rgba(220,38,38,0.05) 100%);
          }
          .fx-pill.green{
            background: linear-gradient(180deg, rgba(22,163,74,0.10) 0%, rgba(22,163,74,0.06) 100%);
          }

          .fx-up{ color:#168a3a; font-weight: 900; }
          .fx-down{ color:#cc2e2e; font-weight: 900; }

          .fx-arrow{
            width: 14px;
            text-align:center;
            font-weight: 900;
          }

          .fx-panel-title{
            font-size: 12px;
            font-weight: 900;
            color: rgba(20,50,79,0.78);
            margin: 0 0 6px 2px;
            letter-spacing: 0.01em;
          }

          .fx-panel-gap{ height: 16px; }

          /* ===============================
             PANEL GRANDE REAL (aplicado por JS al contenedor de Streamlit)
             =============================== */
          .fx-panel-wrap{
            background: rgba(230, 243, 255, 0.55);
            border: 1px solid rgba(15, 55, 100, 0.10);
            border-radius: 22px;
            padding: 16px 16px 26px 16px;
            box-shadow: 0 10px 18px rgba(15,55,100,0.06);
            margin-top: 10px;
          }

          /* Evitar “cortes” visuales dentro del panel */
          .fx-panel-wrap div[data-testid="stSelectbox"],
          .fx-panel-wrap div[data-testid="stMultiSelect"],
          .fx-panel-wrap div[data-testid="stSlider"],
          .fx-panel-wrap div[data-testid="stPlotlyChart"]{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
          }

          /* Estilo combobox base (default) */
          .fx-panel-wrap div[role="combobox"]{
            border-radius: 16px !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
            background: rgba(255,255,255,0.94) !important;
            box-shadow: 0 10px 18px rgba(15, 55, 100, 0.08) !important;
          }

          /* Selectbox medida estilo chip (oscuro + texto azul) */
          .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"]{
            background: #0b2a55 !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            box-shadow: 0 10px 18px rgba(15, 55, 100, 0.10) !important;
          }
          .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"] *{
            color: #8fc2ff !important;
            fill: #8fc2ff !important;
            font-weight: 800 !important;
          }

          /* Tags multiselect (texto BLANCO garantizado) */
          .fx-panel-wrap span[data-baseweb="tag"]{
            background: #0b2a55 !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
          }
          .fx-panel-wrap span[data-baseweb="tag"] *{
            color: #ffffff !important;
            fill: #ffffff !important;
            font-weight: 800 !important;
          }

          /* Link “Informe CEU” (pedido) */
          .fx-report a{
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
            white-space: nowrap;
          }

          @media (max-width: 900px){
            .fx-row{ grid-template-columns: 1fr; row-gap: 10px; }
            .fx-meta{ white-space: normal; }
            .fx-pills{ justify-content: flex-start; }
          }
        </style>
        """
        ),
        unsafe_allow_html=True,
    )


def _apply_panel_wrap(marker_id: str):
    st.markdown(f"<span id='{marker_id}'></span>", unsafe_allow_html=True)
    components.html(
        f"""
        <script>
        (function() {{
          function applyPanelClass() {{
            const marker = window.parent.document.getElementById('{marker_id}');
            if (!marker) return;
            const block = marker.closest('div[data-testid="stVerticalBlock"]');
            if (block) block.classList.add('fx-panel-wrap');
          }}

          applyPanelClass();

          let tries = 0;
          const t = setInterval(() => {{
            applyPanelClass();
            tries += 1;
            if (tries >= 10) clearInterval(t);
          }}, 150);

          const obs = new MutationObserver(() => applyPanelClass());
          obs.observe(window.parent.document.body, {{ childList: true, subtree: true }});
          setTimeout(() => obs.disconnect(), 3000);
        }})();
        </script>
        """,
        height=0,
    )


# ============================================================
# Main
# ============================================================
def render_ipi(go_to):
    _inject_css_fx()

    # =========================
    # Volver (igual patrón EMAE)
    # =========================
    if st.button("← Volver"):
        go_to("home")

    # =========================
    # Load data (Excel INDEC)
    # =========================
    fact = st.empty()
    fact.info("💡 " + random.choice(INDU_LOADING_PHRASES))

    with st.spinner("Cargando indicadores..."):
        df_c2, df_c5 = cargar_ipi_excel()

    fact.empty()

    if df_c2 is None or df_c5 is None:
        st.error("No pude cargar el Excel del IPI Manufacturero (INDEC).")
        return

    # --- headers/nombres/códigos ---
    names_c2 = [str(x).strip() for x in df_c2.iloc[3].fillna("").tolist()]
    codes_c2 = [str(x).strip() for x in df_c2.iloc[2].fillna("").tolist()]
    names_c5 = [str(x).strip() for x in df_c5.iloc[3].fillna("").tolist()]
    codes_c5 = [str(x).strip() for x in df_c5.iloc[2].fillna("").tolist()]

    header_idxs_c2, code_to_header_idx_c2 = _build_div_blocks(codes_c2)

    # --- Total (nivel general): col 3 ---
    ng_se_raw = procesar_serie_excel(df_c5, 3)   # s.e.
    ng_orig_raw = procesar_serie_excel(df_c2, 3) # original

    # normalizo a formato EMAE: Date/Value y REBASE (pedido)
    df_ng_se = _rebase_100(_clean_series(ng_se_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
    df_ng_o  = _rebase_100(_clean_series(ng_orig_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)

    if df_ng_se.empty or df_ng_o.empty:
        st.error("No pude extraer la serie de IPI (nivel general) desde el Excel.")
        return

    # --- KPIs header (YoY original + MoM s.e.) ---
    yoy_full = _compute_yoy_df(df_ng_o)
    mom_full = _compute_mom_df(df_ng_se)

    yoy_val = yoy_full["YoY"].dropna().iloc[-1] if yoy_full["YoY"].notna().any() else None
    yoy_date = yoy_full.dropna(subset=["YoY"]).iloc[-1]["Date"] if yoy_full["YoY"].notna().any() else None

    mom_val = mom_full["MoM"].dropna().iloc[-1] if mom_full["MoM"].notna().any() else None
    mom_date = mom_full.dropna(subset=["MoM"]).iloc[-1]["Date"] if mom_full["MoM"].notna().any() else None

    # --- lista de divisiones (misma lógica) ---
    divs_idxs = [
        i for i, n in enumerate(names_c5)
        if i >= 3 and i % 2 != 0 and n not in ("", "Período", "IPI Manufacturero")
    ]

    # --- diccionario de series por variable (label -> (orig, se)) ---
    # Incluye TOTAL + todas las divisiones
    SERIES: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]] = {
        "IPI - Nivel general": (df_ng_o, df_ng_se),
    }

    for idx in divs_idxs:
        div_name = names_c5[idx]
        div_code = str(codes_c5[idx]).strip()

        # s.e. (Cuadro 5)
        s_se_raw = procesar_serie_excel(df_c5, idx)
        s_se = _rebase_100(_clean_series(s_se_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)

        # original (Cuadro 2) por header idx
        header_idx = code_to_header_idx_c2.get(div_code, None)
        if header_idx is not None:
            s_o_raw = procesar_serie_excel(df_c2, int(header_idx))
            s_o = _rebase_100(_clean_series(s_o_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
        else:
            s_o = pd.DataFrame(columns=["Date", "Value"])

        SERIES[div_name] = (s_o, s_se)

    # =========================================================
    # BLOQUE 1 — IPI (mismo panel que EMAE)
    # + link (pedido)
    # + rebase (ya aplicado a SERIES)
    # + medida extra: "Variación acumulada sin estacionalidad" (pedido)
    # =========================================================
    with st.container():
        _apply_panel_wrap("ipi_panel_marker")

        # Header (mismo HTML que EMAE + link arriba a la derecha)
        a_yoy, cls_yoy = _arrow_cls(yoy_val)
        a_mom, cls_mom = _arrow_cls(mom_val)

        header_lines = [
            '<div class="fx-wrap">',
            '  <div class="fx-title-row" style="justify-content:space-between;">',
            '    <div style="display:flex; align-items:center; gap:12px;">',
            '      <div class="fx-icon-badge">🏭</div>',
            '      <div class="fx-title">Índice de Producción Industrial (IPI)</div>',
            "    </div>",
            f'    <div class="fx-report"><a href="{INFORME_CEU_URL}" target="_blank">📄 Ver último Informe Industrial</a></div>',
            "  </div>",
            '  <div class="fx-card">',
            '    <div class="fx-row">',
            f'      <div class="fx-value">{_fmt_pct_es(yoy_val, 1)}%</div>' if yoy_val is not None else '      <div class="fx-value">—</div>',
            '      <div class="fx-meta">',
            f'        IPI (original)<span class="sep">|</span>YoY<span class="sep">|</span>{_month_label_es(yoy_date)}',
            "      </div>",
            '      <div class="fx-pills">',
            '        <div class="fx-pill red">',
            f'          <span class="fx-arrow {cls_yoy}">{a_yoy}</span>',
            f'          <span class="{cls_yoy}">{_fmt_pct_es(yoy_val, 1) if yoy_val is not None else "—"}%</span>',
            '          <span class="lab">anual</span>',
            "        </div>",
            '        <div class="fx-pill green">',
            f'          <span class="fx-arrow {cls_mom}">{a_mom}</span>',
            f'          <span class="{cls_mom}">{_fmt_pct_es(mom_val, 1) if mom_val is not None else "—"}%</span>',
            '          <span class="lab">mensual</span>',
            "        </div>",
            "      </div>",
            "    </div>",
            "  </div>",
            "</div>",
        ]
        st.markdown("\n".join(header_lines), unsafe_allow_html=True)

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        # Defaults (state)
        if "ipi_medida" not in st.session_state:
            st.session_state["ipi_medida"] = "Nivel desestacionalizado"
        if "ipi_vars" not in st.session_state:
            st.session_state["ipi_vars"] = ["IPI - Nivel general"]

        # Controles (mismo layout)
        c1, c2 = st.columns(2, gap="large")

        with c1:
            st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
            st.selectbox(
                "",
                [
                    "Nivel desestacionalizado",
                    "Nivel original",
                    "Variación acumulada sin estacionalidad",
                ],
                key="ipi_medida",
                label_visibility="collapsed",
            )

        with c2:
            st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
            st.multiselect(
                "",
                options=list(SERIES.keys()),
                key="ipi_vars",
                label_visibility="collapsed",
            )

        vars_sel = st.session_state.get("ipi_vars", [])
        if not vars_sel:
            st.warning("Seleccioná una variable.")
            return

        medida = st.session_state.get("ipi_medida", "Nivel desestacionalizado")

        # Slider mensual (select_slider) armado con min/max real sobre series seleccionadas
        date_mins = []
        date_maxs = []

        for vname in vars_sel:
            df_o, df_s = SERIES.get(vname, (pd.DataFrame(), pd.DataFrame()))
            if medida == "Nivel original":
                base = df_o
            else:
                base = df_s  # desestacionalizado o acumulada s.e.

            if base is not None and not base.empty and "Date" in base.columns:
                date_mins.append(pd.to_datetime(base["Date"].min()))
                date_maxs.append(pd.to_datetime(base["Date"].max()))

        # fallback seguro
        if not date_mins or not date_maxs:
            date_mins = [pd.to_datetime(df_ng_se["Date"].min())]
            date_maxs = [pd.to_datetime(df_ng_se["Date"].max())]

        min_real = min(date_mins)
        max_real = max(date_maxs)

        months = pd.date_range(
            min_real.to_period("M").to_timestamp(),
            max_real.to_period("M").to_timestamp(),
            freq="MS",
        )
        months_d = [m.date() for m in months]

        # default: últimos 5 años si existe
        try:
            default_start = (pd.Timestamp(max_real) - pd.DateOffset(years=5)).date()
        except Exception:
            default_start = months_d[0]

        start_default = max(default_start, months_d[0])
        end_default = months_d[-1]

        st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
        start_d, end_d = st.select_slider(
            "",
            options=months_d,
            value=(start_default, end_default),
            format_func=lambda d: f"{MESES_ES[pd.Timestamp(d).month-1]}-{pd.Timestamp(d).year}",
            label_visibility="collapsed",
            key="ipi_range",
        )

        start_ts = pd.Timestamp(start_d).to_period("M").to_timestamp()
        end_ts = pd.Timestamp(end_d).to_period("M").to_timestamp()

        # Plot
        fig = go.Figure()

        if medida in ("Nivel desestacionalizado", "Nivel original"):
            for vname in vars_sel:
                df_o, df_s = SERIES.get(
                    vname,
                    (pd.DataFrame(columns=["Date", "Value"]), pd.DataFrame(columns=["Date", "Value"])),
                )
                base = df_s if medida == "Nivel desestacionalizado" else df_o
                base = base[(base["Date"] >= start_ts) & (base["Date"] <= end_ts)].copy()

                if not base.empty:
                    suf = "(s.e.)" if medida == "Nivel desestacionalizado" else "(original)"
                    fig.add_trace(
                        go.Scatter(
                            x=base["Date"],
                            y=base["Value"],
                            mode="lines+markers",
                            name=f"{vname} {suf}",
                        )
                    )
            fig.update_yaxes(title="Índice (base 100=abr-23)")

        else:
            # Variación acumulada sin estacionalidad:
            # acumulado sobre el rango seleccionado = (nivel_s.e._t / nivel_s.e._inicio - 1) * 100
            for vname in vars_sel:
                _, df_s = SERIES.get(vname, (pd.DataFrame(columns=["Date", "Value"]), pd.DataFrame(columns=["Date", "Value"])))
                t = df_s[(df_s["Date"] >= start_ts) & (df_s["Date"] <= end_ts)].copy()
                t = t.dropna(subset=["Date", "Value"]).sort_values("Date")
                if t.empty:
                    continue
                base_val = float(t["Value"].iloc[0])
                if base_val == 0 or np.isnan(base_val):
                    continue
                t["Acc"] = (t["Value"] / base_val - 1.0) * 100.0

                fig.add_trace(
                    go.Scatter(
                        x=t["Date"],
                        y=t["Acc"],
                        mode="lines+markers",
                        name=f"{vname} (acum s.e.)",
                    )
                )
            fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="#666666")
            fig.update_yaxes(ticksuffix="%", title="Variación acumulada (%)")

        fig.update_layout(
            height=520,
            hovermode="x unified",
            margin=dict(l=10, r=10, t=10, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            dragmode=False,
        )

        # Aire a la derecha
        x_max = pd.Timestamp(end_ts) + pd.Timedelta(days=10)
        fig.update_xaxes(range=[pd.Timestamp(start_ts), x_max])

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
            key="chart_ipi_panel1",
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
            "Fuente: INDEC — IPI Manufacturero (Excel .xls)"
            "</div>",
            unsafe_allow_html=True,
        )

    # =========================================================
    # BLOQUE 2 — IPI por ramas (comparación A/B) — estilo EMAE sectores
    # + “Variación serie sin estacionalidad”: Período B no repite mes de Período A (pedido)
    # =========================================================
    st.divider()

    with st.container():
        _apply_panel_wrap("ipi_sect_panel_marker")

        header2_lines = [
            '<div class="fx-wrap">',
            '  <div class="fx-title-row">',
            '    <div class="fx-icon-badge">🏭</div>',
            '    <div class="fx-title">Índice de Producción Industrial por Ramas</div>',
            "  </div>",
            "</div>",
        ]
        st.markdown("\n".join(header2_lines), unsafe_allow_html=True)

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        # Armo tabla "larga" para comparación por ramas
        rows_o = []
        rows_s = []

        for vname, (df_o, df_s) in SERIES.items():
            if df_o is not None and not df_o.empty:
                tmp = df_o.copy()
                tmp["Sector"] = vname
                rows_o.append(tmp)
            if df_s is not None and not df_s.empty:
                tmp = df_s.copy()
                tmp["Sector"] = vname
                rows_s.append(tmp)

        df_o_long = pd.concat(rows_o, ignore_index=True) if rows_o else pd.DataFrame(columns=["Date", "Value", "Sector"])
        df_s_long = pd.concat(rows_s, ignore_index=True) if rows_s else pd.DataFrame(columns=["Date", "Value", "Sector"])

        if df_o_long.empty and df_s_long.empty:
            st.error("No hay datos suficientes para construir la apertura por ramas.")
            return

        # Último mes disponible (preferimos original; si no, s.e.)
        max_dt_o = pd.to_datetime(df_o_long["Date"].max()) if not df_o_long.empty else None
        max_dt_s = pd.to_datetime(df_s_long["Date"].max()) if not df_s_long.empty else None
        max_dt = max([d for d in [max_dt_o, max_dt_s] if d is not None])

        last_month_num = int(max_dt.month)
        last_month_label = MESES_ES[last_month_num - 1]  # ene..dic

        years_all = sorted(pd.to_datetime(df_o_long["Date"]).dt.year.unique().tolist(), reverse=True) if not df_o_long.empty else []

        def _month_opt_label(dt: pd.Timestamp) -> str:
            return _month_label_es(pd.to_datetime(dt))

        # =========================
        # Tipo de comparación (3 opciones)
        # =========================
        acc_label = f"Variación acumulada anual (ene-{last_month_label})"

        MODE_LABELS = {
            "acum": acc_label,
            "anual": "Variación anual",
            "se": "Variación serie sin estacionalidad",
        }
        MODE_KEYS = list(MODE_LABELS.keys())

        if "ipi_sec_mode_key" not in st.session_state:
            st.session_state["ipi_sec_mode_key"] = "acum"

        r1c1, r1c2 = st.columns(2, gap="large")

        with r1c1:
            st.markdown("<div class='fx-panel-title'>Tipo de comparación</div>", unsafe_allow_html=True)
            mode_key = st.selectbox(
                "",
                MODE_KEYS,
                format_func=lambda k: MODE_LABELS.get(k, k),
                key="ipi_sec_mode_key",
                label_visibility="collapsed",
            )

        with r1c2:
            st.markdown("&nbsp;", unsafe_allow_html=True)

        # =========================
        # Período A / B
        # =========================
        colA, colB = st.columns(2, gap="large")

        if mode_key == "acum":
            if not years_all:
                st.warning("No hay años disponibles en la serie original.")
                return

            if "ipi_sec_year_a" not in st.session_state:
                st.session_state["ipi_sec_year_a"] = years_all[0]
            if "ipi_sec_year_b" not in st.session_state:
                st.session_state["ipi_sec_year_b"] = years_all[1] if len(years_all) > 1 else years_all[0]

            with colA:
                st.markdown("<div class='fx-panel-title'>Período A</div>", unsafe_allow_html=True)
                st.selectbox("", years_all, key="ipi_sec_year_a", label_visibility="collapsed")

            with colB:
                st.markdown("<div class='fx-panel-title'>Período B</div>", unsafe_allow_html=True)
                st.selectbox("", years_all, key="ipi_sec_year_b", label_visibility="collapsed")

            year_a = int(st.session_state.get("ipi_sec_year_a"))
            year_b = int(st.session_state.get("ipi_sec_year_b"))

            def _accum_avg_by_sector_orig(year: int) -> pd.Series:
                t = df_o_long[df_o_long["Date"].dt.year == year].copy()
                t = t[t["Date"].dt.month <= last_month_num]
                return t.groupby("Sector")["Value"].mean()

            A = _accum_avg_by_sector_orig(year_a)
            B = _accum_avg_by_sector_orig(year_b)

            subtitle = f"Comparación acumulada ene–{last_month_label} (promedio) · A={year_a} / B={year_b}"

        elif mode_key == "anual":
            month_num = last_month_num

            possible_dates = []
            if not df_o_long.empty:
                for y in years_all:
                    dt = pd.Timestamp(year=y, month=month_num, day=1)
                    if (df_o_long["Date"] == dt).any():
                        possible_dates.append(dt)
            possible_dates = sorted(possible_dates, reverse=True)

            if not possible_dates:
                st.warning("No hay meses comparables en la serie original para la variación anual.")
                return

            if "ipi_sec_month_a" not in st.session_state:
                st.session_state["ipi_sec_month_a"] = possible_dates[0]
            if "ipi_sec_month_b" not in st.session_state:
                st.session_state["ipi_sec_month_b"] = possible_dates[1] if len(possible_dates) > 1 else possible_dates[0]

            with colA:
                st.markdown("<div class='fx-panel-title'>Período A</div>", unsafe_allow_html=True)
                st.selectbox(
                    "",
                    possible_dates,
                    key="ipi_sec_month_a",
                    format_func=_month_opt_label,
                    label_visibility="collapsed",
                )

            with colB:
                st.markdown("<div class='fx-panel-title'>Período B</div>", unsafe_allow_html=True)
                st.selectbox(
                    "",
                    possible_dates,
                    key="ipi_sec_month_b",
                    format_func=_month_opt_label,
                    label_visibility="collapsed",
                )

            dt_a = pd.to_datetime(st.session_state.get("ipi_sec_month_a"))
            dt_b = pd.to_datetime(st.session_state.get("ipi_sec_month_b"))

            def _month_level_by_sector_orig(dt: pd.Timestamp) -> pd.Series:
                t = df_o_long[df_o_long["Date"] == dt].copy()
                return t.groupby("Sector")["Value"].mean()

            A = _month_level_by_sector_orig(dt_a)
            B = _month_level_by_sector_orig(dt_b)

            subtitle = f"Comparación anual ({MESES_ES[month_num-1]}) · A={_month_opt_label(dt_a)} / B={_month_opt_label(dt_b)}"

        else:
            if df_s_long.empty:
                st.warning("No hay datos sin estacionalidad disponibles para esta comparación.")
                return

            possible_dates = sorted(df_s_long["Date"].dropna().unique().tolist(), reverse=True)
            possible_dates = [pd.to_datetime(d) for d in possible_dates]

            # A (cualquier mes)
            if "ipi_sec_se_month_a" not in st.session_state:
                st.session_state["ipi_sec_se_month_a"] = possible_dates[0] if possible_dates else None

            with colA:
                st.markdown("<div class='fx-panel-title'>Período A</div>", unsafe_allow_html=True)
                st.selectbox(
                    "",
                    possible_dates,
                    key="ipi_sec_se_month_a",
                    format_func=_month_opt_label,
                    label_visibility="collapsed",
                )

            dt_a = pd.to_datetime(st.session_state.get("ipi_sec_se_month_a"))

            # B: excluir el MISMO MES (month) que A (pedido)
            possible_dates_b = [d for d in possible_dates if pd.to_datetime(d).month != dt_a.month]
            if not possible_dates_b:
                st.warning("No hay meses alternativos para Período B (sin repetir el mes de A).")
                return

            # si el B guardado quedó inválido, resetear
            if ("ipi_sec_se_month_b" not in st.session_state) or (pd.to_datetime(st.session_state["ipi_sec_se_month_b"]).month == dt_a.month):
                st.session_state["ipi_sec_se_month_b"] = possible_dates_b[0]

            with colB:
                st.markdown("<div class='fx-panel-title'>Período B</div>", unsafe_allow_html=True)
                st.selectbox(
                    "",
                    possible_dates_b,
                    key="ipi_sec_se_month_b",
                    format_func=_month_opt_label,
                    label_visibility="collapsed",
                )

            dt_b = pd.to_datetime(st.session_state.get("ipi_sec_se_month_b"))

            def _month_level_by_sector_se(dt: pd.Timestamp) -> pd.Series:
                t = df_s_long[df_s_long["Date"] == dt].copy()
                return t.groupby("Sector")["Value"].mean()

            A = _month_level_by_sector_se(dt_a)
            B = _month_level_by_sector_se(dt_b)

            subtitle = f"Comparación serie s.e. · A={_month_opt_label(dt_a)} / B={_month_opt_label(dt_b)}"

        # =========================
        # %Δ = (A/B - 1) * 100
        # =========================
        common = pd.DataFrame({"A": A, "B": B}).dropna()
        common = common[(common["A"] > 0) & (common["B"] > 0)]

        if common.empty:
            st.warning("No hay datos suficientes para comparar esos períodos.")
            return

        common["pct"] = (common["A"] / common["B"] - 1.0) * 100.0
        common = common.reset_index().rename(columns={"index": "Sector"})

        # orden desc por variación
        common = common.sort_values("pct", ascending=False).reset_index(drop=True)

        # Plot: barras horizontales divergentes (mismo estilo EMAE)
        x = common["pct"].values
        x_min = float(np.nanmin(x)) if len(x) else 0.0
        x_max = float(np.nanmax(x)) if len(x) else 0.0

        pad = 0.15 * max(abs(x_min), abs(x_max), 1e-6)
        x_left = min(0.0, x_min) - pad
        x_right = max(0.0, x_max) + pad

        y_plain = common["Sector"].tolist()

        # Bold solo el nivel general
        y = [
            "<b>IPI - Nivel general</b>" if s == "IPI - Nivel general" else s
            for s in y_plain
        ]

        colors = np.where(x >= 0, "rgba(34,197,94,0.55)", "rgba(239,68,68,0.55)")

        fig2 = go.Figure()
        fig2.add_trace(
            go.Bar(
                x=x,
                y=y,
                orientation="h",
                marker=dict(color=colors),
                customdata=y_plain,
                text=[f"{v:.1f}%".replace(".", ",") for v in x],
                textposition="outside",
                texttemplate="%{text}",
                cliponaxis=False,
                hovertemplate="%{customdata}<br>%{x:.1f}%<extra></extra>",
                name="",
            )
        )

        fig2.update_layout(
            height=max(520, 26 * len(common) + 120),
            margin=dict(l=10, r=10, t=10, b=40),
            hovermode="closest",
            showlegend=False,
            dragmode=False,
        )
        fig2.update_xaxes(
            ticksuffix="%",
            range=[x_left, x_right],
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor="rgba(120,120,120,0.65)",
            showgrid=True,
            gridcolor="rgba(120,120,120,0.25)",
        )
        fig2.update_yaxes(autorange="reversed")

        st.markdown(f"<div class='fx-panel-title'>{subtitle}</div>", unsafe_allow_html=True)

        st.plotly_chart(
            fig2,
            use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
            key="chart_ipi_sect_comp",
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
            "Fuente: INDEC — IPI Manufacturero (Excel .xls)"
            "</div>",
            unsafe_allow_html=True,
        )
