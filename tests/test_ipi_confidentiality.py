import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd


spec = importlib.util.spec_from_file_location(
    "ipi_data_under_test", Path(__file__).resolve().parents[1] / "services/ipi_data.py"
)
ipi = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"streamlit": types.SimpleNamespace(cache_data=lambda **kw: lambda f: f)}):
    spec.loader.exec_module(ipi)


class ConfidentialityTests(unittest.TestCase):
    def sheet(self, values):
        rows = [[None] * 4 for _ in range(6)]
        rows += [[None, "2026*" if i == 0 else None, month, value]
                 for i, (month, value) in enumerate(zip(["Enero", "Febrero", "Marzo"], values))]
        rows += [[None] * 4]
        return pd.DataFrame(rows)

    def test_latest_secret_does_not_fall_back_to_old_public_value(self):
        for marker in ["s", " S ", "s."]:
            with self.subTest(marker=marker):
                self.assertTrue(ipi.procesar_serie_excel(self.sheet([100, 110, marker]), 3).empty)

    def test_published_aggregate_is_preserved(self):
        result = ipi.procesar_serie_excel(self.sheet([100, 110, 120]), 3)
        self.assertEqual(result.valor.tolist(), [100, 110, 120])
        self.assertEqual(result.fecha.iloc[-1], pd.Timestamp("2026-03-01"))

    def test_historical_secret_is_not_filled_or_converted_to_zero(self):
        result = ipi.procesar_serie_excel(self.sheet([100, "s", 120]), 3)
        self.assertEqual(result.valor.tolist(), [100, 120])
        self.assertEqual(result.fecha.dt.month.tolist(), [1, 3])


if __name__ == "__main__":
    unittest.main()
