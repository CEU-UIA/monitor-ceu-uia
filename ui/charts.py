"""Configuración visual compartida para los gráficos Plotly del monitor."""

from __future__ import annotations

from datetime import date, datetime
import re
import unicodedata
from typing import Any

import pandas as pd
import streamlit as st


CHART_FONT = 'Montserrat, "Segoe UI", Arial, sans-serif'
CHART_TEXT_COLOR = "#0b2b4c"
CHART_BACKGROUND = "#ffffff"
CHART_PRIMARY_COLOR = "#2C5378"
CHART_COLORWAY = [
    CHART_PRIMARY_COLOR,
    "#EF553B",
    "#00CC96",
    "#AB63FA",
    "#FFA15A",
    "#19D3F3",
    "#FF6692",
    "#B6E880",
    "#FF97FF",
    "#FECB52",
]

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


def _as_list(values: Any) -> list[Any]:
    """Normaliza los arreglos de Plotly sin convertir strings en caracteres."""
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        return [values]
    try:
        return list(values)
    except TypeError:
        return [values]


def _clean_category(value: Any) -> Any:
    """Quita etiquetas HTML usadas solo para resaltar categorías del gráfico."""
    if isinstance(value, str):
        return re.sub(r"<[^>]+>", "", value)
    return value


def chart_data_frame(fig: Any) -> pd.DataFrame:
    """Extrae en formato largo los datos efectivamente representados."""
    rows: list[dict[str, Any]] = []
    figure_title = getattr(getattr(fig.layout, "title", None), "text", None)

    for trace_index, trace in enumerate(fig.data, start=1):
        x_values = _as_list(getattr(trace, "x", None))
        y_values = _as_list(getattr(trace, "y", None))
        orientation = getattr(trace, "orientation", None)
        custom_values = _as_list(getattr(trace, "customdata", None))

        if orientation == "h":
            categories = custom_values if len(custom_values) == len(y_values) else y_values
            values = x_values
        else:
            categories = x_values or list(range(1, len(y_values) + 1))
            values = y_values

        row_count = max(len(categories), len(values))
        series_name = (
            getattr(trace, "name", None)
            or figure_title
            or f"Serie {trace_index}"
        )
        series_name = _clean_category(series_name)

        for row_index in range(row_count):
            category = categories[row_index] if row_index < len(categories) else None
            value = values[row_index] if row_index < len(values) else None
            rows.append(
                {
                    "serie": series_name,
                    "fecha_o_categoria": _clean_category(category),
                    "valor": value,
                }
            )

    return pd.DataFrame(
        rows,
        columns=["serie", "fecha_o_categoria", "valor"],
    )


def _csv_bytes(data: pd.DataFrame) -> bytes:
    """Genera un CSV UTF-8 con BOM para que Excel reconozca los acentos."""
    return data.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8-sig")


def apply_chart_style(fig: Any) -> Any:
    """Aplica el estándar visual y numérico del monitor a una figura."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=CHART_BACKGROUND,
        plot_bgcolor=CHART_BACKGROUND,
        colorway=CHART_COLORWAY,
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
    show_csv_download: bool = True,
    **kwargs: Any,
):
    """Renderiza Plotly con estilo español y descargas PNG/CSV habilitadas."""
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

    chart_result = st.plotly_chart(fig, config=chart_config, key=key, **kwargs)

    if show_csv_download:
        download_name = _safe_image_filename(image_filename or key)
        st.download_button(
            "⬇️ Descargar datos (CSV)",
            data=_csv_bytes(chart_data_frame(fig)),
            file_name=f"{download_name}.csv",
            mime="text/csv",
            key=f"csv_{download_name}",
        )

    return chart_result
