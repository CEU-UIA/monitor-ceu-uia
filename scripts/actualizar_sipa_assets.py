"""Actualiza los CSV de empleo que consume el monitor.

El script está pensado para ejecutarse fuera de Streamlit (por ejemplo, desde
GitHub Actions). En cada corrida consulta la página oficial de SIPA y solo
descarga/procesa el Excel cuando encuentra una publicación nueva.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
SIPA_DIR = ROOT / "assets" / "sipa"
SIPA_DIR.mkdir(parents=True, exist_ok=True)

SIPA_LANDING_PAGE = (
    "https://www.argentina.gob.ar/trabajo/estadisticas/"
    "situacion-y-evolucion-del-trabajo-registrado"
)
SIPA_METADATA_FILE = SIPA_DIR / "actualizacion.json"
SIPA_OUTPUT_FILES = (
    "sipa_total.csv",
    "sipa_sec_orig.csv",
    "sipa_sec_sa.csv",
    "sipa_sub_orig.csv",
    "sipa_sub_sa.csv",
)

SIPA_XLSX_RE = re.compile(
    r"(?:https?:)?//[^\"'<>\s]+/sites/default/files/"
    r"trabajoregistrado_(\d{4})_estadisticas\.xlsx"
    r"|/sites/default/files/trabajoregistrado_(\d{4})_estadisticas\.xlsx",
    re.IGNORECASE,
)


def crear_sesion() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": (
                "Monitor-CEU-UIA/1.0 "
                "(actualizador automatico de estadisticas publicas)"
            )
        }
    )
    return session


def _version_desde_url(url: str) -> int:
    match = re.search(r"trabajoregistrado_(\d{4})_estadisticas\.xlsx", url, re.I)
    return int(match.group(1)) if match else -1


def _urls_sipa_en_html(raw_html: str) -> list[str]:
    contenido = html.unescape(raw_html)
    urls: set[str] = set()

    for match in SIPA_XLSX_RE.finditer(contenido):
        raw_url = match.group(0)
        if raw_url.startswith("//"):
            raw_url = f"https:{raw_url}"
        urls.add(urljoin(SIPA_LANDING_PAGE, raw_url))

    return sorted(urls, key=_version_desde_url, reverse=True)


def _meses_recientes(cantidad: int = 18):
    year = date.today().year
    month = date.today().month

    for _ in range(cantidad):
        yield year, month
        month -= 1
        if month == 0:
            month = 12
            year -= 1


def _url_existe(session: requests.Session, url: str) -> bool:
    """Verifica una URL sin descargar el archivo completo."""
    try:
        response = session.get(
            url,
            headers={"Range": "bytes=0-0"},
            stream=True,
            timeout=(5, 12),
        )
        try:
            return response.status_code in (200, 206)
        finally:
            response.close()
    except requests.RequestException:
        return False


def resolver_latest_sipa_xlsx_url(session: requests.Session | None = None) -> str:
    session = session or crear_sesion()

    try:
        response = session.get(SIPA_LANDING_PAGE, timeout=(8, 30))
        response.raise_for_status()
        urls = _urls_sipa_en_html(response.text)
        if urls:
            return urls[0]
    except requests.RequestException as exc:
        print(f"Advertencia: no se pudo leer la página de SIPA: {exc}")

    # Respaldo para cambios temporales en la página. Se prueba primero el mes
    # actual y normalmente se resuelve en una o dos solicitudes livianas.
    for year, month in _meses_recientes():
        yymm = f"{year % 100:02d}{month:02d}"
        url = (
            "https://www.argentina.gob.ar/sites/default/files/"
            f"trabajoregistrado_{yymm}_estadisticas.xlsx"
        )
        if _url_existe(session, url):
            return url

    raise RuntimeError("No se pudo encontrar el XLSX vigente de SIPA.")


def _leer_metadata(path: Path = SIPA_METADATA_FILE) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def fuente_ya_procesada(
    url: str,
    *,
    force: bool = False,
    sipa_dir: Path = SIPA_DIR,
    metadata_path: Path = SIPA_METADATA_FILE,
) -> bool:
    if force:
        return False

    metadata = _leer_metadata(metadata_path)
    outputs_completos = all((sipa_dir / name).is_file() for name in SIPA_OUTPUT_FILES)
    return outputs_completos and metadata.get("source_url") == url


def _descargar_excel(session: requests.Session, url: str, destino: Path) -> str:
    digest = hashlib.sha256()
    total = 0

    with session.get(url, stream=True, timeout=(10, 120)) as response:
        response.raise_for_status()
        with destino.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)
                digest.update(chunk)
                total += len(chunk)

    if total < 1_024:
        raise RuntimeError("La descarga de SIPA está vacía o incompleta.")

    with destino.open("rb") as fh:
        if fh.read(2) != b"PK":
            raise RuntimeError("La URL de SIPA no devolvió un archivo XLSX válido.")

    return digest.hexdigest()


def parse_mes(x):
    if pd.isna(x):
        return pd.NaT

    if isinstance(x, pd.Timestamp):
        return pd.Timestamp(x.year, x.month, 1)

    if isinstance(x, (int, float)) and not pd.isna(x):
        try:
            dt = pd.to_datetime(x, unit="D", origin="1899-12-30", errors="coerce")
            if not pd.isna(dt):
                return pd.Timestamp(dt.year, dt.month, 1)
        except (OverflowError, ValueError):
            pass

    value = str(x).strip().lower()
    if not value:
        return pd.NaT

    value = value.replace("*", "").replace("/", "-").replace(".", "-")
    value = re.sub(r"\s+", "", value)

    match = re.match(r"^(?P<yyyy>\d{4})m(?P<mm>\d{1,2})$", value)
    if match:
        return pd.Timestamp(int(match.group("yyyy")), int(match.group("mm")), 1)

    dt = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if not pd.isna(dt):
        return pd.Timestamp(dt.year, dt.month, 1)

    meses = {
        "ene": 1, "enero": 1,
        "feb": 2, "febrero": 2,
        "mar": 3, "marzo": 3,
        "abr": 4, "abril": 4,
        "may": 5, "mayo": 5,
        "jun": 6, "junio": 6,
        "jul": 7, "julio": 7,
        "ago": 8, "agosto": 8,
        "sep": 9, "set": 9, "sept": 9, "septiembre": 9,
        "oct": 10, "octubre": 10,
        "nov": 11, "noviembre": 11,
        "dic": 12, "diciembre": 12,
    }

    match = re.match(r"^(?P<mon>[a-záéíóúñ]{3,9})-?(?P<yy>\d{2,4})$", value)
    if match:
        month_name = match.group("mon")
        year = int(match.group("yy"))
        if month_name in meses:
            year = year if year > 1900 else 2000 + year
            return pd.Timestamp(year, meses[month_name], 1)

    return pd.NaT


def extraer_serie_col_b(df_raw, col_fecha=0, col_val=1):
    tmp = df_raw.copy()
    tmp = tmp.rename(
        columns={
            tmp.columns[col_fecha]: "fecha_raw",
            tmp.columns[col_val]: "valor_raw",
        }
    )
    tmp["fecha"] = tmp["fecha_raw"].apply(parse_mes)
    tmp["valor"] = pd.to_numeric(tmp["valor_raw"], errors="coerce")

    return (
        tmp.dropna(subset=["fecha", "valor"])[["fecha", "valor"]]
        .drop_duplicates(subset="fecha", keep="last")
        .sort_values("fecha")
        .reset_index(drop=True)
    )


def extraer_sectores(df_raw):
    header = df_raw.iloc[1, 1:].copy().dropna()
    sectores = [str(value).strip() for value in header.tolist() if str(value).strip()]

    if not sectores:
        return pd.DataFrame(columns=["fecha"])

    data = df_raw.iloc[2:, : 1 + len(sectores)].copy()
    data.columns = ["fecha_raw"] + sectores
    data["fecha"] = data["fecha_raw"].apply(parse_mes)
    data = data.dropna(subset=["fecha"]).drop(columns=["fecha_raw"])

    for column in sectores:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    return (
        data.dropna(how="all", subset=sectores)
        .drop_duplicates(subset="fecha", keep="last")
        .sort_values("fecha")
        .reset_index(drop=True)
    )


def extraer_subsectores_industria(df_raw):
    if df_raw is None or df_raw.empty or df_raw.shape[1] < 2:
        return pd.DataFrame(columns=["fecha"])

    col_indices = list(range(1, min(8, df_raw.shape[1])))
    nombres = [str(df_raw.iloc[1, column]).strip() for column in col_indices]

    data = df_raw.iloc[2:, [0] + col_indices].copy()
    data.columns = ["fecha_raw"] + nombres
    data["fecha"] = data["fecha_raw"].apply(parse_mes)
    data = data.dropna(subset=["fecha"]).drop(columns=["fecha_raw"])

    for column in nombres:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    return (
        data.dropna(how="all", subset=nombres)
        .drop_duplicates(subset="fecha", keep="last")
        .sort_values("fecha")
        .reset_index(drop=True)
    )


def filtrar_fechas(df):
    if df.empty or "fecha" not in df.columns:
        return df

    result = df.copy()
    result = result[
        (result["fecha"] >= "2000-01-01") & (result["fecha"] <= "2035-12-01")
    ]
    return result.sort_values("fecha").reset_index(drop=True)


def _procesar_excel(path: Path) -> dict[str, pd.DataFrame]:
    with pd.ExcelFile(path, engine="openpyxl") as workbook:
        required = {"T.2.1", "T.2.2", "A.2.1", "A.2.2", "A.6.1", "A.6.2"}
        missing = required.difference(workbook.sheet_names)
        if missing:
            raise RuntimeError(f"Faltan hojas esperadas en SIPA: {', '.join(sorted(missing))}")

        t21 = pd.read_excel(workbook, sheet_name="T.2.1", header=None, usecols=[0, 1])
        t22 = pd.read_excel(workbook, sheet_name="T.2.2", header=None, usecols=[0, 1])
        a21 = pd.read_excel(
            workbook, sheet_name="A.2.1", header=None, usecols=list(range(17))
        )
        a22 = pd.read_excel(
            workbook, sheet_name="A.2.2", header=None, usecols=list(range(17))
        )
        sub_usecols = [0, 3, 4, 5, 6, 7, 8, 9]
        a61 = pd.read_excel(
            workbook, sheet_name="A.6.1", header=None, usecols=sub_usecols
        )
        a62 = pd.read_excel(
            workbook, sheet_name="A.6.2", header=None, usecols=sub_usecols
        )

    serie_original = extraer_serie_col_b(t21).rename(columns={"valor": "orig"})
    serie_sa = extraer_serie_col_b(t22).rename(columns={"valor": "sa"})

    frames = {
        "sipa_total.csv": serie_original.merge(
            serie_sa, on="fecha", how="inner"
        ).sort_values("fecha"),
        "sipa_sec_orig.csv": extraer_sectores(a21),
        "sipa_sec_sa.csv": extraer_sectores(a22),
        "sipa_sub_orig.csv": extraer_subsectores_industria(a61),
        "sipa_sub_sa.csv": extraer_subsectores_industria(a62),
    }
    return {name: filtrar_fechas(frame) for name, frame in frames.items()}


def _validar_outputs(frames: dict[str, pd.DataFrame]) -> pd.Timestamp:
    for name in SIPA_OUTPUT_FILES:
        frame = frames.get(name)
        if frame is None or frame.empty:
            raise RuntimeError(f"El procesamiento produjo {name} vacío.")
        if "fecha" not in frame.columns:
            raise RuntimeError(f"{name} no contiene la columna fecha.")
        if frame["fecha"].duplicated().any():
            raise RuntimeError(f"{name} contiene fechas duplicadas.")
        if not frame["fecha"].is_monotonic_increasing:
            raise RuntimeError(f"{name} no quedó ordenado por fecha.")

    latest = {name: frame["fecha"].max() for name, frame in frames.items()}
    if len(set(latest.values())) != 1:
        detail = ", ".join(f"{name}: {value:%Y-%m}" for name, value in latest.items())
        raise RuntimeError(f"Las series de SIPA terminan en períodos distintos ({detail}).")

    return next(iter(latest.values()))


def _guardar_outputs(
    frames: dict[str, pd.DataFrame],
    metadata: dict,
    *,
    sipa_dir: Path = SIPA_DIR,
) -> None:
    sipa_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="sipa_output_", dir=sipa_dir.parent) as tmp:
        staging = Path(tmp)
        for name, frame in frames.items():
            # Los CSV históricos del repositorio usan CRLF. Mantenerlo evita
            # diffs completos cuando solo se agrega un período nuevo.
            frame.to_csv(
                staging / name,
                index=False,
                encoding="utf-8-sig",
                lineterminator="\r\n",
            )
        (staging / SIPA_METADATA_FILE.name).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        for name in (*SIPA_OUTPUT_FILES, SIPA_METADATA_FILE.name):
            os.replace(staging / name, sipa_dir / name)


def actualizar(*, force: bool = False) -> bool:
    session = crear_sesion()
    url = resolver_latest_sipa_xlsx_url(session)
    print(f"Fuente SIPA detectada: {url}")

    if fuente_ya_procesada(url, force=force):
        print("Sin cambios: la publicación ya fue procesada.")
        return False

    with tempfile.TemporaryDirectory(prefix="sipa_download_") as tmp:
        workbook_path = Path(tmp) / "sipa.xlsx"
        print("Descargando la nueva publicación...")
        sha256 = _descargar_excel(session, url, workbook_path)
        frames = _procesar_excel(workbook_path)

    latest_date = _validar_outputs(frames)
    metadata = {
        "source_url": url,
        "source_version": f"{_version_desde_url(url):04d}",
        "source_sha256": sha256,
        "latest_data_date": latest_date.strftime("%Y-%m-%d"),
        "processed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _guardar_outputs(frames, metadata)

    print("OK. Archivos guardados en assets/sipa/.")
    print(f"Última fecha disponible: {latest_date.date()}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="descarga y procesa nuevamente la publicación aunque ya esté registrada",
    )
    args = parser.parse_args()
    actualizar(force=args.force)


if __name__ == "__main__":
    main()
