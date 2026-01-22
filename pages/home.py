import streamlit as st


def render_main_home(go_to):
    # ============================================================
    # HOME – Full width SOLO para esta página
    # (no rompe el resto del monitor)
    # ============================================================
    st.markdown(
        """
        <style>
          /* Forzar ancho completo y quitar aire superior SOLO en Home */
          section.main > div.block-container {
            max-width: 100% !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            padding-top: 0.3rem !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ============================================================
    # Banner superior (estable, sin CSS raro)
    # ============================================================
    st.image("assets/header_ceu.png", use_container_width=True)

    # Un cachitito de separación (ajustable)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ============================================================
    # Título
    # ============================================================
    st.markdown(
        """
        <div class="home-wrap">
          <div class="home-title">Monitor CEU–UIA</div>
          <div class="home-subtitle">Seleccioná una sección</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ============================================================
    # Botones de secciones
    # ============================================================
    left_pad, mid, right_pad = st.columns([1, 6, 1])
    with mid:
        st.markdown('<div class="home-cards">', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        with c1:
            if st.button("📊\nMacroeconomía", use_container_width=True):
                go_to("macro_home")

        with c2:
            if st.button("💼\nEmpleo Privado", use_container_width=True):
                go_to("empleo")

        with c3:
            if st.button("🏭\nProducción Industrial", use_container_width=True):
                go_to("ipi")

        st.markdown("</div>", unsafe_allow_html=True)
