
import base64
import streamlit as st


def header_banner(image_path: str):
    """
    Banner full-width, sin recorte, alto mínimo necesario,
    pegado arriba de todo.
    """
    with open(image_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

    st.markdown(
        f"""
        <style>
          /* Saca espacio superior default de Streamlit */
          .block-container {{
            padding-top: 0rem;
          }}

          .ceu-banner {{
            width: 100vw;
            aspect-ratio: 6 / 1;   /* ajusta proporción del banner */
            margin-left: calc(-50vw + 50%);
            margin-top: -1.5rem;

            background-image: url("data:image/png;base64,{img_base64}");
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            background-color: #2f4f8f; /* azul institucional de fondo */
          }}
        </style>

        <div class="ceu-banner"></div>
        """,
        unsafe_allow_html=True,
    )



def render_main_home(go_to):
    # Banner ARRIBA DE TODO
    header_banner("assets/header_ceu.png")

    st.markdown(
        """
        <div class="home-wrap">
          <div class="home-title">Monitor CEU–UIA</div>
          <div class="home-subtitle">Seleccioná una sección</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
