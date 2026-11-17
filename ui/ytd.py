from html import escape

import pandas as pd

from services.metrics import year_to_date


def ytd_pill(df, value_col, date_col="Date", *, mode="december", unit="%"):
    """Annual accumulated change for a card, with its comparison in the tooltip."""
    value, date = year_to_date(df, value_col, date_col, mode=mode, difference=unit != "%")
    label = f"acum. {date.year}" if pd.notna(date) else "acum. anual"
    if pd.isna(date):
        detail = "Sin datos disponibles."
    elif mode == "sum":
        detail = (f"Enero–{date:%m/%Y} vs igual período de {date.year - 1}. "
                  "Se requieren todos los meses de ambos períodos.")
    else:
        detail = f"Último dato ({date:%d/%m/%Y}) vs último dato de diciembre de {date.year - 1}."
    if unit == "p.p.":
        detail += " Cambio en puntos porcentuales."
    elif unit == "mill. USD":
        detail += " Diferencia en millones de USD."
    if pd.isna(value):
        number, arrow = "—", ""
        detail += " Información insuficiente para calcular la variación."
    else:
        number = f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        number += "%" if unit == "%" else f" {unit}"
        arrow = "▲ " if value > 0 else "▼ " if value < 0 else ""
    return (
        f'<div class="fx-pill ytd-pill" title="{escape(detail, quote=True)}" '
        'style="display:inline-flex;align-items:center;gap:8px;padding:7px 10px;'
        'border-radius:12px;border:1px solid #cbdceb;background:#edf4fb;'
        'color:#2C5378;font-size:13px;font-weight:700;white-space:nowrap;max-width:100%;flex-wrap:wrap;">'
        f'<span style="font-weight:900">{arrow}{number}</span>'
        f'<span class="lab">{label}</span></div>'
    )
