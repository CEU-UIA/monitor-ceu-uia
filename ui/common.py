import base64
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st


_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


@lru_cache(maxsize=1)
def institutional_logo_sources() -> tuple[str, str]:
    """Devuelve los logos institucionales como data URI para incrustarlos en HTML."""
    sources = []
    for filename in ("logo_ceu.png", "logo_oit.png"):
        encoded = base64.b64encode((_ASSETS_DIR / filename).read_bytes()).decode("ascii")
        sources.append(f"data:image/png;base64,{encoded}")
    return tuple(sources)


def topbar_logo() -> None:
    """Logos institucionales del CEU y la OIT arriba a la derecha."""
    try:
        ceu_logo, oit_logo = institutional_logo_sources()
        st.markdown(
            f"""
            <style>
              .institutional-topbar {{
                width: 100%;
                display: flex;
                justify-content: flex-end;
                align-items: center;
                gap: 14px;
                margin: 0 0 0.75rem auto;
              }}
              .institutional-topbar .ceu-topbar-logo {{
                width: 215px;
                max-width: 70vw;
                height: auto;
                display: block;
              }}
              .institutional-topbar .oit-topbar-logo {{
                width: 50px;
                height: auto;
                display: block;
              }}
              @media (max-width: 700px) {{
                .institutional-topbar {{ gap: 10px; }}
                .institutional-topbar .ceu-topbar-logo {{ width: 160px; }}
                .institutional-topbar .oit-topbar-logo {{ width: 40px; }}
              }}
            </style>
            <div class="institutional-topbar">
              <img
                src="{ceu_logo}"
                class="ceu-topbar-logo"
                alt="Centro de Estudios UIA"
              />
              <img
                src="{oit_logo}"
                class="oit-topbar-logo"
                alt="Organización Internacional del Trabajo"
              />
            </div>
            """,
            unsafe_allow_html=True,
        )
    except OSError:
        st.markdown("### CEU - UIA · OIT")


def safe_pct(x, dec: int = 1) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:.{dec}f}%".replace(".", ",")


def get_section(default: str = "home") -> str:
    """Lee la seccion desde session_state y query params."""
    if "section" not in st.session_state:
        st.session_state.section = default

    params = st.query_params
    if "section" in params:
        sec = params["section"]
        if isinstance(sec, (list, tuple)):
            sec = sec[0]
        if isinstance(sec, str) and sec.strip():
            st.session_state.section = sec.strip()

    return st.session_state.section


def go_to(section: str):
    st.session_state["section"] = section
    st.query_params["section"] = section  # mantiene URL consistente
    st.rerun()
