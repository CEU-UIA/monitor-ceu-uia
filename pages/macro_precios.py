
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import textwrap
import streamlit.components.v1 as components

from services.macro_data import get_ipc_indec_full


# ============================================================
# Helpers
# ============================================================
def _fmt_pct_es(x: float, dec: int = 1) -> str:
    try:
        return f"{float(x):.{dec}f}".replace(".", ",")
    except Exception:
        return "—"


def _mes_es(m: int) -> str:
    return {
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"
    }[int(m)]


def _mmmyy_es(dt) -> str:
    dt = pd.to_datetime(dt)
    return f"{_mes_es(dt.month)}-{str(dt.year)[-2:]}"


def _mmmyy_num(dt) -> str:
    dt = pd.to_datetime(dt)
    return f"{dt.month:02d}/{str(dt.year)[-2:]}"


def _is_nivel_general(label: str) -> bool:
    return str(label).strip().lower() == "nivel general"


def _clean_code(x) -> str:
    s = str(x).strip()
    if s.endswith(".0") and s.replace(".0", "").isdigit():
        return s[:-2]
    return s


def _arrow_cls(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ("", "")
    return ("▲", "fx-up") if v >= 0 else ("▼", "fx-down")


def _tick_step_from_months(n_months: int) -> int:
    """
    Reduce la densidad de ticks del eje X para rangos largos.
    """
    if n_months <= 12:
        return 1     # mensual
    if n_months <= 24:
        return 2     # bimestral
    if n_months <= 48:
        return 3     # trimestral
    return 6         # semestral


# ============================================================
# Page
# ============================================================
def render_macro_precios(go_to):

    # =========================
    # Botón volver
    # =========================
    if st.button("← Volver"):
        go_to("macro_home")

    # =========================
    # CSS (mismo estilo que tipo de cambio)
    # =========================
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
            font-size: 56px;
            font-weight: 950;
            letter-spacing: -0.02em;
            color: #14324f;
            line-height: 0.95;
          }

          .fx-meta{
            font-size: 13px;
            color: #2b4660;
            font-weight: 800;
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
            font-weight: 800;
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
             PANEL GRANDE REAL
             =============================== */
          .fx-panel-wrap{
            background: rgba(230, 243, 255, 0.55);
            border: 1px solid rgba(15, 55, 100, 0.10);
            border-radius: 22px;
            padding: 16px 16px 26px 16px;
            box-shadow: 0 10px 18px rgba(15,55,100,0.06);
            margin-top: 10px;
          }

          .fx-panel-wrap div[data-testid="stSelectbox"],
          .fx-panel-wrap div[data-testid="stMultiSelect"],
          .fx-panel-wrap div[data-testid="stSlider"],
          .fx-panel-wrap div[data-testid="stPlotlyChart"],
          .fx-panel-wrap div[data-testid="stDownloadButton"],
          .fx-panel-wrap div[data-testid="stRadio"]{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
          }

          .fx-panel-wrap div[role="combobox"]{
            border-radius: 16px !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
            background: rgba(255,255,255,0.94) !important;
            box-shadow: 0 10px 18px rgba(15, 55, 100, 0.08) !important;
          }

          /* SELECTBOX "Medida" estilo chip oscuro */
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

          /* Tags multiselect visibles */
          .fx-panel-wrap span[data-baseweb="tag"]{
            background: #0b2a55 !important;
            color: #ffffff !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
          }
          .fx-panel-wrap span[data-baseweb="tag"] *{
            color: #ffffff !important;
            fill: #ffffff !important;
          }

          /* Evita que el texto del botón se parta en 2 líneas */
          div[data-testid="stButton"] button{
            white-space: nowrap !important;
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

    # =========================
    # Datos (Nacional)
    # =========================
    with st.spinner("Cargando datos..."):
        ipc = get_ipc_indec_full()

    ipc = ipc[ipc["Region"] == "Nacional"].copy()
    if ipc.empty:
        st.warning("Sin datos IPC.")
        return

    ipc["Codigo_str"] = ipc["Codigo"].apply(_clean_code).astype(str).str.strip()
    ipc["Descripcion"] = ipc["Descripcion"].astype(str).str.strip()
    ipc["Periodo"] = pd.to_datetime(ipc["Periodo"], errors="coerce").dt.normalize()
    ipc = ipc.dropna(subset=["Periodo"]).sort_values("Periodo")

    # =========================
    # Opciones + labels
    # =========================
    label_fix = {"B": "Bienes", "S": "Servicios"}

    sel = ipc[["Codigo_str", "Descripcion"]].drop_duplicates().copy()

    def _is_empty_desc(d: str) -> bool:
        ds = str(d).strip().lower()
        return (ds == "") or (ds == "nan") or (ds == "none")

    def build_label(code: str, desc: str) -> str:
        code = str(code).strip()
        if code.isdigit() and int(code) == 0:
            return "Nivel general"
        if not _is_empty_desc(desc):
            return str(desc).strip()
        if code in label_fix:
            return label_fix[code]
        return code

    sel["Label"] = sel.apply(lambda r: build_label(r["Codigo_str"], r["Descripcion"]), axis=1)
    sel["ord0"] = sel["Label"].apply(lambda x: 0 if _is_nivel_general(x) else 1)
    sel = sel.sort_values(["ord0", "Label"]).drop(columns=["ord0"])

    options = sel["Codigo_str"].tolist()
    code_to_label = dict(zip(sel["Codigo_str"], sel["Label"]))

    # default: Nivel general
    default_code = None
    for c, lab in code_to_label.items():
        if _is_nivel_general(lab):
            default_code = c
            break
    if default_code is None and options:
        default_code = options[0]

    # =========================
    # Panel wrap marker (JS)
    # =========================
    st.markdown("<span id='ipc_panel_marker'></span>", unsafe_allow_html=True)
    components.html(
        """
        <script>
        (function() {
          function applyPanelClass() {
            const marker = window.parent.document.getElementById('ipc_panel_marker');
            if (!marker) return;
            const block = marker.closest('div[data-testid="stVerticalBlock"]');
            if (block) block.classList.add('fx-panel-wrap');
          }
          applyPanelClass();
          let tries = 0;
          const t = setInterval(() => {
            applyPanelClass();
            tries += 1;
            if (tries >= 10) clearInterval(t);
          }, 150);

          const obs = new MutationObserver(() => applyPanelClass());
          obs.observe(window.parent.document.body, { childList: true, subtree: true });
          setTimeout(() => obs.disconnect(), 3000);
        })();
        </script>
        """,
        height=0,
    )

    # =========================
    # Negrita en dropdown para opciones clave (JS)
    # =========================
    st.markdown("<span id='ipc_bold_options_marker'></span>", unsafe_allow_html=True)
    components.html(
        """
        <script>
        (function () {
          const targets = new Set([
            "nivel general", "bienes", "estacional", "núcleo", "nucleo", "regulados", "servicios"
          ]);

          function applyBold() {
            const doc = window.parent.document;
            const opts = doc.querySelectorAll('div[role="option"]');
            if (!opts || !opts.length) return;

            opts.forEach(el => {
              const t = (el.innerText || "").trim().toLowerCase();
              // match exact, o empieza con (por si Streamlit agrega algo raro)
              if (targets.has(t) || Array.from(targets).some(k => t.startsWith(k))) {
                el.style.fontWeight = "800";
              }
            });
          }

          applyBold();
          const obs = new MutationObserver(() => applyBold());
          obs.observe(window.parent.document.body, { childList: true, subtree: true });
          setTimeout(() => obs.disconnect(), 8000);
        })();
        </script>
        """,
        height=0,
    )

    # ============================================================
    # Estado para renderizar HEADER antes de los controles
    # ============================================================
    DEFAULT_MEDIDA = "Mensual"
    DEFAULT_SELECTED = [default_code] if default_code else []

    medida_state = st.session_state.get("ipc_medida", DEFAULT_MEDIDA)
    selected_state = st.session_state.get("ipc_vars", DEFAULT_SELECTED)

    if medida_state not in ["Mensual", "Anual"]:
        medida_state = DEFAULT_MEDIDA
    if not isinstance(selected_state, (list, tuple)) or len(selected_state) == 0:
        selected_state = DEFAULT_SELECTED

    if medida_state == "Mensual":
        y_col_state = "v_m_IPC"
        medida_txt_state = "Variación mensual"
    else:
        y_col_state = "v_i_a_IPC"
        medida_txt_state = "Variación anual"

    # Header siempre basado en Nivel general si existe
    nivel_code = None
    for c, lab in code_to_label.items():
        if _is_nivel_general(lab):
            nivel_code = c
            break

    header_code = nivel_code if (nivel_code in options) else None
    if header_code is None:
        header_code = (selected_state[0] if selected_state else (default_code or options[0]))

    hdr_label = code_to_label.get(header_code, header_code)

    hdr_series = (
        ipc[ipc["Codigo_str"] == header_code]
        .dropna(subset=[y_col_state])
        .sort_values("Periodo")
    )
    if hdr_series.empty:
        st.warning("Sin datos para armar el header con esa serie.")
        return

    last_period = pd.to_datetime(hdr_series["Periodo"].iloc[-1])
    last_val = float(hdr_series[y_col_state].iloc[-1])

    # pills: mensual y anual siempre
    hdr_m = ipc[ipc["Codigo_str"] == header_code].dropna(subset=["v_m_IPC"]).sort_values("Periodo")
    hdr_a = ipc[ipc["Codigo_str"] == header_code].dropna(subset=["v_i_a_IPC"]).sort_values("Periodo")

    m_val = np.nan
    if not hdr_m.empty:
        t = hdr_m[hdr_m["Periodo"] == last_period]
        m_val = float(t["v_m_IPC"].iloc[-1]) if not t.empty else float(hdr_m["v_m_IPC"].iloc[-1])

    a_val = np.nan
    if not hdr_a.empty:
        t = hdr_a[hdr_a["Periodo"] == last_period]
        a_val = float(t["v_i_a_IPC"].iloc[-1]) if not t.empty else float(hdr_a["v_i_a_IPC"].iloc[-1])

    a_m, cls_m = _arrow_cls(m_val if pd.notna(m_val) else np.nan)
    a_a, cls_a = _arrow_cls(a_val if pd.notna(a_val) else np.nan)

    hdr_label_txt = "Nivel General" if str(hdr_label).strip().lower() == "nivel general" else hdr_label

    # =========================
    # HEADER
    # =========================
    header_lines = [
        '<div class="fx-wrap">',
        '  <div class="fx-title-row">',
        '    <div class="fx-icon-badge">🛒</div>',
        '    <div class="fx-title">IPC</div>',
        "  </div>",
        '  <div class="fx-card">',
        '    <div class="fx-row">',
        f'      <div class="fx-value">{_fmt_pct_es(last_val, 1)}%</div>',
        '      <div class="fx-meta">',
        f'        {hdr_label_txt}<span class="sep">|</span>{medida_txt_state}<span class="sep">|</span>{_mmmyy_es(last_period)}',
        "      </div>",
        '      <div class="fx-pills">',
        '        <div class="fx-pill red">',
        f'          <span class="fx-arrow {cls_m}">{a_m}</span>',
        f'          <span class="{cls_m}">{_fmt_pct_es(m_val, 1) if pd.notna(m_val) else "—"}%</span>',
        '          <span class="lab">mensual</span>',
        "        </div>",
        '        <div class="fx-pill green">',
        f'          <span class="fx-arrow {cls_a}">{a_a}</span>',
        f'          <span class="{cls_a}">{_fmt_pct_es(a_val, 1) if pd.notna(a_val) else "—"}%</span>',
        '          <span class="lab">anual</span>',
        "        </div>",
        "      </div>",
        "    </div>",
        "  </div>",
        "</div>",
    ]
    st.markdown("\n".join(header_lines), unsafe_allow_html=True)

    st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

    # =========================
    # CONTROLES
    # =========================
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
        medida = st.selectbox(
            "",
            ["Mensual", "Anual"],
            index=0 if medida_state == "Mensual" else 1,
            label_visibility="collapsed",
            key="ipc_medida",
        )

    with c2:
        st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
        selected = st.multiselect(
            "",
            options=options,
            default=list(selected_state) if selected_state else DEFAULT_SELECTED,
            format_func=lambda c: code_to_label.get(c, c),
            label_visibility="collapsed",
            key="ipc_vars",
        )

    if not selected:
        st.info("Seleccioná al menos una categoría.")
        return

    if medida == "Mensual":
        y_col = "v_m_IPC"
        y_axis_label = "Variación mensual (%)"
    else:
        y_col = "v_i_a_IPC"
        y_axis_label = "Variación anual (%)"

    # =========================
    # Rango de fechas (MES A MES)
    # =========================
    df_sel = ipc[ipc["Codigo_str"].isin(selected)].copy()
    df_sel = df_sel.dropna(subset=[y_col])

    if df_sel.empty:
        st.warning("No hay datos para las selecciones / medida elegida.")
        return

    min_dt = pd.to_datetime(df_sel["Periodo"].min())
    max_dt = pd.to_datetime(df_sel["Periodo"].max())
    min_m = min_dt.to_period("M").to_timestamp(how="start")
    max_m = max_dt.to_period("M").to_timestamp(how="start")

    months = pd.date_range(min_m, max_m, freq="MS")
    if len(months) < 2:
        st.warning("Rango insuficiente para armar selector mensual.")
        return

    default_start = months[max(0, len(months) - 24)]
    default_end = months[-1]

    st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)

    start_m, end_m = st.select_slider(
        "",
        options=list(months),
        value=(default_start, default_end),
        format_func=lambda d: _mmmyy_es(d),  # si querés 01/23: _mmmyy_num(d)
        label_visibility="collapsed",
        key="ipc_range_month",
    )

    start_m = pd.to_datetime(start_m).normalize()
    end_m = pd.to_datetime(end_m).normalize()
    end_exclusive = end_m + pd.DateOffset(months=1)

    df_plot = df_sel[(df_sel["Periodo"] >= start_m) & (df_sel["Periodo"] < end_exclusive)].copy()
    if df_plot.empty:
        st.warning("No hay datos en el rango seleccionado.")
        return

    # =========================
    # Gráfico — ticks adaptativos + hover sin fecha duplicada
    # =========================
    x_min = start_m
    x_max = end_m + pd.DateOffset(months=1)

    all_ticks = pd.date_range(x_min, x_max, freq="MS")
    n_months = len(all_ticks)
    step = _tick_step_from_months(n_months)

    tickvals = list(all_ticks[::step])
    ticktext = [_mmmyy_es(d) for d in tickvals]  # o _mmmyy_num(d)

    fig = go.Figure()

    # Nivel general primero si está seleccionado
    selected_sorted = list(selected)
    if nivel_code in selected_sorted:
        selected_sorted = [nivel_code] + [c for c in selected_sorted if c != nivel_code]

    for c in selected_sorted:
        s = df_plot[df_plot["Codigo_str"] == c].dropna(subset=[y_col]).sort_values("Periodo")
        if s.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=s["Periodo"],
                y=s[y_col],
                name=code_to_label.get(c, c),
                mode="lines+markers",
                marker=dict(size=5),
                # Evita duplicación: el encabezado del unified hover ya pone la fecha
                hovertemplate="%{y:.1f}%<extra></extra>",
            )
        )

    fig.update_layout(
        hovermode="x unified",
        height=520,
        margin=dict(l=10, r=20, t=10, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1.0),
        dragmode=False,
    )
    fig.update_yaxes(title_text=y_axis_label, ticksuffix="%", fixedrange=False)
    fig.update_xaxes(
        title_text="",
        range=[x_min, x_max],
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
        tickangle=-90 if n_months >= 36 else 0,
        fixedrange=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
    )

    # =========================
    # MODAL: Tabla de datos (Año + Frecuencia) — sin años vacíos (ej: 2016)
    # =========================
    @st.dialog("📋 Tabla de datos (IPC Nacional)")
    def _tabla_modal():
        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:-4px;'>"
            "Cobertura nacional – INDEC"
            "</div>",
            unsafe_allow_html=True,
        )

        tab_base = ipc.copy()
        tab_base["Year"] = tab_base["Periodo"].dt.year
        tab_base["Month"] = tab_base["Periodo"].dt.month

        # Años con al menos algún dato mensual o anual (así se va 2016 si está vacío)
        years = (
            tab_base.dropna(subset=["v_m_IPC", "v_i_a_IPC"], how="all")["Year"]
            .dropna()
            .unique()
        )
        years = sorted(list(years), reverse=True)

        if not years:
            st.info("No hay datos suficientes.")
            return

        cA, cB = st.columns(2)
        with cA:
            y_sel = st.selectbox("Año", years, index=0, key="ipc_modal_year")
        with cB:
            freq_sel = st.selectbox("Frecuencia", ["Mensual", "Anual"], index=0, key="ipc_modal_freq")

        label_fix2 = {"B": "Bienes", "S": "Servicios"}

        def _is_empty_desc2(d):
            d = str(d).strip().lower()
            return d in ["", "nan", "none"]

        def build_label2(code, desc):
            code = str(code).strip()
            if code.isdigit() and int(code) == 0:
                return "Nivel general"
            if not _is_empty_desc2(desc):
                return str(desc).strip()
            if code in label_fix2:
                return label_fix2[code]
            return code

        tb = tab_base[tab_base["Year"] == y_sel].copy()
        tb["Label"] = tb.apply(lambda r: build_label2(r["Codigo_str"], r["Descripcion"]), axis=1)

        categorias = {"Bienes", "Servicios", "Núcleo", "Regulados", "Estacional"}

        def sort_key(x):
            if str(x).strip().lower() == "nivel general":
                return (0, str(x))
            if x in categorias:
                return (1, str(x))
            return (2, str(x))

        def fmt(v):
            if pd.isna(v):
                return "-"
            return f"{float(v):.1f}%".replace(".", ",")

        if freq_sel == "Mensual":
            tb = tb.dropna(subset=["Periodo", "v_m_IPC"]).copy()
            if tb.empty:
                st.info("No hay datos mensuales para ese año.")
                return

            piv = (
                tb.pivot_table(index="Label", columns="Month", values="v_m_IPC", aggfunc="last")
                .reindex(columns=range(1, 13))
            )

            month_map = {
                1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
                7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
            }
            piv.columns = [month_map[m] for m in piv.columns]
            piv = piv.loc[sorted(piv.index, key=sort_key)]
            piv_fmt = piv.applymap(fmt)

        else:
            tb = tb.dropna(subset=["Periodo", "v_i_a_IPC"]).copy()
            if tb.empty:
                st.info("No hay datos anuales para ese año.")
                return

            # Último dato disponible del año por categoría (normalmente dic)
            last_by_label = (
                tb.sort_values("Periodo")
                  .groupby("Label", as_index=True)
                  .tail(1)
                  .set_index("Label")[["v_i_a_IPC"]]
                  .rename(columns={"v_i_a_IPC": "Anual"})
            )

            last_by_label = last_by_label.loc[sorted(last_by_label.index, key=sort_key)]
            piv_fmt = last_by_label.applymap(fmt)

        def style_rows(df):
            styles = []
            for idx in df.index:
                if str(idx).strip().lower() == "nivel general":
                    styles.append(["font-weight:800; background-color:rgba(17,24,39,0.06)"] * df.shape[1])
                elif idx in categorias:
                    styles.append(["font-weight:800; background-color:rgba(17,24,39,0.10)"] * df.shape[1])
                else:
                    styles.append([""] * df.shape[1])
            return pd.DataFrame(styles, index=df.index, columns=df.columns)

        st.dataframe(
            piv_fmt.style.apply(style_rows, axis=None),
            use_container_width=True,
            height=520,
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:8px;'>Fuente: INDEC.</div>",
            unsafe_allow_html=True,
        )

    # =========================
    # Acciones: solo Tabla de datos
    # =========================
    c_btn, c_sp = st.columns([2, 8])
    with c_btn:
        if st.button("📋 Tabla de datos", use_container_width=True, key="ipc_open_table"):
            _tabla_modal()

    st.markdown(
        "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:6px;'>Fuente: INDEC.</div>",
        unsafe_allow_html=True,
    )



    # =========================================================
    # IPIM (INDEC) — BLOQUE SIMPLE (como IPC) + SELECTORES DEPENDIENTES
    # Medida: Mensual/Anual (calculada desde indice_ipim)
    # Variable principal: Nivel general / Productos nacionales / Productos importados
    # Si Variable = Nacional -> selector 3: Primarios / Industria(manufacturados) / Energía
    # Si selector 3 = Industria -> selector 4: multiselect (Nivel general industria + 15..36)
    # HEADER FIJO: SIEMPRE Nivel general (último dato)
    # =========================================================
    st.divider()

    import io
    import re
    import requests
    import streamlit.components.v1 as st_components  # <-- FIX: no usar "components"

    IPIM_URL = "https://www.indec.gob.ar/ftp/cuadros/economia/indice_ipim.csv"

    @st.cache_data(ttl=12 * 60 * 60)
    def _load_ipim_simple() -> pd.DataFrame:
        r = requests.get(IPIM_URL, timeout=60)
        r.raise_for_status()
        raw = r.content

        df = None
        for sep in [";", ",", "\t"]:
            try:
                tmp = pd.read_csv(io.BytesIO(raw), sep=sep, engine="python")
                if tmp is None or tmp.empty:
                    continue
                cols = [c.strip().lower() for c in tmp.columns]
                ok_period = "periodo" in cols
                ok_ap = "nivel_general_aperturas" in cols
                ok_ind = "indice_ipim" in cols
                if ok_period and ok_ap and ok_ind:
                    df = tmp
                    break
            except Exception:
                continue

        if df is None or df.empty:
            return pd.DataFrame()

        out = df[["periodo", "nivel_general_aperturas", "indice_ipim"]].copy()
        out = out.rename(
            columns={
                "periodo": "Periodo_raw",
                "nivel_general_aperturas": "Apertura_raw",
                "indice_ipim": "Indice_raw",
            }
        )

        # --- Apertura limpia (minúsculas + underscores) ---
        out["Apertura"] = (
            out["Apertura_raw"]
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace("\u00a0", " ", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(" ", "_", regex=False)
            .str.replace("__", "_", regex=False)
        )

        # --- Periodo: viene ISO 'YYYY-MM-DD' -> NO dayfirst ---
        s_per = out["Periodo_raw"].astype(str).str.strip()
        per = pd.to_datetime(s_per, format="%Y-%m-%d", errors="coerce")
        out["Periodo"] = per.dt.to_period("M").dt.to_timestamp(how="start")

        # --- Índice numérico robusto (coma decimal) ---
        s = out["Indice_raw"].astype(str).str.strip()
        s = s.str.replace("\u00a0", " ", regex=False).str.replace(" ", "", regex=False)

        has_comma = s.str.contains(",", na=False)
        s.loc[has_comma] = s.loc[has_comma].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)

        out["Indice"] = pd.to_numeric(s, errors="coerce")

        out = out.dropna(subset=["Periodo", "Apertura", "Indice"]).sort_values("Periodo").reset_index(drop=True)
        return out


    # -------------------------
    # Load
    # -------------------------
    ipim = _load_ipim_simple()
    if ipim.empty:
        st.warning("No se pudo cargar IPIM (INDEC).")
        st.stop()


    # -------------------------
    # Catálogos (labels)
    # -------------------------
    SERIES_TOP = {
        "ng_nivel_general": "Nivel general",
        "n_productos_nacionales": "Productos nacionales",
        "i_productos_importados": "Productos importados",
    }

    # Selector 3 (solo si top = nacionales)
    SERIES_NAC = {
        "1_primarios": "Primarios",
        "d_productos_manufacturados": "Industria (manufacturados)",
        "e_energia_electrica": "Energía eléctrica",
    }

    # Para selector 4: nivel general industria + 15_...36_ (solo 2 dígitos)
    def _is_2digit_industry(code: str) -> bool:
        return bool(re.match(r"^\d{2}_", str(code)))

    def _industry_2digit_codes(df: pd.DataFrame) -> list[str]:
        codes = sorted({c for c in df["Apertura"].unique() if _is_2digit_industry(c)})
        out = []
        for c in codes:
            try:
                n = int(str(c)[:2])
                if 15 <= n <= 36:
                    out.append(c)
            except Exception:
                continue
        return out

    def _pretty_industry_label(code: str) -> str:
        # 15_alimentos_y_bebidas -> "Alimentos y bebidas"
        s = str(code)
        rest = s[3:].replace("_", " ").strip()
        rest = rest[:1].upper() + rest[1:] if rest else rest
        return rest


    # -------------------------
    # Métricas (para TODAS las aperturas)
    # -------------------------
    ipim = ipim.sort_values(["Apertura", "Periodo"]).copy()
    ipim["v_m"] = ipim.groupby("Apertura")["Indice"].pct_change(1) * 100
    ipim["v_i_a"] = ipim.groupby("Apertura")["Indice"].pct_change(12) * 100


    # -------------------------
    # Session state defaults
    # -------------------------
    if "ipim_medida_simple" not in st.session_state:
        st.session_state["ipim_medida_simple"] = "Mensual"
    if "ipim_var_simple" not in st.session_state:
        st.session_state["ipim_var_simple"] = "ng_nivel_general"

    # nuevos selectores
    if "ipim_nac_group" not in st.session_state:
        st.session_state["ipim_nac_group"] = "d_productos_manufacturados"  # default industria

    # selector 4: MULTI
    if "ipim_industry_multi" not in st.session_state:
        st.session_state["ipim_industry_multi"] = ["__nivel_general_industria__"]


    # -------------------------
    # estilos (selector azul como IPC)
    # -------------------------
    st.markdown("<span id='ipim_panel_marker'></span>", unsafe_allow_html=True)
    st_components.html(
        """
        <script>
        (function() {
        function applyPanelClass() {
            const marker = window.parent.document.getElementById('ipim_panel_marker');
            if (!marker) return;
            const block = marker.closest('div[data-testid="stVerticalBlock"]');
            if (block) block.classList.add('fx-panel-wrap');
        }
        applyPanelClass();
        let tries = 0;
        const t = setInterval(() => {
            applyPanelClass();
            tries += 1;
            if (tries >= 10) clearInterval(t);
        }, 150);

        const obs = new MutationObserver(() => applyPanelClass());
        obs.observe(window.parent.document.body, { childList: true, subtree: true });
        setTimeout(() => obs.disconnect(), 3000);
        })();
        </script>
        """,
        height=0,
    )


    # =========================
    # HEADER FIJO (Nivel general)
    # =========================
    HEADER_CODE = "ng_nivel_general"
    medida_state = st.session_state.get("ipim_medida_simple", "Mensual")
    if medida_state not in ["Mensual", "Anual"]:
        medida_state = "Mensual"

    y_col_hdr = "v_m" if medida_state == "Mensual" else "v_i_a"
    medida_txt_state = "Variación mensual" if medida_state == "Mensual" else "Variación anual"

    hdr = ipim[ipim["Apertura"] == HEADER_CODE].dropna(subset=[y_col_hdr]).sort_values("Periodo")
    if hdr.empty:
        st.warning("IPIM: sin datos para armar el header (Nivel general).")
        st.stop()

    last_period = pd.to_datetime(hdr["Periodo"].iloc[-1])
    last_val = float(hdr[y_col_hdr].iloc[-1])

    at = ipim[ipim["Apertura"] == HEADER_CODE].sort_values("Periodo")
    m_val = at.loc[at["Periodo"] == last_period, "v_m"]
    a_val = at.loc[at["Periodo"] == last_period, "v_i_a"]
    m_val = float(m_val.iloc[0]) if (not m_val.empty and pd.notna(m_val.iloc[0])) else np.nan
    a_val = float(a_val.iloc[0]) if (not a_val.empty and pd.notna(a_val.iloc[0])) else np.nan

    a_m, cls_m = _arrow_cls(m_val if pd.notna(m_val) else np.nan)
    a_a, cls_a = _arrow_cls(a_val if pd.notna(a_val) else np.nan)

    header_lines = [
        '<div class="fx-wrap">',
        '  <div class="fx-title-row">',
        '    <div class="fx-icon-badge">🏭</div>',
        '    <div class="fx-title">IPIM</div>',
        "  </div>",
        '  <div class="fx-card">',
        '    <div class="fx-row">',
        f'      <div class="fx-value">{_fmt_pct_es(last_val, 1)}%</div>',
        '      <div class="fx-meta">',
        f'        Nivel general<span class="sep">|</span>{medida_txt_state}<span class="sep">|</span>{_mmmyy_es(last_period)}',
        "      </div>",
        '      <div class="fx-pills">',
        '        <div class="fx-pill red">',
        f'          <span class="fx-arrow {cls_m}">{a_m}</span>',
        f'          <span class="{cls_m}">{_fmt_pct_es(m_val, 1) if pd.notna(m_val) else "—"}%</span>',
        '          <span class="lab">mensual</span>',
        "        </div>",
        '        <div class="fx-pill green">',
        f'          <span class="fx-arrow {cls_a}">{a_a}</span>',
        f'          <span class="{cls_a}">{_fmt_pct_es(a_val, 1) if pd.notna(a_val) else "—"}%</span>',
        '          <span class="lab">anual</span>',
        "        </div>",
        "      </div>",
        "    </div>",
        "  </div>",
        "</div>",
    ]
    st.markdown("\n".join(header_lines), unsafe_allow_html=True)
    st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)


    # =========================
    # CONTROLES (fila 1)
    # =========================
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
        st.selectbox(
            "",
            ["Mensual", "Anual"],
            index=0 if medida_state == "Mensual" else 1,
            label_visibility="collapsed",
            key="ipim_medida_simple",
        )

    with c2:
        st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
        vars_codes = list(SERIES_TOP.keys())
        var_state = st.session_state.get("ipim_var_simple", "ng_nivel_general")
        if var_state not in SERIES_TOP:
            var_state = "ng_nivel_general"

        st.selectbox(
            "",
            vars_codes,
            index=vars_codes.index(var_state),
            format_func=lambda c: SERIES_TOP.get(c, c),
            label_visibility="collapsed",
            key="ipim_var_simple",
        )


    # =========================
    # CONTROLES (fila 2: dependientes)
    # =========================
    c3, c4 = st.columns(2, gap="large")

    medida_now = st.session_state["ipim_medida_simple"]
    var_now = st.session_state["ipim_var_simple"]

    final_code = var_now  # puede ser str o list[str]

    with c3:
        if var_now == "n_productos_nacionales":
            st.markdown("<div class='fx-panel-title'>Apertura (nacionales)</div>", unsafe_allow_html=True)

            nac_state = st.session_state.get("ipim_nac_group", "d_productos_manufacturados")
            if nac_state not in SERIES_NAC:
                nac_state = "d_productos_manufacturados"
                st.session_state["ipim_nac_group"] = nac_state

            nac_codes = list(SERIES_NAC.keys())
            st.selectbox(
                "",
                nac_codes,
                index=nac_codes.index(nac_state),
                format_func=lambda c: SERIES_NAC.get(c, c),
                label_visibility="collapsed",
                key="ipim_nac_group",
            )

            nac_now = st.session_state["ipim_nac_group"]
            final_code = nac_now

    with c4:
        if var_now == "n_productos_nacionales" and st.session_state.get("ipim_nac_group") == "d_productos_manufacturados":
            st.markdown("<div class='fx-panel-title'>Industria (manufacturados)</div>", unsafe_allow_html=True)

            ind2 = _industry_2digit_codes(ipim)
            ind_options = ["__nivel_general_industria__"] + ind2

            # limpiar selección actual según opciones vigentes
            cur_sel = st.session_state.get("ipim_industry_multi", ["__nivel_general_industria__"])
            cur_sel = [x for x in cur_sel if x in ind_options]
            if not cur_sel:
                cur_sel = ["__nivel_general_industria__"]
            st.session_state["ipim_industry_multi"] = cur_sel

            st.multiselect(
                "",
                ind_options,
                format_func=lambda c: ("Nivel general (industria)" if c == "__nivel_general_industria__" else _pretty_industry_label(c)),
                label_visibility="collapsed",
                key="ipim_industry_multi",
            )

            sel = st.session_state.get("ipim_industry_multi", ["__nivel_general_industria__"])
            final_code = ["d_productos_manufacturados" if x == "__nivel_general_industria__" else x for x in sel]


    # =========================
    # RANGO + GRÁFICO (según selección final_code)
    # =========================
    y_col = "v_m" if medida_now == "Mensual" else "v_i_a"
    y_axis_label = "Variación mensual (%)" if medida_now == "Mensual" else "Variación anual (%)"

    codes_to_plot = final_code if isinstance(final_code, list) else [final_code]

    df_sel = ipim[ipim["Apertura"].isin(codes_to_plot)].dropna(subset=[y_col]).copy()
    if df_sel.empty:
        st.info("No hay datos para esa selección / medida.")
        st.stop()

    min_dt = pd.to_datetime(df_sel["Periodo"].min()).to_period("M").to_timestamp(how="start")
    max_dt = pd.to_datetime(df_sel["Periodo"].max()).to_period("M").to_timestamp(how="start")

    months = pd.date_range(min_dt, max_dt, freq="MS")
    if len(months) < 2:
        st.warning("Rango insuficiente para armar selector mensual.")
        st.stop()

    default_start = months[max(0, len(months) - 24)]
    default_end = months[-1]

    st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)

    start_m, end_m = st.select_slider(
        "",
        options=list(months),
        value=(default_start, default_end),
        format_func=lambda d: _mmmyy_es(d),
        label_visibility="collapsed",
        key="ipim_range_months_simple",
    )

    start_m = pd.to_datetime(start_m).normalize()
    end_m = pd.to_datetime(end_m).normalize()
    end_exclusive = end_m + pd.DateOffset(months=1)

    x_min = start_m
    x_max = end_m + pd.DateOffset(months=1)

    all_ticks = pd.date_range(x_min, x_max, freq="MS")
    n_months = len(all_ticks)
    step = _tick_step_from_months(n_months)

    tickvals = list(all_ticks[::step])
    ticktext = [_mmmyy_es(d) for d in tickvals]

    def _final_label(code: str) -> str:
        if code in SERIES_TOP:
            return SERIES_TOP[code]
        if code in SERIES_NAC:
            return SERIES_NAC[code]
        if code == "d_productos_manufacturados":
            return "Nivel general (industria)"
        if _is_2digit_industry(code):
            return _pretty_industry_label(code)
        return code

    fig = go.Figure()

    for code in codes_to_plot:
        df_one = ipim[ipim["Apertura"] == code].dropna(subset=[y_col]).copy()
        if df_one.empty:
            continue

        df_one = df_one[(df_one["Periodo"] >= start_m) & (df_one["Periodo"] < end_exclusive)].copy()
        if df_one.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=df_one["Periodo"],
                y=df_one[y_col],
                name=_final_label(code),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate="%{y:.1f}%<extra></extra>",
            )
        )

    if len(fig.data) == 0:
        st.warning("No hay datos en el rango seleccionado.")
        st.stop()

    fig.update_layout(
        hovermode="x unified",
        height=520,
        margin=dict(l=10, r=10, t=10, b=60),  # r más chico para no “reservar” espacio
        showlegend=(len(codes_to_plot) > 1),
        dragmode=False,
        legend=dict(
            x=0.99,
            y=0.99,
            xanchor="right",
            yanchor="top",
            orientation="v",
            bgcolor="rgba(255,255,255,0.0)",
            borderwidth=0,
            itemsizing="constant",
        ),
    )


    fig.update_yaxes(title_text=y_axis_label, ticksuffix="%", fixedrange=False)
    fig.update_xaxes(
        title_text="",
        range=[x_min, x_max],
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
        tickangle=-90 if n_months >= 36 else 0,
        fixedrange=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
        key="ipim_simple_chart",
    )

    st.markdown(
        "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:6px;'>Fuente: INDEC.</div>",
        unsafe_allow_html=True,
    )











    # TABLA DE DATOS#######
    @st.dialog("📋 Tabla de datos (IPIM)")
    def _tabla_ipim_modal():
        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:-4px;'>"
            "Cobertura nacional – INDEC"
            "</div>",
            unsafe_allow_html=True,
        )

        tab_base = ipim.copy()
        tab_base["Year"] = tab_base["Periodo"].dt.year
        tab_base["Month"] = tab_base["Periodo"].dt.month

        # -------------------------
        # Defaults modal (keys propias)
        # -------------------------
        if "ipim_tbl_var_top" not in st.session_state:
            st.session_state["ipim_tbl_var_top"] = "ng_nivel_general"
        if "ipim_tbl_nac_group" not in st.session_state:
            st.session_state["ipim_tbl_nac_group"] = "d_productos_manufacturados"
        if "ipim_tbl_freq" not in st.session_state:
            st.session_state["ipim_tbl_freq"] = "Anual"

        # -------------------------
        # Selectores (Variable + Frecuencia)
        # -------------------------
        t1, t2 = st.columns(2, gap="large")

        with t1:
            var_top_codes = list(SERIES_TOP.keys())
            cur_top = st.session_state["ipim_tbl_var_top"]
            if cur_top not in SERIES_TOP:
                cur_top = "ng_nivel_general"
                st.session_state["ipim_tbl_var_top"] = cur_top

            st.selectbox(
                "Variable",
                var_top_codes,
                index=var_top_codes.index(cur_top),
                format_func=lambda c: SERIES_TOP.get(c, c),
                key="ipim_tbl_var_top",
            )

        with t2:
            st.selectbox(
                "Frecuencia",
                ["Mensual", "Anual"],
                key="ipim_tbl_freq",
            )

        modal_top = st.session_state["ipim_tbl_var_top"]
        modal_final_group = modal_top
        freq_sel = st.session_state["ipim_tbl_freq"]

        # selector 2 (solo si Nacionales)
        if modal_top == "n_productos_nacionales":
            nac_codes = list(SERIES_NAC.keys())
            cur_nac = st.session_state["ipim_tbl_nac_group"]
            if cur_nac not in SERIES_NAC:
                cur_nac = "d_productos_manufacturados"
                st.session_state["ipim_tbl_nac_group"] = cur_nac

            st.selectbox(
                "Apertura (nacionales)",
                nac_codes,
                index=nac_codes.index(cur_nac),
                format_func=lambda c: SERIES_NAC.get(c, c),
                key="ipim_tbl_nac_group",
            )
            modal_final_group = st.session_state["ipim_tbl_nac_group"]

        # -------------------------
        # helpers formato
        # -------------------------
        def fmt(v):
            if pd.isna(v):
                return "-"
            return f"{float(v):.1f}%".replace(".", ",")

        # ======================================================
        # CASO ESPECIAL: Nacionales → Industria (manufacturados)
        # ======================================================
        if modal_top == "n_productos_nacionales" and modal_final_group == "d_productos_manufacturados":
            ind2 = _industry_2digit_codes(tab_base)
            codes = ["d_productos_manufacturados"] + ind2

            df = tab_base[tab_base["Apertura"].isin(codes)].copy()

            if freq_sel == "Mensual":
                df = df.dropna(subset=["Periodo", "v_m"]).sort_values(["Apertura", "Periodo"])
                if df.empty:
                    st.info("No hay datos mensuales para industria (manufacturados).")
                    return

                piv = df.pivot_table(
                    index="Apertura",
                    columns="Periodo",
                    values="v_m",
                    aggfunc="last",
                )
                piv = piv.reindex(sorted(piv.columns), axis=1)

                row_labels = []
                for c in piv.index:
                    if c == "d_productos_manufacturados":
                        row_labels.append("Nivel general (industria)")
                    elif _is_2digit_industry(c):
                        row_labels.append(_pretty_industry_label(c))
                    else:
                        row_labels.append(str(c))
                piv.index = row_labels

                piv.columns = [_mmmyy_es(pd.to_datetime(c)) for c in piv.columns]
                piv_fmt = piv.applymap(fmt)

                def style_rows(df_):
                    styles = []
                    for idx in df_.index:
                        if str(idx).strip().lower() == "nivel general (industria)":
                            styles.append(
                                ["font-weight:800; background-color:rgba(17,24,39,0.06)"] * df_.shape[1]
                            )
                        else:
                            styles.append([""] * df_.shape[1])
                    return pd.DataFrame(styles, index=df_.index, columns=df_.columns)

                st.dataframe(
                    piv_fmt.style.apply(style_rows, axis=None),
                    use_container_width=True,
                    height=520,
                )

            else:
                df = df.dropna(subset=["Periodo", "v_i_a"]).sort_values(["Apertura", "Periodo"])
                if df.empty:
                    st.info("No hay datos anuales para industria (manufacturados).")
                    return

                last_by_year = df.groupby(["Apertura", "Year"], as_index=False).tail(1)

                piv = last_by_year.pivot_table(
                    index="Apertura",
                    columns="Year",
                    values="v_i_a",
                    aggfunc="last",
                )
                piv = piv.reindex(sorted(piv.columns), axis=1)

                row_labels = []
                for c in piv.index:
                    if c == "d_productos_manufacturados":
                        row_labels.append("Nivel general (industria)")
                    elif _is_2digit_industry(c):
                        row_labels.append(_pretty_industry_label(c))
                    else:
                        row_labels.append(str(c))
                piv.index = row_labels

                piv_fmt = piv.applymap(fmt)

                def style_rows(df_):
                    styles = []
                    for idx in df_.index:
                        if str(idx).strip().lower() == "nivel general (industria)":
                            styles.append(
                                ["font-weight:800; background-color:rgba(17,24,39,0.06)"] * df_.shape[1]
                            )
                        else:
                            styles.append([""] * df_.shape[1])
                    return pd.DataFrame(styles, index=df_.index, columns=df_.columns)

                st.dataframe(
                    piv_fmt,
                    use_container_width=True,
                    height=520,
                )

            st.markdown(
                "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:8px;'>Fuente: INDEC.</div>",
                unsafe_allow_html=True,
            )
            return

        # ======================================================
        # RESTO DE CASOS
        # ======================================================
        df = tab_base[tab_base["Apertura"] == modal_final_group].copy()
        serie_label = _final_label(modal_final_group) if "_final_label" in globals() else str(modal_final_group)

        if freq_sel == "Mensual":
            df = df.dropna(subset=["Periodo", "v_m"]).sort_values("Periodo")
            if df.empty:
                st.info("No hay datos mensuales para esa selección.")
                return

            piv = df.pivot_table(index=None, columns="Periodo", values="v_m", aggfunc="last")
            piv = piv.reindex(sorted(piv.columns), axis=1)
            piv.index = [serie_label]
            piv.columns = [_mmmyy_es(pd.to_datetime(c)) for c in piv.columns]

            st.dataframe(piv.applymap(fmt), use_container_width=True, height=220)

        else:
            df = df.dropna(subset=["Periodo", "v_i_a"]).sort_values("Periodo")
            if df.empty:
                st.info("No hay datos anuales para esa selección.")
                return

            last_by_year = df.groupby("Year", as_index=False).tail(1)
            piv = last_by_year.pivot_table(index=None, columns="Year", values="v_i_a", aggfunc="last")
            piv = piv.reindex(sorted(piv.columns), axis=1)
            piv.index = [serie_label]

            st.dataframe(piv.applymap(fmt), use_container_width=True, height=200)

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:8px;'>Fuente: INDEC.</div>",
            unsafe_allow_html=True,
        )


    # =========================
    # BOTÓN (FUERA DEL MODAL)
    # =========================
    c_btn, c_sp = st.columns([2, 8])
    with c_btn:
        if st.button("📋 Tabla de datos", use_container_width=True, key="ipim_open_table"):
            _tabla_ipim_modal()




