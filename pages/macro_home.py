import streamlit as st

#### NUEVO: imports + cache helpers
import pandas as pd

from services.macro_data import (
    get_a3500,
    get_monetaria_serie,
    get_ipc_bcra,
)
####


#### NUEVO: formateadores simples
def _fmt_num_es(x: float, dec: int = 0) -> str:
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _fmt_pct_es(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",") + "%"
####


#### NUEVO: últimos datos (cacheados)
@st.cache_data(ttl=12 * 60 * 60)
def _last_tc():
    df = get_a3500()
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "FX"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["FX"]), pd.to_datetime(r["Date"])

@st.cache_data(ttl=12 * 60 * 60)
def _last_tasa(default_id: int = 13):
    df = get_monetaria_serie(default_id)
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "value"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["value"]), pd.to_datetime(r["Date"])

@st.cache_data(ttl=12 * 60 * 60)
def _last_ipc_bcra():
    df = get_ipc_bcra()
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "value"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["value"]), pd.to_datetime(r["Date"])
####


def render_macro_home(go_to):
    st.markdown(
        """
        <div class="home-wrap">
            <div class="home-title">Macroeconomía</div>
            <div class="home-subtitle">Seleccioná una variable</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_pad, mid, right_pad = st.columns([1, 6, 1])

    with mid:
        st.markdown('<div class="home-cards">', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        #### NUEVO: placeholders de “último dato” (no rompen nada si fallan)
        fx_val, fx_date = _last_tc()
        tasa_val, tasa_date = _last_tasa(13)  # <- cambiá 13 por 12 o 14 si querés otra por default
        ipc_val, ipc_date = _last_ipc_bcra()
        ####

        with c1:
            if st.button("💱\nTipo de cambio", use_container_width=True):
                go_to("macro_fx")

            #### NUEVO: último TC debajo del botón
            if fx_val is None or fx_date is None:
                st.caption("Último: —")
            else:
                st.caption(f"Último: ${_fmt_num_es(fx_val, 2)} · {fx_date.strftime('%d/%m/%Y')}")
            ####

        with c2:
            if st.button("📈\nTasa de interés", use_container_width=True):
                go_to("macro_tasa")

            #### NUEVO: última tasa debajo del botón
            if tasa_val is None or tasa_date is None:
                st.caption("Último: —")
            else:
                st.caption(f"Último: {_fmt_pct_es(tasa_val, 1)} TNA · {tasa_date.strftime('%d/%m/%Y')}")
            ####

        with c3:
            if st.button("🛒\nPrecios", use_container_width=True):
                go_to("macro_precios")

            #### NUEVO: último IPC BCRA debajo del botón (value viene en decimal)
            if ipc_val is None or ipc_date is None:
                st.caption("Último: —")
            else:
                st.caption(f"Último: {_fmt_pct_es(ipc_val * 100, 1)} m/m · {ipc_date.strftime('%m/%Y')}")
            ####

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
