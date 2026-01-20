import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_monetaria_serie


def _fmt_pct_es(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def render_macro_tasa(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 📈 Tasa de interés")
    st.caption("Tasa de adelantos a cuentas corrientes de empresas - % TNA")
    st.divider()

    tasa = get_monetaria_serie(145)
    if tasa.empty:
        st.warning("Sin datos de tasa.")
        return

    tasa = tasa.dropna(subset=["Date", "value"]).sort_values("Date").reset_index(drop=True)

    # Último dato
    last_val = float(tasa["value"].iloc[-1])
    last_date = pd.to_datetime(tasa["Date"].iloc[-1]).date()

    c1, c2 = st.columns([1, 3])

    # ----------------------------
    # (1) + (2) KPI con coma + "TNA" + fecha último dato
    # ----------------------------
    with c1:
        st.markdown(
            f"""
            <div style="font-size:46px; font-weight:800; line-height:1.0;">
                {_fmt_pct_es(last_val, 1)}% <span style="font-size:18px; font-weight:700;">TNA</span>
            </div>
            <div style="margin-top:8px; color:#6b7280; font-size:14px;">
                Último dato: {last_date.strftime("%d/%m/%Y")}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ----------------------------
    # Gráfico
    # (3) rangeslider
    # (4) título dinámico
    # (5) aire a la derecha (1 mes)
    # (6) eje x en español
    # ----------------------------
    with c2:
        inflacion_esp_12m = 20.0  # umbral fijo que pediste
        pos = "por encima" if last_val > inflacion_esp_12m else "debajo"
        title_txt = (
            f"   La tasa se ubica {pos} de la inflación esperada para los próximos 12 meses: "
            f"{_fmt_pct_es(inflacion_esp_12m, 0)}%"
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=tasa["Date"], y=tasa["value"], name="Tasa", mode="lines"))

        # (5) un mes libre a la derecha
        min_date = pd.to_datetime(tasa["Date"].min())
        max_date = pd.to_datetime(tasa["Date"].max()) + pd.Timedelta(days=31)

        # (6) eje x en español con ticks manuales
        mes_es = {
            1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"
        }

        # ticks cada 6 meses para no saturar
        tickvals = pd.date_range(min_date.normalize(), max_date.normalize(), freq="6MS")
        if len(tickvals) < 4:
            tickvals = pd.date_range(min_date.normalize(), max_date.normalize(), freq="3MS")

        ticktext = [f"{mes_es[d.month]} {d.year}" for d in tickvals]

        fig.update_layout(
            hovermode="x unified",
            height=450,
            margin=dict(l=10, r=10, t=70, b=60),
            showlegend=False,
            title=dict(text=title_txt, x=0, xanchor="left"),
        )

        fig.update_yaxes(title_text="% TNA", ticksuffix="%")

        fig.update_xaxes(
            title_text="",
            range=[min_date, max_date],
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            # (3) barra dinámica para zoom/selección
            rangeslider=dict(visible=True),
        )

        st.plotly_chart(fig, use_container_width=True)
