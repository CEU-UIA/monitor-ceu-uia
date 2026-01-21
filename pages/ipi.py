import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.ipi_data import cargar_ipi_excel, procesar_serie_excel
from services.metrics import calc_var, fmt, obtener_nombre_mes


# =========================
# HELPER SPARKLINE
# =========================
def sparkline_fig(df_serie, height=90):
    if df_serie is None or df_serie.empty:
        return None

    s = df_serie.dropna().sort_values("fecha").tail(18)
    if s.empty:
        return None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=s["fecha"],
            y=s["valor"],
            mode="lines",
            line=dict(width=2),
            hovertemplate="%{x|%b-%y}: %{y:.1f}<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def render_ipi(go_to):
    if st.button("← Volver"):
        go_to("home")

    st.markdown("## 🏭 Producción Industrial")
    st.caption("Fuente: INDEC – IPI Manufacturero (Excel)")
    st.divider()

    if "ipi_sel_div" not in st.session_state:
        st.session_state.ipi_sel_div = None

    df_c2, df_c5 = cargar_ipi_excel()
    if df_c2 is None or df_c5 is None:
        st.error("Error al descargar el archivo del INDEC.")
        return

    names_c2 = [str(x).strip() for x in df_c2.iloc[3].fillna("").tolist()]
    codes_c2 = [str(x).strip() for x in df_c2.iloc[2].fillna("").tolist()]
    names_c5 = [str(x).strip() for x in df_c5.iloc[3].fillna("").tolist()]

    ng_sa = procesar_serie_excel(df_c5, 3)
    ng_orig = procesar_serie_excel(df_c2, 3)

    if ng_sa.empty or ng_orig.empty:
        st.warning("No se pudieron extraer series del Excel.")
        return

    m_ng = calc_var(ng_sa["valor"], 1)
    i_ng = calc_var(ng_orig["valor"], 12)

    st.subheader(f"IPI Manufacturero - {obtener_nombre_mes(ng_sa['fecha'].iloc[-1])}")
    m_cols = st.columns(2)
    m_cols[0].metric("Variación Mensual (SA)", f"{fmt(m_ng, 1)}%")
    m_cols[1].metric("Variación Interanual", f"{fmt(i_ng, 1)}%")

    # =========================
    # DIVISIONES INDUSTRIALES
    # =========================
    st.write("#### Divisiones Industriales")

    divs_idxs = [
        i for i, n in enumerate(names_c5)
        if i >= 3 and i % 2 != 0 and n not in ("", "Período", "IPI Manufacturero")
    ]

    for i in range(0, len(divs_idxs), 3):
        cols = st.columns(3, vertical_alignment="top")

        for j, idx in enumerate(divs_idxs[i:i + 3]):
            name = names_c5[idx]

            s_sa = procesar_serie_excel(df_c5, idx)
            v_m = calc_var(s_sa["valor"], 1) if not s_sa.empty else np.nan

            try:
                idx_c2 = names_c2.index(name)
                s_orig = procesar_serie_excel(df_c2, idx_c2)
                v_i = calc_var(s_orig["valor"], 12) if not s_orig.empty else np.nan
                raw_code = codes_c2[idx_c2]
            except Exception:
                v_i = np.nan
                raw_code = None

            arrow = "⬆️" if (pd.notna(v_m) and v_m > 0) else ("⬇️" if (pd.notna(v_m) and v_m < 0) else "•")
            fig_sp = sparkline_fig(s_sa)

            with cols[j]:
                st.markdown(
                    f"""
                    <div class="macro-card">
                      <div style="font-weight:800; font-size:16px; margin-bottom:6px;">{name}</div>
                      <div style="display:flex; gap:14px; align-items:baseline; margin-bottom:4px;">
                        <div style="font-size:26px; font-weight:900;">{arrow} {fmt(v_m, 1)}%</div>
                        <div style="font-size:13px; font-weight:700; color:#526484;">Var. Mensual (s.e)</div>
                      </div>
                      <div style="font-size:13px; font-weight:700; color:#526484; margin-bottom:8px;">
                        Interanual:
                        <span style="color:#0b2b4c; font-weight:900;">{fmt(v_i, 1)}%</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if fig_sp is not None:
                    st.plotly_chart(
                        fig_sp,
                        use_container_width=True,
                        config={"displayModeBar": False},
                    )

                if st.button("Ver detalle", key=f"ipi_btn_{idx}"):
                    if raw_code:
                        st.session_state.ipi_sel_div = (name, raw_code)

    # =========================
    # DETALLE SUBCLASES
    # =========================
    if st.session_state.ipi_sel_div:
        div_name, div_code = st.session_state.ipi_sel_div
        st.divider()
        st.subheader(f"Detalle de Subclases: {div_name}")

        prefixes = [p.strip() for p in str(div_code).split("-") if p.strip()]
        if "36" in prefixes:
            prefixes.append("33")

        sub_list = []
        for i, code in enumerate(codes_c2):
            code_s = str(code).strip()
            if any(code_s.startswith(p) for p in prefixes) and code_s not in prefixes:
                s = procesar_serie_excel(df_c2, i)
                if not s.empty:
                    sub_list.append({
                        "Subclase": names_c2[i],
                        "Variación Interanual (%)": calc_var(s["valor"], 12)
                    })

        if sub_list:
            df_sub = pd.DataFrame(sub_list).dropna()
            st.dataframe(
                df_sub.style.format({"Variación Interanual (%)": "{:,.2f}%"}),
                width="stretch",
            )
        else:
            st.info("No hay desglose adicional disponible.")
