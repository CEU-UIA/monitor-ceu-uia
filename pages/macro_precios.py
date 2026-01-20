import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_ipc_indec_full


def _fmt_pct_es(x: float, dec: int = 1) -> str:
    if x is None or pd.isna(x):
        return "-"
    return f"{x:.{dec}f}".replace(".", ",")


def _fmt_mes_es(dt: pd.Timestamp) -> str:
    mes_es = {
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
    }
    dt = pd.to_datetime(dt)
    return f"{mes_es[dt.month]}-{str(dt.year)[-2:]}"


def render_macro_precios(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 🛒 Precios")
    st.caption("Tasa mensual de inflación - % Nacional")
    st.divider()

    # --- CSS para que el selector sea más visible y no ocupe TODO el ancho ---
    st.markdown(
        """
        <style>
          /* caja del multiselect */
          div[data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid rgba(17,24,39,0.18) !important;
            border-radius: 10px !important;
          }
          /* ancho "razonable" del select */
          .ipc-select-wrap { max-width: 520px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    ipc = get_ipc_indec_full()
    ipc = ipc[ipc["Region"] == "Nacional"].copy()
    if ipc.empty:
        st.warning("Sin datos IPC.")
        return

    # normalización básica
    ipc = ipc.dropna(subset=["Periodo"]).copy()
    ipc["Periodo"] = pd.to_datetime(ipc["Periodo"], errors="coerce")
    ipc = ipc.dropna(subset=["Periodo"]).sort_values("Periodo")

    # Opciones / default
    opciones = sorted(ipc["Descripcion"].dropna().unique().tolist())
    default = ["Nivel general"] if "Nivel general" in opciones else (opciones[:1] if opciones else [])

    st.markdown("<div class='ipc-select-wrap'>", unsafe_allow_html=True)
    descs = st.multiselect("Seleccioná una o más divisiones", opciones, default=default)
    st.markdown("</div>", unsafe_allow_html=True)

    if not descs:
        st.info("Seleccioná al menos una división.")
        return

    # Último periodo disponible (para KPI / títulos)
    last_period = pd.to_datetime(ipc["Periodo"].max())
    last_period_label = _fmt_mes_es(last_period)

    # Serie IPC general (para el título cuando hay múltiples)
    gen_last_m = None
    gen_row = ipc[(ipc["Descripcion"] == "Nivel general") & (ipc["Periodo"] == last_period)]
    if not gen_row.empty and pd.notna(gen_row["v_m_IPC"].iloc[0]):
        gen_last_m = float(gen_row["v_m_IPC"].iloc[0])

    # Datos para KPI: tomamos la PRIMER división seleccionada para el KPI
    primary_desc = descs[0]
    serie_kpi = ipc[(ipc["Descripcion"] == primary_desc) & (ipc["Periodo"] == last_period)].copy()

    # si justo la división no tiene dato en el último mes, caemos al último disponible
    if serie_kpi.empty:
        s_tmp = ipc[ipc["Descripcion"] == primary_desc].dropna(subset=["v_m_IPC"]).sort_values("Periodo")
        if s_tmp.empty:
            st.warning("Sin serie para esa división.")
            return
        last_period = pd.to_datetime(s_tmp["Periodo"].iloc[-1])
        last_period_label = _fmt_mes_es(last_period)
        serie_kpi = s_tmp[s_tmp["Periodo"] == last_period].copy()

    last_m = float(serie_kpi["v_m_IPC"].iloc[0]) if pd.notna(serie_kpi["v_m_IPC"].iloc[0]) else None
    last_yoy = float(serie_kpi["v_i_a_IPC"].iloc[0]) if pd.notna(serie_kpi.get("v_i_a_IPC", pd.Series([None])).iloc[0]) else None

    # Layout
    c1, c2 = st.columns([1, 3], vertical_alignment="top")

    # KPI
    with c1:
        st.markdown(
            f"""
            <div style="font-size:46px; font-weight:800; line-height:1.0;">
              {_fmt_pct_es(last_m, 1)}% <span style="font-size:16px; font-weight:700;">mensual</span> {last_period_label}
            </div>
            <div style="margin-top:10px; font-size:18px;">
              <b>{_fmt_pct_es(last_yoy, 1)}% YoY</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Gráfico
    with c2:
        # Título dinámico
        if len(descs) == 1:
            title_txt = f"La inflación de {primary_desc} de {last_period_label} fue {_fmt_pct_es(last_m, 1)}%"
        else:
            # si no hay nivel general, usamos la división primaria como fallback
            if gen_last_m is None:
                title_txt = f"{primary_desc}: {_fmt_pct_es(last_m, 1)}% mensual ({last_period_label})"
            else:
                title_txt = f"IPC general: {_fmt_pct_es(gen_last_m, 1)}% mensual ({last_period_label})"

        fig = go.Figure()

        # Trazas (una por división)
        for d in descs:
            s = (
                ipc[ipc["Descripcion"] == d]
                .dropna(subset=["v_m_IPC"])
                .sort_values("Periodo")
                .copy()
            )
            if s.empty:
                continue

            fig.add_trace(
                go.Scatter(
                    x=s["Periodo"],
                    y=s["v_m_IPC"],
                    name=d,
                    mode="lines",
                    hovertemplate="%{x|%b-%y}<br>%{y:.1f}%<extra></extra>",
                )
            )

        # 1 mes libre a la derecha
        min_date = pd.to_datetime(ipc["Periodo"].min())
        max_date = pd.to_datetime(last_period) + pd.DateOffset(months=1)

        # Eje X en español (ticks manuales)
        mes_es = {
            1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
        }
        tickvals = pd.date_range(min_date.normalize(), max_date.normalize(), freq="6MS")
        if len(tickvals) < 4:
            tickvals = pd.date_range(min_date.normalize(), max_date.normalize(), freq="3MS")
        ticktext = [f"{mes_es[t.month]}-{str(t.year)[-2:]}" for t in tickvals]

        # Selector de período SIN mini-gráfico (rangeselector)
        fig.update_xaxes(
            title_text="",
            range=[min_date, max_date],
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            rangeselector=dict(
                buttons=[
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1A", step="year", stepmode="backward"),
                    dict(count=2, label="2A", step="year", stepmode="backward"),
                    dict(step="all", label="Todo"),
                ]
            ),
        )

        fig.update_layout(
            hovermode="x unified",
            height=450,
            margin=dict(l=10, r=10, t=70, b=60),
            title=dict(text=title_txt, x=0, xanchor="left"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        fig.update_yaxes(title_text="Variación mensual (%)", ticksuffix="%")

        st.plotly_chart(fig, use_container_width=True)

        # Fuente
        st.markdown(
            "<div style='color:#6b7280; font-size:12px; margin-top:6px;'>Fuente: INDEC</div>",
            unsafe_allow_html=True,
        )

        # Descargar CSV (series seleccionadas)
        out = ipc[ipc["Descripcion"].isin(descs)][["Periodo", "Descripcion", "v_m_IPC", "v_i_a_IPC"]].copy()
        out = out.rename(columns={"Periodo": "periodo", "Descripcion": "division", "v_m_IPC": "v_m", "v_i_a_IPC": "yoy"})
        out = out.sort_values(["division", "periodo"])
        csv_bytes = out.to_csv(index=False).encode("utf-8")
        file_name = f"ipc_{last_period.strftime('%Y-%m')}.csv"

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv_bytes,
            file_name=file_name,
            mime="text/csv",
            use_container_width=False,
        )
