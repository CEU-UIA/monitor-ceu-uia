import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_ipc_indec_full


def _fmt_pct_es(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def _mes_es(m: int) -> str:
    return {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}[m]


def _mmmyy_es(dt: pd.Timestamp) -> str:
    dt = pd.to_datetime(dt)
    return f"{_mes_es(dt.month)}-{str(dt.year)[-2:]}"


def render_macro_precios(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 🛒 Precios")
    st.caption("Tasa mensual de inflación - % Nacional")
    st.divider()

    # --- CSS: multiselect angosto + chips de período (tipo “tasa”) ---
    st.markdown(
        """
        <style>
        /* Multiselect más angosto y más “presente” */
        div[data-baseweb="select"]{
            max-width: 560px;
        }
        div[data-baseweb="select"] > div{
            background: rgba(255,255,255,0.9);
            border: 1px solid rgba(0,0,0,0.10);
            border-radius: 10px;
        }

        /* Chips 6M/1A/2A/Todo: estilo “pill” */
        div[role="radiogroup"]{
            gap: 8px !important;
        }
        div[role="radiogroup"] > label{
            border: 1px solid rgba(0,0,0,0.12);
            border-radius: 999px;
            padding: 6px 12px;
            background: rgba(255,255,255,0.9);
        }
        div[role="radiogroup"] > label:hover{
            border-color: rgba(0,0,0,0.22);
        }
        /* achica el texto */
        div[role="radiogroup"] span{
            font-size: 12px !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    ipc = get_ipc_indec_full()
    ipc = ipc[ipc["Region"] == "Nacional"].copy()
    if ipc.empty:
        st.warning("Sin datos IPC.")
        return

    # selector de 1 o más divisiones
    opciones = sorted(ipc["Descripcion"].dropna().unique())
    default = ["Nivel general"] if "Nivel general" in opciones else [opciones[0]]

    descs = st.multiselect(
        "Seleccioná una o más divisiones",
        options=opciones,
        default=default,
    )
    if not descs:
        st.info("Seleccioná al menos una división.")
        return

    # serie de nivel general (para título cuando hay múltiples)
    ng = ipc[ipc["Descripcion"] == "Nivel general"].dropna(subset=["v_m_IPC"]).copy()
    if ng.empty:
        st.warning("No se encontró 'Nivel general'.")
        return

    last_period = pd.to_datetime(ng["Periodo"].iloc[-1])
    ng_last_vm = float(ng["v_m_IPC"].iloc[-1])

    # selector de período (chips)
    rango = st.radio(
        "Período",
        ["6M", "1A", "2A", "Todo"],
        horizontal=True,
        index=3,
        label_visibility="collapsed",
    )

    # rango de fechas según selección
    max_real = pd.to_datetime(last_period)
    if rango == "6M":
        min_sel = max_real - pd.DateOffset(months=6)
        tick_freq = "MS"   # mensual
    elif rango == "1A":
        min_sel = max_real - pd.DateOffset(years=1)
        tick_freq = "2MS"  # cada 2 meses
    elif rango == "2A":
        min_sel = max_real - pd.DateOffset(years=2)
        tick_freq = "3MS"  # cada 3 meses
    else:
        min_sel = pd.to_datetime(ipc["Periodo"].min())
        tick_freq = "6MS"  # cada 6 meses

    # aire a la derecha (1 mes)
    max_sel = max_real + pd.DateOffset(months=1)

    # KPI: se basa en la PRIMERA división seleccionada (si hay una sola, perfecto)
    base_desc = descs[0]
    base = ipc[ipc["Descripcion"] == base_desc].dropna(subset=["v_m_IPC"]).copy()
    base = base.sort_values("Periodo")
    if base.empty:
        st.warning("Sin serie para esa división.")
        return

    base_last_vm = float(base["v_m_IPC"].iloc[-1])
    base_last_yoy = float(base["v_i_a_IPC"].iloc[-1]) if pd.notna(base["v_i_a_IPC"].iloc[-1]) else None
    base_last_period = pd.to_datetime(base["Periodo"].iloc[-1])

    c1, c2 = st.columns([1, 3], vertical_alignment="top")

    # ----------------------------
    # KPI + descarga
    # ----------------------------
    with c1:
        st.markdown(
            f"""
            <div style="font-weight:800; line-height:1.0;">
              <span style="font-size:48px;">{_fmt_pct_es(base_last_vm, 1)}%</span>
              <span style="font-size:20px; font-weight:700; color:#111827; margin-left:6px;">
                {_mmmyy_es(base_last_period)}
              </span>
            </div>
            <div style="margin-top:10px; font-size:22px; font-weight:800;">
              {_fmt_pct_es(base_last_yoy, 1) if base_last_yoy is not None else "-"}% anual
            </div>
            """,
            unsafe_allow_html=True,
        )

        # espacio y botón debajo del KPI
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # CSV: si hay varias divisiones, exporta todas las elegidas, si no exporta una
        out = ipc[ipc["Descripcion"].isin(descs)].copy()
        out = out[out["Region"] == "Nacional"]
        out = out.sort_values(["Descripcion", "Periodo"])

        csv = out.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
        st.download_button(
            "⬇️ Descargar CSV",
            data=csv,
            file_name="ipc_divisiones.csv",
            mime="text/csv",
            use_container_width=False,
        )

    # ----------------------------
    # Gráfico
    # ----------------------------
    with c2:
        # título: 1 división -> texto con esa división; múltiples -> solo IPC general
        if len(descs) == 1:
            title_txt = (
                f"La inflación de {base_desc} de {_mmmyy_es(base_last_period)} fue "
                f"{_fmt_pct_es(base_last_vm, 1)}%"
            )
        else:
            title_txt = f"IPC nivel general de {_mmmyy_es(last_period)}: {_fmt_pct_es(ng_last_vm, 1)}%"

        # datos del período seleccionado (para autoescala Y)
        tmp = ipc[ipc["Descripcion"].isin(descs)].dropna(subset=["v_m_IPC"]).copy()
        tmp = tmp[(tmp["Periodo"] >= min_sel) & (tmp["Periodo"] <= max_real)]

        if tmp.empty:
            st.warning("No hay datos en el período seleccionado.")
            return

        ymin = float(tmp["v_m_IPC"].min())
        ymax = float(tmp["v_m_IPC"].max())
        pad = max(0.8, (ymax - ymin) * 0.10)  # padding razonable
        y_range = [ymin - pad, ymax + pad]

        # ticks X en español, densidad según período
        tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq=tick_freq)
        # si quedaron pocos ticks, densificamos un poco
        if len(tickvals) < 4:
            tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq="MS")
        ticktext = [f"{_mes_es(d.month)}-{str(d.year)[-2:]}" for d in tickvals]

        fig = go.Figure()

        for d in descs:
            s = ipc[(ipc["Descripcion"] == d)].dropna(subset=["v_m_IPC"]).copy()
            s = s[(s["Periodo"] >= min_sel) & (s["Periodo"] <= max_real)].sort_values("Periodo")
            if s.empty:
                continue

            fig.add_trace(
                go.Scatter(
                    x=s["Periodo"],
                    y=s["v_m_IPC"],
                    name=d,
                    mode="lines+markers",
                    marker=dict(size=4),
                    hovertemplate="%{x|%b-%y}<br>%{y:.1f}%<extra></extra>",
                )
            )

        # leyenda: si hay varias, arriba a la derecha
        show_legend = len(descs) > 1

        fig.update_layout(
            hovermode="x unified",
            height=520,
            margin=dict(l=10, r=20, t=60, b=70),
            title=dict(text=title_txt, x=0, xanchor="left"),
            showlegend=show_legend,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
            ) if show_legend else None,
        )

        fig.update_yaxes(
            title_text="Variación mensual (%)",
            ticksuffix="%",
            range=y_range,          # autoescala por período
            fixedrange=False,
        )

        fig.update_xaxes(
            title_text="",
            range=[min_sel, max_sel],      # aire a la derecha
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            fixedrange=False,
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption("Fuente: INDEC")
