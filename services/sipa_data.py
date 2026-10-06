from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
SIPA_DIR = ROOT / "assets" / "sipa"
SIPA_FILES = (
    "sipa_total.csv",
    "sipa_sec_orig.csv",
    "sipa_sec_sa.csv",
    "sipa_sub_orig.csv",
    "sipa_sub_sa.csv",
)


def _leer_csv_sipa(nombre_archivo: str) -> pd.DataFrame:
    path = SIPA_DIR / nombre_archivo

    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    df = pd.read_csv(path)

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df = df.dropna(subset=["fecha"]).sort_values("fecha").reset_index(drop=True)

    return df


def _firma_assets_sipa() -> tuple[tuple[str, int, int], ...]:
    """Firma liviana para invalidar la caché si cambia algún CSV."""
    firma = []
    for nombre in SIPA_FILES:
        path = SIPA_DIR / nombre
        stat = path.stat()
        firma.append((nombre, stat.st_mtime_ns, stat.st_size))
    return tuple(firma)


@st.cache_data(show_spinner=False)
def _cargar_sipa_cacheado(firma_assets):
    # firma_assets forma parte de la clave de caché. No hace falta utilizarla
    # dentro de la función: cambia cuando GitHub Actions reemplaza los CSV.
    del firma_assets

    return tuple(_leer_csv_sipa(nombre) for nombre in SIPA_FILES)


def cargar_sipa_excel():
    """
    Mantengo el mismo nombre para no tocar empleo.py.

    Antes:
      - resolvía URL
      - descargaba Excel
      - parseaba hojas
      - cacheaba

    Ahora:
      - solo lee CSV locales generados por scripts/actualizar_sipa_assets.py
    """
    try:
        return _cargar_sipa_cacheado(_firma_assets_sipa())

    except Exception as e:
        st.error(f"No se pudieron cargar los datos SIPA locales: {e}")

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )
