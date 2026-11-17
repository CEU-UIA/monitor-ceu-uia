import numpy as np
import pandas as pd


def fmt(n, dec: int = 2, es_puestos: bool = False) -> str:
    if pd.isna(n) or n is None:
        return "s/d"
    formatted = f"{n:,.0f}" if es_puestos else f"{n:,.{dec}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def obtener_nombre_mes(fecha) -> str:
    if pd.isna(fecha):
        return "s/d"
    meses = [
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]
    return f"{meses[fecha.month - 1]} {fecha.year}"


def calc_var(serie: pd.Series, lag: int) -> float:
    if len(serie) <= lag:
        return np.nan
    den = serie.iloc[-lag - 1]
    if den == 0 or pd.isna(den):
        return np.nan
    return (serie.iloc[-1] / den - 1) * 100


def year_to_date(df, value_col, date_col="Date", *, mode="december", difference=False):
    """Return (change, latest valid date), independently of chart date filters.

    december: latest level vs last observation in the preceding December.
    sum: January through latest month vs the SAME complete months a year earlier.
    difference=True returns an absolute difference (e.g. percentage points).
    Missing baselines/months or zero denominators produce NaN, never a partial YTD.
    """
    if mode not in {"december", "sum"}:
        raise ValueError(f"Unsupported YTD mode: {mode}")
    if df is None or not {date_col, value_col}.issubset(df.columns):
        return np.nan, pd.NaT
    dates = pd.to_datetime(df[date_col], errors="coerce", utc=True).dt.tz_convert(None)
    values = pd.to_numeric(df[value_col], errors="coerce").replace([np.inf, -np.inf], np.nan)
    s = pd.DataFrame({"date": dates, "value": values}).dropna().sort_values("date")
    s = s.drop_duplicates("date", keep="last")
    if s.empty:
        return np.nan, pd.NaT
    last = s["date"].iloc[-1]
    if mode == "december":
        base = s[(s["date"].dt.year == last.year - 1) & (s["date"].dt.month == 12)]
        if base.empty:
            return np.nan, last
        current, previous = s["value"].iloc[-1], base["value"].iloc[-1]
    else:
        # One observation per month: only monthly original series belong here.
        monthly = s.set_index(s["date"].dt.to_period("M"))["value"]
        if monthly.index.has_duplicates:
            return np.nan, last
        current_months = pd.period_range(f"{last.year}-01", periods=last.month, freq="M")
        previous_months = current_months - 12
        current_values = monthly.reindex(current_months)
        previous_values = monthly.reindex(previous_months)
        if current_values.isna().any() or previous_values.isna().any():
            return np.nan, last
        current, previous = current_values.sum(), previous_values.sum()
    if difference:
        return float(current - previous), last
    if previous == 0:
        return np.nan, last
    return float((current / previous - 1) * 100), last

