"""Scientific regressions: no invented zeros, no leakage and no neutral fallback."""

import unittest
from datetime import date, timedelta
from pipeline.science import calibrate, calendar_rows, probability, period_days


class ScienceTests(unittest.TestCase):
    def test_zero_detection_years_are_in_denominator(self):
        result = probability([(2020, 0), (2021, 12), (2022, 0)])
        self.assertAlmostEqual(result["probability"], 1 / 3)
        self.assertLess(result["ci_low"], 1 / 3)
        self.assertGreater(result["ci_high"], 1 / 3)

    def test_missing_acquisition_is_not_a_zero_year(self):
        covered = set()
        for year in (2020, 2021, 2022):
            covered.update(period_days(date(year, 1, 1), "month"))
        daily = {date(2021, 1, 15): 2}
        rows = calendar_rows(daily, covered, "month", date(2026, 1, 1))
        self.assertAlmostEqual(rows[1]["probability"], 1 / 3)
        covered.remove(date(2022, 1, 16))
        self.assertEqual(calendar_rows(daily, covered, "month", date(2026, 1, 1)), {})

    def test_current_period_is_excluded(self):
        covered = set(period_days(date(2026, 1, 1), "month"))
        self.assertEqual(calendar_rows({}, covered, "month", date(2026, 1, 20)), {})

    def test_week_53_is_not_assigned_to_next_calendar_year(self):
        covered = set()
        for y in (2009, 2015, 2020):
            d = date.fromisocalendar(y, 53, 1)
            covered.update(period_days(d, "week"))
        result = calendar_rows({date(2021, 1, 1): 1}, covered, "week", date(2026, 1, 1))
        self.assertEqual(result[53]["years_used"], 3)
        self.assertAlmostEqual(result[53]["probability"], 1 / 3)

    def test_no_calibration_without_three_years(self):
        self.assertIsNone(calibrate([(2022, 10, 20)] * 12))
        self.assertIsNone(calibrate([]))

    def test_calibration_and_year_bootstrap(self):
        pairs = [(y, 10, 20) for y in (2020, 2021, 2022) for _ in range(6)]
        model = calibrate(pairs)
        self.assertEqual(model["factor"], 2)
        self.assertEqual(model["low"], 2)
        self.assertEqual(model["high"], 2)
        self.assertEqual(model["mae"], 0)
        self.assertTrue(model["validated"])

    def test_brier_does_not_train_on_future_years(self):
        result = probability([(2020, 0), (2021, 0), (2022, 0), (2023, 1)])
        self.assertEqual(result["validation"]["test_years"], 1)
        self.assertAlmostEqual(result["validation"]["brier_score"], (1 - 0.5 / 4) ** 2)

    def test_zero_reference_is_not_discarded_from_calibration(self):
        pairs = [(y, 10, 0) for y in (2020, 2021, 2022) for _ in range(6)]
        self.assertIsNone(calibrate(pairs))


if __name__ == "__main__":
    unittest.main()
