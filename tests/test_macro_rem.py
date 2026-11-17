import importlib.util
import sys
import types
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import requests


# Cargar el servicio sin iniciar Streamlit ni compartir su caché entre pruebas.
spec = importlib.util.spec_from_file_location(
    "macro_data_under_test", Path(__file__).resolve().parents[1] / "services/macro_data.py"
)
macro = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"streamlit": types.SimpleNamespace(cache_data=lambda **kw: lambda f: f)}):
    spec.loader.exec_module(macro)


class RemTests(unittest.TestCase):
    def setUp(self):
        self.base = macro.build_bands_2025("2025-04-14", "2025-12-31", 1000, 1400)
        self.empty_rem = pd.DataFrame({"Date": pd.Series(dtype="datetime64[ns]"),
                                       "v_m_REM": pd.Series(dtype=float)})

    def ipc(self, periods):
        return pd.DataFrame({"Period": pd.PeriodIndex(periods, freq="M"),
                             "v_m_CPI": [0.02] * len(periods)})

    def test_download_and_latest_forecast(self):
        df = pd.DataFrame({
            "Variable": ["Precios minoristas (IPC nivel general; INDEC)"] * 3,
            "Referencia": ["var. % mensual"] * 3,
            "Fecha de pronóstico": pd.to_datetime(["2026-09-30", "2026-10-31", "2026-10-31"]),
            "Período": pd.to_datetime(["2026-11-01", "2026-12-01", "2026-11-01"]),
            "Mediana": [9.0, 1.5, 1.8],
        })
        buf = BytesIO()
        df.to_excel(buf, sheet_name="Base de Datos Completa", startrow=1, index=False)
        with patch.object(macro.requests, "get", return_value=Mock(content=buf.getvalue())) as get:
            result = macro.get_rem_last()
        self.assertEqual(result.v_m_REM.tolist(), [1.8, 1.5])
        self.assertIn("/informes/relevamiento-expectativas-mercado-historico.xlsx", get.call_args.args[0])
        self.assertEqual(get.call_args.kwargs["timeout"], 30)

    def test_http_error_and_timeout_return_typed_empty(self):
        for error in [requests.HTTPError("404"), requests.Timeout("timeout")]:
            with self.subTest(error=error), patch.object(macro.requests, "get", side_effect=error):
                result = macro.get_rem_last()
            self.assertTrue(result.empty)
            self.assertEqual(str(result.Date.dtype), "datetime64[ns]")

    def test_html_instead_of_excel(self):
        with patch.object(macro.requests, "get", return_value=Mock(content=b"<html>Unavailable</html>")):
            self.assertTrue(macro.get_rem_last().empty)

    def test_no_rem_uses_observed_ipc_only(self):
        result = macro.build_bands_2026(self.base, self.empty_rem, self.ipc(["2025-11", "2025-12"]))
        self.assertEqual(result.Date.max(), pd.Timestamp("2026-02-28"))
        self.assertFalse(result.isna().any().any())

    def test_no_data_returns_empty(self):
        self.assertTrue(macro.build_bands_2026(self.base, self.empty_rem, self.ipc([])).empty)

    def test_gap_stops_compounding(self):
        result = macro.build_bands_2026(self.base, self.empty_rem, self.ipc(["2025-11", "2026-01"]))
        self.assertEqual(result.Date.max(), pd.Timestamp("2026-01-31"))

    def test_observed_ipc_takes_precedence_over_rem(self):
        rem = pd.DataFrame({"Date": pd.to_datetime(["2025-11-01", "2025-12-01"]), "v_m_REM": [99, 2]})
        actual = macro.build_bands_2026(self.base, rem, self.ipc(["2025-11"]))
        expected = macro.build_bands_2026(self.base, self.empty_rem, self.ipc(["2025-11", "2025-12"]))
        pd.testing.assert_frame_equal(actual, expected)


if __name__ == "__main__":
    unittest.main()
