import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.actualizar_sipa_assets import (
    SIPA_OUTPUT_FILES,
    _urls_sipa_en_html,
    fuente_ya_procesada,
    resolver_latest_sipa_xlsx_url,
)


class ActualizarSipaAssetsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
