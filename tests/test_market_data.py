import unittest

from services.market_data import _normalise_ccl_argentina_datos


class NormaliseCclArgentinaDatosTests(unittest.TestCase):
    def test_uses_sell_filters_weekends_and_repairs_isolated_spike(self):
        payload = [
            {"fecha": "2025-05-01", "compra": 1189.0, "venta": 1190.0},
            {"fecha": "2025-05-02", "compra": 1428.0, "venta": 1429.3},
            {"fecha": "2025-05-03", "compra": 1428.0, "venta": 1429.3},
            {"fecha": "2025-05-04", "compra": 1428.0, "venta": 1429.3},
            {"fecha": "2025-05-05", "compra": 1211.0, "venta": 1212.6},
        ]

        result = _normalise_ccl_argentina_datos(payload)

        self.assertEqual(result["Date"].dt.strftime("%Y-%m-%d").tolist(), [
            "2025-05-01",
            "2025-05-02",
            "2025-05-05",
        ])
        spike = result.loc[result["Date"] == "2025-05-02"].iloc[0]
        self.assertEqual(spike["value_raw"], 1429.3)
        self.assertAlmostEqual(spike["value"], (1190.0 + 1212.6) / 2.0)
        self.assertTrue(spike["adjusted"])

    def test_falls_back_to_buy_when_sell_is_not_positive(self):
        payload = [
            {"fecha": "2026-08-17", "compra": 1571.1, "venta": 0},
        ]

        result = _normalise_ccl_argentina_datos(payload)

        self.assertEqual(result.iloc[0]["value"], 1571.1)
        self.assertFalse(result.iloc[0]["adjusted"])

    def test_does_not_flatten_a_sustained_market_move(self):
        payload = [
            {"fecha": "2026-08-17", "compra": 99.0, "venta": 100.0},
            {"fecha": "2026-08-18", "compra": 119.0, "venta": 120.0},
            {"fecha": "2026-08-19", "compra": 139.0, "venta": 140.0},
        ]

        result = _normalise_ccl_argentina_datos(payload)

        self.assertEqual(result["value"].tolist(), [100.0, 120.0, 140.0])
        self.assertFalse(result["adjusted"].any())

    def test_returns_empty_schema_for_invalid_payload(self):
        result = _normalise_ccl_argentina_datos({"fecha": "2026-08-21"})

        self.assertTrue(result.empty)
        self.assertEqual(
            result.columns.tolist(),
            ["Date", "value", "buy", "sell", "value_raw", "adjusted", "source"],
        )


if __name__ == "__main__":
    unittest.main()
