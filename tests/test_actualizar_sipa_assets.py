import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pandas as pd

from scripts.actualizar_sipa_assets import (
    SIPA_OUTPUT_FILES,
    _validar_outputs,
    _urls_sipa_en_html,
    extraer_serie_col_b,
    fuente_ya_procesada,
    parse_mes,
    resolver_latest_sipa_xlsx_url,
)


class ActualizarSipaAssetsTests(unittest.TestCase):
    def test_interpreta_datetime_de_python_sin_intercambiar_mes_y_dia(self):
        self.assertEqual(parse_mes(datetime(2026, 7, 1)), pd.Timestamp("2026-07-01"))

    def test_conserva_todos_los_meses_cuando_excel_entrega_datetime(self):
        raw = pd.DataFrame(
            [
                ["Período", "Valor"],
                *[
                    [datetime(2025, month, 1), float(month)]
                    for month in range(1, 13)
                ],
            ]
        )

        result = extraer_serie_col_b(raw)

        self.assertEqual(len(result), 12)
        self.assertEqual(result["fecha"].dt.month.tolist(), list(range(1, 13)))

    def test_detecta_la_publicacion_mas_reciente_con_url_relativa(self):
        html = """
        <a href="/sites/default/files/trabajoregistrado_2607_estadisticas.xlsx">Anterior</a>
        <a href="/sites/default/files/trabajoregistrado_2609_estadisticas.xlsx">Actual</a>
        """

        self.assertEqual(
            _urls_sipa_en_html(html)[0],
            "https://www.argentina.gob.ar/sites/default/files/"
            "trabajoregistrado_2609_estadisticas.xlsx",
        )

    def test_resuelve_desde_la_pagina_sin_probar_archivos(self):
        response = Mock()
        response.text = (
            '<a href="https://www.argentina.gob.ar/sites/default/files/'
            'trabajoregistrado_2608_estadisticas.xlsx">Estadísticas</a>'
        )
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        result = resolver_latest_sipa_xlsx_url(session)

        self.assertTrue(result.endswith("trabajoregistrado_2608_estadisticas.xlsx"))
        session.get.assert_called_once()

    def test_omite_descarga_si_la_fuente_y_los_csv_no_cambiaron(self):
        source_url = (
            "https://www.argentina.gob.ar/sites/default/files/"
            "trabajoregistrado_2608_estadisticas.xlsx"
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in SIPA_OUTPUT_FILES:
                (directory / name).write_text("fecha,valor\n", encoding="utf-8")
            metadata = directory / "actualizacion.json"
            metadata.write_text(json.dumps({"source_url": source_url}), encoding="utf-8")

            self.assertTrue(
                fuente_ya_procesada(
                    source_url,
                    sipa_dir=directory,
                    metadata_path=metadata,
                )
            )
            self.assertFalse(
                fuente_ya_procesada(
                    source_url,
                    force=True,
                    sipa_dir=directory,
                    metadata_path=metadata,
                )
            )

    def test_rechaza_una_serie_que_pierde_meses_recientes(self):
        fechas = pd.date_range("2024-08-01", "2026-07-01", freq="MS").delete(20)
        frames = {
            name: pd.DataFrame({"fecha": fechas, "valor": range(len(fechas))})
            for name in SIPA_OUTPUT_FILES
        }

        with self.assertRaisesRegex(RuntimeError, "perdió meses recientes"):
            _validar_outputs(frames)

    def test_rechaza_una_serie_que_retrocede(self):
        fechas = pd.date_range("2024-08-01", "2026-07-01", freq="MS")
        frames = {
            name: pd.DataFrame({"fecha": fechas, "valor": range(len(fechas))})
            for name in SIPA_OUTPUT_FILES
        }
        anteriores = {
            name: pd.Timestamp("2026-08-01") for name in SIPA_OUTPUT_FILES
        }

        with self.assertRaisesRegex(RuntimeError, "retrocede"):
            _validar_outputs(frames, ultimas_anteriores=anteriores)


if __name__ == "__main__":
    unittest.main()
