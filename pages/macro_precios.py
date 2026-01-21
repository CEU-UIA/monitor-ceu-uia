import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_ipc_indec_full


def _fmt_pct_es(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def _mes_es(m: int) -> str:
    return {
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"
    }[m]


def _mmmyy_es(dt) -> str:
    dt = pd.to_datetime(dt)
    return f"{_mes_es(dt.month)}-{str(dt.year)[-2:]}"


def _find_nivel_general_code(df_codes: pd.DataFrame):
    """
    Devuelve el 'Codigo' que corresponde a Nivel general.
    Primero intenta por descripción exacta/contiene, luego por código 0 si existe.
    """
    if df_codes.empty:
        return None

    # por texto
    for _, r in df_codes.iterrows():
        lab = str(r.get("Label", "")).strip().lower()
        if lab == "nivel general":
            return r["Codigo"]
    for _, r in df_codes.iterrows():
        lab = str(r.get("Label", "")).strip().lower()
        if "nivel general" in lab:
            return r["Codigo"]

    # fallback por código 0
    if any(str(c).strip() == "0" for c in df_codes["Codigo"].astype(str)):
        return "0"

    return None


def render_macro_precios(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 🛒 Precios")
    st.caption("Tasa de inflación - % Nacional")
    st.divider()

    # --- CSS: multiselect más grande y con contraste + pills ---
    st.markdown(
        """
        <style>
        /* Multiselect: más grande + fondo oscuro + texto claro */
        div[data-baseweb="select"]{
            max-width: 680px;
        }
        div[data-baseweb="select"] > div{
            background: rgba(17,24,39,0.94); /* gris oscuro */
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 12px;
            min-height: 48px;
        }
        div[data-baseweb="select"] *{
            color: rgba(255,255,255,0.92) !important;
            font-weight: 650;
            font-size: 14px;
        }

        /* Chips 6M/1A/2A/Todo + Frecuencia */
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
        div[role="radiogroup"] span{
            font-size: 12px !important;
            font-weight: 700 !important;
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

    # ------------------------------------------------------------------
    # 4) Selector por Codigo (+ labels manuales B/S/Estacional/Núcleo/Regulados)
    # ------------------------------------------------------------------
    # Tomo una tabla única de códigos con su descripción (1 a 1 "ideal")
    codes = (
        ipc[["Codigo", "Descripcion"]]
        .drop_duplicates()
        .copy()
    )
    codes["Codigo"] = codes["Codigo"].astype(str).str.strip()
    codes["Descripcion"] = codes["Descripcion"].astype(str).str.strip()

    # Si la descripción viene vacía para algunos códigos, la completamos:
    manual = {
        "B": "Bienes",
        "S": "Servicios",
        "Estacional": "Estacional",
        "Núcleo": "Núcleo",
        "Regulados": "Regulados",
    }
    # Label final: si hay descripción útil, usarla; si no, usar manual o el propio código.
    def _label_row(r):
        c = str(r["Codigo"]).strip()
        d = str(r["Descripcion"]).strip()
        if d and d.lower() != "nan":
            return d
        if c in manual:
            return manual[c]
        return c

    codes["Label"] = codes.apply(_label_row, axis=1)

    # Orden: nivel general primero (si existe), luego alfabético por label
    ng_code = _find_nivel_general_code(codes)
    if ng_code is not None:
        codes_others = codes[codes["Codigo"] != str(ng_code)].sort_values("Label")
        codes_ordered = pd.concat([codes[codes["Codigo"] == str(ng_code)], codes_others], ignore_index=True)
    else:
        codes_ordered = codes.sort_values("Label")

    code_list = codes_ordered["Codigo"].tolist()
    code_to_label = dict(zip(codes_ordered["Codigo"], codes_ordered["Label"]))

    # Default: Nivel general si existe
    default_codes = [str(ng_code)] if ng_code is not None else ([code_list[0]] if code_list else [])

    selected_codes = st.multiselect(
        "Seleccioná una o más divisiones",
        options=code_list,
        default=default_codes,
        format_func=lambda c: code_to_label.get(str(c), str(c)),
    )
    if not selected_codes:
        st.info("Seleccioná al menos una división.")
        return

    # ------------------------------------------------------------------
    # 2) Selector Frecuencia: mensual vs anual (cambia serie, título y eje Y)
    # ------------------------------------------------------------------
    freq = st.radio(
        "Seleccioná la frecuencia",
        ["Mensual", "Anual"],
        horizontal=True,
        index=0,
    )
    if freq == "Mensual":
        y_col = "v_m_IPC"
        y_label = "Variación mensual (%)"
        freq_word = "inflación"
    else:
        y_col = "v_i_a_IPC"
        y_label = "Variación anual (%)"
        freq_word = "inflación interanual"

    # --- Serie base: PRIMERA seleccionada ---
    base_code = str(selected_codes[0]).strip()
    base_label = code_to_label.get(base_code, base_code)

    base = ipc[ipc["Codigo"].astype(str).str.strip() == base_code].copy()
    base = base.dropna(subset=[y_col]).sort_values("Periodo")
    if base.empty:
        st.warning("Sin serie para esa división/frecuencia.")
        return

    base_last_period = pd.to_datetime(base["Periodo"].iloc[-1])
    base_last_val = float(base[y_col].iloc[-1])

    # además, mantenemos ambos para KPI secundario (sin que lo pidas, pero queda coherente)
    base_last_vm = None
    base_last_yoy = None
    if "v_m_IPC" in base.columns and pd.notna(base["v_m_IPC"].iloc[-1]):
        base_last_vm = float(base["v_m_IPC"].iloc[-1])
    if "v_i_a_IPC" in base.columns and pd.notna(base["v_i_a_IPC"].iloc[-1]):
        base_last_yoy = float(base["v_i_a_IPC"].iloc[-1])

    # ----------------------------
    # Layout KPI + Gráfico
    # ----------------------------
    c1, c2 = st.columns([1, 3], vertical_alignment="top")

    with c1:
        # KPI principal = frecuencia elegida
        big = base_last_val
        big_suffix = "mensual" if freq == "Mensual" else "anual"
        small = None
        small_suffix = None

        if freq == "Mensual":
            small = base_last_yoy
            small_suffix = "anual"
        else:
            small = base_last_vm
            small_suffix = "mensual"

        st.markdown(
            f"""
            <div style="font-weight:800; line-height:1.0;">
              <span style="font-size:48px;">{_fmt_pct_es(big, 1)}%</span>
              <span style="font-size:20px; font-weight:700; color:#111827; margin-left:6px;">
                {_mmmyy_es(base_last_period)}
              </span>
            </div>
            <div style="margin-top:10px; font-size:18px; font-weight:800;">
              {big_suffix}
            </div>
            <div style="margin-top:8px; font-size:18px; font-weight:800;">
              {_fmt_pct_es(small, 1) if small is not None else "-"}% {small_suffix if small_suffix else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # CSV de los códigos seleccionados (filtrado por nacional)
        out = ipc[ipc["Codigo"].astype(str).str.strip().isin([str(x).strip() for x in selected_codes])].copy()
        out = out[out["Region"] == "Nacional"].sort_values(["Codigo", "Periodo"])
        csv = out.to_csv(index=False, sep=";", decimal=",").encode("utf-8")

        st.download_button(
            "⬇️ Descargar CSV",
            data=csv,
            file_name="ipc_codigos.csv",
            mime="text/csv",
            use_container_width=False,
        )

    with c2:
        # 3) Selector de período ARRIBA DEL GRÁFICO (como el resto)
        rango = st.radio(
            "Período",
            ["6M", "1A", "2A", "Todo"],
            horizontal=True,
            index=3,
            label_visibility="collapsed",
        )

        max_real = pd.to_datetime(base_last_period)
        if rango == "6M":
            min_sel = max_real - pd.DateOffset(months=6)
            tick_freq = "MS"
        elif rango == "1A":
            min_sel = max_real - pd.DateOffset(years=1)
            tick_freq = "2MS"
        elif rango == "2A":
            min_sel = max_real - pd.DateOffset(years=2)
            tick_freq = "3MS"
        else:
            min_sel = pd.to_datetime(ipc["Periodo"].min())
            tick_freq = "6MS"

        max_sel = max_real + pd.DateOffset(months=1)

        # Título: respeta la PRIMERA selección + la frecuencia
        title_txt = (
            f"La {freq_word} de {base_label} de {_mmmyy_es(base_last_period)} fue "
            f"{_fmt_pct_es(base_last_val, 1)}%"
        )

        # Autoescala Y según período y frecuencia elegida
        tmp = ipc[ipc["Codigo"].astype(str).str.strip().isin([str(x).strip() for x in selected_codes])].copy()
        tmp = tmp.dropna(subset=[y_col])
        tmp = tmp[(tmp["Periodo"] >= min_sel) & (tmp["Periodo"] <= max_real)]
        if tmp.empty:
            st.warning("No hay datos en el período seleccionado.")
            return

        ymin = float(tmp[y_col].min())
        ymax = float(tmp[y_col].max())
        pad = max(0.8, (ymax - ymin) * 0.10)
        y_range = [ymin - pad, ymax + pad]

        # ticks X
        tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq=tick_freq)
        if len(tickvals) < 4:
            tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq="MS")
        ticktext = [f"{_mes_es(d.month)}-{str(d.year)[-2:]}" for d in tickvals]

        fig = go.Figure()

        for c in selected_codes:
            c = str(c).strip()
            lab = code_to_label.get(c, c)

            s = ipc[ipc["Codigo"].astype(str).str.strip() == c].copy()
            s = s.dropna(subset=[y_col])
            s = s[(s["Periodo"] >= min_sel) & (s["Periodo"] <= max_real)].sort_values("Periodo")
            if s.empty:
                continue

            fig.add_trace(
                go.Scatter(
                    x=s["Periodo"],
                    y=s[y_col],
                    name=lab,
                    mode="lines+markers",
                    marker=dict(size=5),
                    hovertemplate="%{x|%b-%y}<br>%{y:.1f}%<extra></extra>",
                )
            )

        show_legend = len(selected_codes) > 1

        fig.update_layout(
            hovermode="x unified",
            height=520,
            margin=dict(l=10, r=20, t=60, b=70),
            title=dict(text=title_txt, x=0, xanchor="left"),
            showlegend=show_legend,
        )

        if show_legend:
            fig.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1.0,
                )
            )

        fig.update_yaxes(
            title_text=y_label,      # <- cambia con frecuencia
            ticksuffix="%",
            range=y_range,
            fixedrange=False,
        )

        fig.update_xaxes(
            title_text="",
            range=[min_sel, max_sel],
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            fixedrange=False,
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: INDEC")

    # ----------------------------
    # Tabla interactiva (abajo) - se mantiene mensual (últimos 12 meses)
    # ----------------------------
    st.markdown("#### Tabla de variaciones mensuales (últimos 12 meses)")

    tab = ipc.dropna(subset=["Periodo", "Codigo", "v_m_IPC"]).copy()
    tab["Periodo"] = pd.to_datetime(tab["Periodo"], errors="coerce")
    tab = tab.dropna(subset=["Periodo"])

    # últimos 12 meses disponibles
    last_period = tab["Periodo"].max()
    months = pd.period_range(last_period.to_period("M") - 11, last_period.to_period("M"), freq="M")
    month_dates = [p.to_timestamp("M") for p in months]
    col_labels = [_mmmyy_es(d) for d in month_dates]

    tab["Codigo"] = tab["Codigo"].astype(str).str.strip()
    tab["Label"] = tab["Codigo"].map(code_to_label).fillna(tab["Codigo"])

    piv = (
        tab[tab["Periodo"].dt.to_period("M").isin(months)]
        .assign(Period=lambda x: x["Periodo"].dt.to_period("M"))
        .pivot_table(index="Label", columns="Period", values="v_m_IPC", aggfunc="last")
    )

    piv = piv.reindex(columns=months)
    piv.columns = col_labels

    # Orden: Nivel general primero (si está), luego alfabético
    idx = list(piv.index)
    ng_label = None
    for k, v in code_to_label.items():
        if str(k).strip() == str(ng_code).strip():
            ng_label = v
            break
    others = sorted([x for x in idx if x != ng_label], key=lambda z: str(z))
    ordered = ([ng_label] if ng_label in idx else []) + others
    piv = piv.reindex(ordered)

    def _fmt_cell(v):
        if pd.isna(v):
            return "-"
        return f"{_fmt_pct_es(float(v), 1)}%"

    piv_fmt = piv.applymap(_fmt_cell)

    st.dataframe(piv_fmt, use_container_width=True)
