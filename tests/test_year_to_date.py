import unittest

import numpy as np
import pandas as pd

from services.metrics import year_to_date
from ui.ytd import ytd_pill


class YearToDateTests(unittest.TestCase):
    def frame(self, dates, values):
        return pd.DataFrame({"Date": pd.to_datetime(dates), "Value": values})

    def test_daily_uses_last_december_quote_not_january_first(self):
        df = self.frame(["2025-12-30", "2026-01-02", "2026-08-18"], [100, 110, 120])
        value, date = year_to_date(df, "Value")
        self.assertAlmostEqual(value, 20)
        self.assertEqual(date, pd.Timestamp("2026-08-18"))

    def test_old_series_uses_its_year_not_the_current_year(self):
        df = self.frame(["2023-12-01", "2024-06-01"], [100, 90])
        value, date = year_to_date(df, "Value")
        self.assertAlmostEqual(value, -10)
        self.assertEqual(date.year, 2024)

    def test_price_index_compounds_monthly_changes(self):
        df = self.frame(["2025-12-01", "2026-01-01", "2026-02-01"], [100, 110, 121])
        self.assertAlmostEqual(year_to_date(df, "Value")[0], 21)

    def test_rates_use_percentage_points_including_zero_baseline(self):
        df = self.frame(["2025-12-30", "2026-03-04"], [0, 2])
        self.assertEqual(year_to_date(df, "Value", difference=True)[0], 2)
        self.assertTrue(np.isnan(year_to_date(df, "Value")[0]))
        self.assertIn("2,0 p.p.", ytd_pill(df, "Value", unit="p.p."))

    def test_activity_uses_ratio_of_sums_not_mean_of_growth_rates(self):
        df = self.frame(["2025-01-01", "2025-02-01", "2026-01-01", "2026-02-01"], [100, 300, 120, 330])
        self.assertAlmostEqual(year_to_date(df, "Value", mode="sum")[0], 12.5)

    def test_activity_ignores_later_months_in_comparison_year(self):
        df = self.frame(["2025-01-01", "2025-02-01", "2026-01-01"], [100, 999, 120])
        self.assertAlmostEqual(year_to_date(df, "Value", mode="sum")[0], 20)

    def test_activity_requires_all_months_on_both_sides(self):
        full = self.frame(["2025-01-01", "2025-02-01", "2026-01-01", "2026-02-01"], [100]*4)
        for missing in [0, 1, 2]:
            with self.subTest(missing=missing):
                self.assertTrue(np.isnan(year_to_date(full.drop(missing), "Value", mode="sum")[0]))

    def test_no_december_does_not_silently_use_november(self):
        df = self.frame(["2025-11-01", "2026-01-01"], [100, 120])
        self.assertTrue(np.isnan(year_to_date(df, "Value")[0]))

    def test_unsorted_data_and_missing_latest_values(self):
        df = self.frame(["2026-04-01", "2026-03-01", "2025-12-01"], [np.nan, 120, 100])
        value, date = year_to_date(df, "Value")
        self.assertAlmostEqual(value, 20)
        self.assertEqual(date, pd.Timestamp("2026-03-01"))

    def test_empty_or_missing_columns_show_neutral_placeholder(self):
        for df in [None, pd.DataFrame(), self.frame([], [])]:
            with self.subTest(df=df):
                self.assertTrue(np.isnan(year_to_date(df, "Value")[0]))
                html = ytd_pill(df, "Value")
                self.assertIn("—", html)
                self.assertNotIn("nan", html)
                self.assertNotIn("▼", html)

    def test_trade_balance_uses_absolute_accumulated_difference(self):
        df = self.frame(["2025-01-01", "2025-02-01", "2026-01-01", "2026-02-01"], [-10, -20, 10, 20])
        self.assertEqual(year_to_date(df, "Value", mode="sum", difference=True)[0], 60)
        self.assertIn("60,0 mill. USD", ytd_pill(df, "Value", mode="sum", unit="mill. USD"))

    def test_custom_column_names_and_display_period(self):
        df = pd.DataFrame({"Periodo": pd.to_datetime(["2025-12-01", "2026-07-01"]), "Indice": [100, 105]})
        html = ytd_pill(df, "Indice", "Periodo")
        self.assertIn("5,0%", html)
        self.assertIn("acum. 2026", html)
        self.assertIn("01/07/2026", html)
        self.assertIn("diciembre de 2025", html)


if __name__ == "__main__":
    unittest.main()
