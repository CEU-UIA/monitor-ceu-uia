import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import base64

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
MORA_PATH = "assets/mora_por_actividad.xlsx"

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


@st.cache_data(show_spinner=False)
def load_mora():
    """Carga la hoja Monitor del Excel de morosidad."""
    df = pd.read_excel(MORA_PATH, sheet_name="Monitor", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    # Normalizar tasa_mora a float (puede venir como "3%" o 0.03)
    if "tasa_mora" in df.columns:
        def parse_tasa(x):
            try:
                s = str(x).replace("%", "").replace(",", ".").strip()
                v = float(s)
                return v if v > 1 else v * 100
            except:
                return float("nan")
        df["tasa_mora"] = df["tasa_mora"].apply(parse_tasa)
    # Asegurar numéricos
    for col in ["saldo_total (miles de $)", "saldo_irregular (miles de $)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=DM+Mono:wght@400;500&display=swap');
  html, body, [class*="css"], [data-testid] { font-family: 'Sora', sans-serif !important; }
  [data-testid="stSidebar"]    { display: none !important; }
  [data-testid="stSidebarNav"] { display: none !important; }
  .block-container {
    max-width: 960px;
    padding-top: 0rem !important;
    padding-bottom: 4rem;
    padding-left: 2rem;
    padding-right: 2rem;
  }
  [data-testid="stHeader"] { background: transparent !important; }
  div[data-testid="stTabs"] { margin-top: -8px; }
  button[data-baseweb="tab"] {
    font-family: 'Sora', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
  }
  label[data-testid="stWidgetLabel"] p {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6b7a99 !important;
  }
  div[data-baseweb="select"] > div {
    font-family: 'Sora', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    border-radius: 10px !important;
    border: 1.5px solid #e2e8f4 !important;
  }
</style>
"""

# ─────────────────────────────────────────────
# KPI card helper
# ─────────────────────────────────────────────
CARD_STYLE = (
    "background:white;"
    "border:1.5px solid #e2e8f4;"
    "border-radius:14px;"
    "padding:0.9rem 0.8rem;"
    "border-top:4px solid #1B2D6B;"
    "box-shadow:0 2px 6px rgba(0,0,0,0.04);"
)
LABEL_STYLE = (
    "font-family:'DM Mono',monospace;"
    "font-size:0.6rem;font-weight:600;"
    "text-transform:uppercase;letter-spacing:0.07em;"
    "color:#6b7a99;margin-bottom:0.35rem;"
)
VALUE_STYLE = (
    "font-family:'Sora',sans-serif;"
    "font-size:1.15rem;font-weight:800;"
    "color:#1B2D6B;letter-spacing:-0.02em;"
    "margin-bottom:0.2rem;line-height:1.2;"
)
PERIOD_STYLE = (
    "font-family:'DM Mono',monospace;"
    "font-size:0.6rem;color:#9aa3b2;"
)

def kpi_card(label, value, sub=""):
    return (
        f'<div style="{CARD_STYLE}">'
        f'<div style="{LABEL_STYLE}">{label}</div>'
        f'<div style="{VALUE_STYLE}">{value}</div>'
        f'<div style="{PERIOD_STYLE}">{sub}</div>'
        f'</div>'
    )

def fmt_miles(x):
    if x is None or pd.isna(x): return "—"
    return f"${float(x)/1_000_000:,.1f}M".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_pct(x):
    if x is None or pd.isna(x): return "—"
    return f"{float(x):.1f}%".replace(".", ",")


# ─────────────────────────────────────────────
# Gráfico de barras horizontales (azul degradado)
# ─────────────────────────────────────────────
def fig_barras_h(title, labels, values, suffix="%", color_scale=True):
    pares = sorted(
        [(l, v) for l, v in zip(labels, values) if v is not None and not pd.isna(v)],
        key=lambda x: x[1],
    )
    names = [p[0] for p in pares]
    vals  = [float(p[1]) for p in pares]
    n     = len(vals)
    maxv  = max(vals) if vals else 1.0

    azul_oscuro = (27, 45, 107)
    azul_claro  = (173, 198, 230)
    colores = []
    for i in range(n):
        t = i / max(n - 1, 1)
        r = int(azul_claro[0] + t * (azul_oscuro[0] - azul_claro[0]))
        g = int(azul_claro[1] + t * (azul_oscuro[1] - azul_claro[1]))
        b = int(azul_claro[2] + t * (azul_oscuro[2] - azul_claro[2]))
        colores.append(f"rgb({r},{g},{b})")

    text_labels = [f"{v:.1f}{suffix}".replace(".", ",") for v in vals]

    fig = go.Figure(go.Bar(
        x=vals, y=names,
        orientation="h",
        marker_color=colores,
        text=text_labels,
        textposition="outside",
        textfont=dict(size=11),
        cliponaxis=False,
        hovertemplate=f"<b>%{{y}}</b><br>%{{x:.1f}}{suffix}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, family="Sora, sans-serif"), x=0.01),
        margin=dict(t=40, b=30, l=200, r=60),
        xaxis=dict(range=[0, maxv * 1.15], showgrid=False, showticklabels=False,
                   showline=False, zeroline=False, fixedrange=True),
        yaxis=dict(tickfont=dict(size=10, family="Sora, sans-serif"), automargin=True),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(320, n * 36 + 80),
        font=dict(family="Sora, sans-serif", color="#31333F"),
        showlegend=False, bargap=0.3,
    )
    return fig


def fig_scatter_mora(df, x_col, y_col, label_col, title):
    """Scatter: saldo total vs tasa mora, un punto por sector."""
    fig = go.Figure(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode="markers+text",
        text=df[label_col],
        textposition="top center",
        textfont=dict(size=9, family="Sora, sans-serif"),
        marker=dict(
            color=df[y_col],
            colorscale="Reds",
            size=12,
            showscale=True,
            colorbar=dict(title="Tasa mora (%)", tickfont=dict(size=9)),
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Saldo total: $%{x:,.0f}k<br>"
            "Tasa mora: %{y:.1f}%<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, family="Sora, sans-serif"), x=0.01),
        height=400,
        margin=dict(t=40, b=50, l=60, r=20),
        xaxis=dict(
            title="Saldo total (miles de $)",
            gridcolor="#F0F2F6",
            tickfont=dict(size=9, family="DM Mono, monospace"),
        ),
        yaxis=dict(
            title="Tasa de mora (%)",
            gridcolor="#F0F2F6",
            tickfont=dict(size=9, family="DM Mono, monospace"),
            ticksuffix="%",
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Sora, sans-serif", color="#31333F"),
        showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────
def render_morosidad(go_to=None):

    st.markdown(CSS, unsafe_allow_html=True)

    # Header
    try:
        logo_b64  = img_to_base64("assets/okok2.png")
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:48px;width:auto;">'
    except Exception:
        logo_html = '<span style="font-family:\'Sora\',sans-serif;font-size:26px;font-weight:700;color:white;">ceu</span>'

    # Botón volver
    back_html = ""
    if go_to:
        if st.button("← Volver al inicio"):
            go_to("home")

    st.markdown(f"""
    <div style="background:#1B2D6B;margin:0 -2rem 0 -2rem;padding:18px 2rem;
    display:flex;align-items:center;justify-content:space-between;gap:20px;">
      <span style="font-family:'Sora',sans-serif;font-size:1.5rem;font-weight:700;color:white;">
        Morosidad
      </span>
      {logo_html}
    </div>
    <div style="background:#F0F3FA;margin:0 -2rem 1.5rem -2rem;padding:10px 2rem;
    font-size:12px;color:#6b6f7e;border-bottom:1px solid #E6E9EF;font-family:'Sora',sans-serif;">
      Unión Industrial Argentina · Datos BCRA
    </div>
    """, unsafe_allow_html=True)

    # Cargar datos
    try:
        df = load_mora()
        data_ok = True
    except Exception as e:
        st.error(f"⚠️ No se pudo cargar `assets/mora_por_actividad.xlsx`.\n\n`{e}`")
        return

    # ── Tabs ──────────────────────────────────
    tab_total, tab_industria = st.tabs([
        "📊 Total",
        "🔍 Lupa en Industria",
    ])

    # ══════════════════════════════════════════
    # TAB 1 — TOTAL
    # ══════════════════════════════════════════
    with tab_total:

        st.markdown(
            '<div style="font-family:\'Sora\',sans-serif;font-size:1.1rem;font-weight:700;'
            'color:#1B2D6B;margin:1rem 0 0.8rem 0;">Vista general por sector (1 dígito)</div>',
            unsafe_allow_html=True,
        )

        # Agrupar por Sector_1_dígito para KPIs globales
        col_sector = "Sector_1_dígito"
        col_saldo  = "saldo_total (miles de $)"
        col_irreg  = "saldo_irregular (miles de $)"
        col_mora   = "tasa_mora"

        # KPIs globales
        total_saldo  = df[col_saldo].sum()  if col_saldo in df.columns else None
        total_irreg  = df[col_irreg].sum()  if col_irreg in df.columns else None
        mora_global  = (total_irreg / total_saldo * 100) if (total_saldo and total_irreg) else None

        # Sector con mayor mora (agrupado)
        if col_sector in df.columns and col_mora in df.columns:
            df_g1 = df.groupby(col_sector).apply(
                lambda x: pd.Series({
                    col_saldo: x[col_saldo].sum(),
                    col_irreg: x[col_irreg].sum(),
                    col_mora:  (x[col_irreg].sum() / x[col_saldo].sum() * 100)
                               if x[col_saldo].sum() > 0 else float("nan"),
                })
            ).reset_index()
            peor_sector = df_g1.sort_values(col_mora, ascending=False).iloc[0][col_sector] \
                          if not df_g1.empty else "—"
        else:
            df_g1 = pd.DataFrame()
            peor_sector = "—"

        # ---- KPI cards ----
        cards_html = (
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.65rem;margin-bottom:1.5rem;">'
            + kpi_card("Saldo total sistema", fmt_miles(total_saldo), "miles de $")
            + kpi_card("Saldo irregular", fmt_miles(total_irreg), "miles de $")
            + kpi_card("Tasa de mora global", fmt_pct(mora_global), "saldo irregular / saldo total")
            + "</div>"
        )
        st.markdown(cards_html, unsafe_allow_html=True)

        # ---- Selector de variable a graficar ----
        var_total = st.selectbox(
            "Variable a visualizar",
            options=["Tasa de mora (%)", "Saldo total (miles de $)", "Saldo irregular (miles de $)"],
            key="sel_total_var",
        )

        if not df_g1.empty:
            if var_total == "Tasa de mora (%)":
                labels = df_g1[col_sector].tolist()
                values = df_g1[col_mora].tolist()
                suffix = "%"
            elif var_total == "Saldo total (miles de $)":
                labels = df_g1[col_sector].tolist()
                values = (df_g1[col_saldo] / 1_000_000).tolist()
                suffix = "M"
            else:
                labels = df_g1[col_sector].tolist()
                values = (df_g1[col_irreg] / 1_000_000).tolist()
                suffix = "M"

            with st.container(border=True):
                st.plotly_chart(
                    fig_barras_h(
                        f"{var_total} por sector (1 dígito)",
                        labels, values, suffix=suffix,
                    ),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

            # Scatter mora vs saldo
            with st.container(border=True):
                st.plotly_chart(
                    fig_scatter_mora(
                        df_g1,
                        x_col=col_saldo,
                        y_col=col_mora,
                        label_col=col_sector,
                        title="Saldo total vs Tasa de mora por sector",
                    ),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
        else:
            st.info("No se encontraron columnas esperadas en el Excel.")

        st.markdown(
            '<div style="text-align:center;font-family:\'DM Mono\',monospace;font-size:0.7rem;'
            'color:#aab0c0;letter-spacing:0.05em;margin-top:2rem;">'
            'CEU – Centro de Estudios UIA · Unión Industrial Argentina · 2026</div>',
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════
    # TAB 2 — LUPA EN INDUSTRIA
    # ══════════════════════════════════════════
    with tab_industria:

        st.markdown(
            '<div style="font-family:\'Sora\',sans-serif;font-size:1.1rem;font-weight:700;'
            'color:#1B2D6B;margin:1rem 0 0.8rem 0;">Zoom en Industria manufacturera (2 dígitos)</div>',
            unsafe_allow_html=True,
        )

        col_sector1 = "Sector_1_dígito"
        col_nombre  = "Nombre"
        col_saldo   = "saldo_total (miles de $)"
        col_irreg   = "saldo_irregular (miles de $)"
        col_mora    = "tasa_mora"

        # Filtrar industria (buscamos "alimentos", "textil", "manufactura", etc.)
        # En tu Excel el sector se llama algo como "Industria manufacturera" o "Alimentos y bebidas"
        # Por ahora filtramos los sectores disponibles y mostramos un selectbox
        sectores_disponibles = sorted(df[col_sector1].dropna().unique().tolist()) \
                               if col_sector1 in df.columns else []

        # Selector de sector (para el zoom)
        sector_zoom = st.selectbox(
            "Sector (1 dígito)",
            options=sectores_disponibles,
            key="sel_industria_sector",
        )

        df_zoom = df[df[col_sector1] == sector_zoom].copy() if sector_zoom else pd.DataFrame()

        # KPIs del sector seleccionado
        saldo_sect = df_zoom[col_saldo].sum() if not df_zoom.empty and col_saldo in df_zoom.columns else None
        irreg_sect = df_zoom[col_irreg].sum() if not df_zoom.empty and col_irreg in df_zoom.columns else None
        mora_sect  = (irreg_sect / saldo_sect * 100) if (saldo_sect and irreg_sect) else None

        cards_html2 = (
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.65rem;margin-bottom:1.5rem;">'
            + kpi_card("Saldo total sector", fmt_miles(saldo_sect), "miles de $")
            + kpi_card("Saldo irregular", fmt_miles(irreg_sect), "miles de $")
            + kpi_card("Tasa de mora sector", fmt_pct(mora_sect), "saldo irregular / saldo total")
            + "</div>"
        )
        st.markdown(cards_html2, unsafe_allow_html=True)

        # Variable a graficar
        var_zoom = st.selectbox(
            "Variable a visualizar",
            options=["Tasa de mora (%)", "Saldo total (miles de $)", "Saldo irregular (miles de $)"],
            key="sel_zoom_var",
        )

        if not df_zoom.empty and col_nombre in df_zoom.columns:
            if var_zoom == "Tasa de mora (%)":
                labels = df_zoom[col_nombre].tolist()
                values = df_zoom[col_mora].tolist()
                suffix = "%"
            elif var_zoom == "Saldo total (miles de $)":
                labels = df_zoom[col_nombre].tolist()
                values = (df_zoom[col_saldo] / 1_000_000).tolist()
                suffix = "M"
            else:
                labels = df_zoom[col_nombre].tolist()
                values = (df_zoom[col_irreg] / 1_000_000).tolist()
                suffix = "M"

            with st.container(border=True):
                st.plotly_chart(
                    fig_barras_h(
                        f"{var_zoom} · {sector_zoom} (por actividad)",
                        labels, values, suffix=suffix,
                    ),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

            # Scatter mora vs saldo a nivel 2 dígitos
            if col_mora in df_zoom.columns and col_saldo in df_zoom.columns:
                with st.container(border=True):
                    st.plotly_chart(
                        fig_scatter_mora(
                            df_zoom.dropna(subset=[col_mora, col_saldo]),
                            x_col=col_saldo,
                            y_col=col_mora,
                            label_col=col_nombre,
                            title=f"Saldo vs Tasa de mora · {sector_zoom}",
                        ),
                        use_container_width=True,
                        config={"displayModeBar": False},
                    )
        else:
            st.info("No hay datos de actividades (2 dígitos) para este sector, o falta la columna 'Nombre'.")

        st.markdown(
            '<div style="text-align:center;font-family:\'DM Mono\',monospace;font-size:0.7rem;'
            'color:#aab0c0;letter-spacing:0.05em;margin-top:2rem;">'
            'CEU – Centro de Estudios UIA · Unión Industrial Argentina · 2026</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# Standalone (para probar directo con streamlit run)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(
        page_title="Morosidad – CEU UIA",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    render_morosidad()
