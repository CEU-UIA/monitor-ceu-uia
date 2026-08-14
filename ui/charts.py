"""Configuración visual compartida para los gráficos Plotly del monitor."""

from __future__ import annotations

from datetime import date, datetime
import re
import unicodedata
from typing import Any

import streamlit as st


CHART_FONT = 'Montserrat, "Segoe UI", Arial, sans-serif'
CHART_TEXT_COLOR = "#0b2b4c"
CHART_BACKGROUND = "#ffffff"

# Se deja únicamente la descarga como imagen. Así la opción queda siempre
# disponible sin sumar controles de navegación que no utiliza el tablero.
_MODEBAR_BUTTONS_TO_REMOVE = [
    "zoom2d",
    "pan2d",
    "select2d",
    "lasso2d",
    "zoomIn2d",
    "zoomOut2d",
    "autoScale2d",
    "resetScale2d",
    "hoverClosestCartesian",
    "hoverCompareCartesian",
    "toggleSpikelines",
]

_DATE_TICKFORMAT_STOPS = [
    dict(dtickrange=[None, 86_400_000], value="%d/%m<br>%H:%M"),
    dict(dtickrange=[86_400_000, "M1"], value="%d/%m/%Y"),
    dict(dtickrange=["M1", "M12"], value="%m/%Y"),
    dict(dtickrange=["M12", None], value="%Y"),
]


def _safe_image_filename(value: str | None) -> str:
    """Devuelve un nombre estable y válido para la descarga del PNG."""
    base = str(value or "grafico_ceu_uia").strip().lower()
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-z0-9_-]+", "_", base).strip("_")
    return base or "grafico_ceu_uia"


def _is_date_like(value: Any) -> bool:
    """Reconoce fechas de Python, pandas y NumPy sin sumar dependencias."""
    if isinstance(value, (date, datetime)):
        return True
    value_type = type(value)
    return value_type.__name__ in {"Timestamp", "datetime64"}


def _apply_spanish_date_axes(fig: Any) -> None:
    """Evita abreviaturas de meses en inglés aun si falla el locale del navegador."""
    date_axes: set[str] = set()
    for trace in fig.data:
        values = getattr(trace, "x", None)
        if values is None:
            continue
        first = next((value for value in values if value is not None), None)
        if not _is_date_like(first):
            continue
        axis_ref = getattr(trace, "xaxis", None) or "x"
        date_axes.add("xaxis" if axis_ref == "x" else f"xaxis{axis_ref[1:]}")

    for axis_name in date_axes:
        axis = getattr(fig.layout, axis_name, None)
        if axis is None:
            continue
        updates = {"hoverformat": "%d/%m/%Y"}
        if axis.tickformat is None and axis.ticktext is None:
            updates["tickformatstops"] = _DATE_TICKFORMAT_STOPS
        axis.update(**updates)


def apply_chart_style(fig: Any) -> Any:
    """Aplica el estándar visual y numérico del monitor a una figura."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=CHART_BACKGROUND,
        plot_bgcolor=CHART_BACKGROUND,
        separators=",.",  # decimal con coma y miles con punto
        font=dict(family=CHART_FONT, color=CHART_TEXT_COLOR),
        hoverlabel=dict(font=dict(family=CHART_FONT)),
    )
    fig.update_xaxes(
        tickfont=dict(family=CHART_FONT, color=CHART_TEXT_COLOR),
        title_font=dict(family=CHART_FONT, color=CHART_TEXT_COLOR),
    )
    fig.update_yaxes(
        tickfont=dict(family=CHART_FONT, color=CHART_TEXT_COLOR),
        title_font=dict(family=CHART_FONT, color=CHART_TEXT_COLOR),
    )
    _apply_spanish_date_axes(fig)
    return fig


def plotly_chart(
    fig: Any,
    *,
    config: dict[str, Any] | None = None,
    key: str | None = None,
    image_filename: str | None = None,
    **kwargs: Any,
):
    """Renderiza Plotly con estilo español y descarga PNG habilitada."""
    apply_chart_style(fig)

    chart_config = dict(config or {})
    image_options = dict(chart_config.get("toImageButtonOptions") or {})
    image_options.update(
        {
            "format": "png",
            "filename": _safe_image_filename(image_filename or key),
            "scale": 2,
        }
    )

    chart_config.update(
        {
            "displayModeBar": True,
            "displaylogo": False,
            "locale": "es",
            "responsive": True,
            "scrollZoom": False,
            "toImageButtonOptions": image_options,
            "modeBarButtonsToRemove": _MODEBAR_BUTTONS_TO_REMOVE,
        }
    )

    return st.plotly_chart(fig, config=chart_config, key=key, **kwargs)
