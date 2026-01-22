import streamlit as st
import pandas as pd

from services.macro_data import (
    get_a3500,
    get_monetaria_serie,
    get_ipc_bcra,
)

# ============================================================
# Format helpers (ES)
# ============================================================
def _fmt_num_es(x: float, dec: int = 2) -> str:
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _fmt_pct_es(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",") + "%"


# ============================================================
# Últimos datos (cacheados para no hacer lenta la Home)
# ============================================================
@st.cache_data(ttl=12 * 60 * 60)
def _last_tc():
    df = get_a3500()  # columnas: Date, FX
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "FX"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["FX"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60)
def _last_tasa(default_id: int = 13):
    # Monetarias: Date, value
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
    # BCRA IPC: Date, v_m_CPI (decimal), Period
    df = get_ipc_bcra()
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "v_m_CPI"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["v_m_CPI"]), pd.to_datetime(r["Date"])


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

        # ------------------------------------------------------------
        # Cargamos "últimos datos" (cacheados, si falla => None)
        # ------------------------------------------------------------
        fx_val, fx_date = _last_tc()

        # Tasa default: 13 (Adelantos). Si querés Plazo Fijo=12 o Personales=14, cambiá acá.
        tasa_val, tasa_date = _last_tasa(13)

        # IPC BCRA (v_m_CPI en decimal)
        ipc_val, ipc_date = _last_ipc_bcra()

        with c1:
            if st.button("💱\nTipo de cambio", use_container_width=True):
                go_to("macro_fx")

            if fx_val is None or fx_date is None:
                st.caption("Último: —")
            else:
                st.caption(f"Último: ${_fmt_num_es(fx_val, 2)} · {fx_date.strftime('%d/%m/%Y')}")

        with c2:
            if st.button("📈\nTasa de interés", use_container_width=True):
                go_to("macro_tasa")

            if tasa_val is None or tasa_date is None:
                st.caption("Último: —")
            else:
                st.caption(f"Último: {_fmt_pct_es(tasa_val, 1)} TNA · {tasa_date.strftime('%d/%m/%Y')}")

        with c3:
            if st.button("🛒\nPrecios", use_container_width=True):
                go_to("macro_precios")

            # ipc_val viene en decimal -> % m/m
            if ipc_val is None:
                st.caption("Último: —")
            else:
                txt_val = _fmt_pct_es(ipc_val * 100, 1) + " m/m"
                txt_date = ipc_date.strftime("%m/%Y") if ipc_date is not None else ""
                st.caption(f"Último: {txt_val}" + (f" · {txt_date}" if txt_date else ""))

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
