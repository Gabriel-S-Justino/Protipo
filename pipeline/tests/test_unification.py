from contextlib import nullcontext
from datetime import date
from unittest.mock import patch
import pytest
from pipeline.analytics import harmonize


class Rows(list):
    def close(self):
        pass


class Connection:
    def __init__(self):
        self.inserted = []

    def execute(self, sql, params=None):
        if isinstance(params, list):
            self.inserted.extend(params)
        return self

    def scalar_one(self):
        return 99


def run_unification(model):
    conn = Connection()
    first, second, third = date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)
    rows = Rows(
        [
            {
                "gx": -79,
                "gy": -10,
                "day": first,
                "instrument": "MODIS",
                "code": "MODIS_SP",
                "value": 10,
            },
            {
                "gx": -79,
                "gy": -10,
                "day": second,
                "instrument": "VIIRS",
                "code": "VIIRS_SNPP_SP",
                "value": 3,
            },
            {
                "gx": -79,
                "gy": -10,
                "day": third,
                "instrument": "MODIS",
                "code": "MODIS_SP",
                "value": 4,
            },
        ]
    )
    with patch("pipeline.analytics.get_engine") as engine, patch(
        "pipeline.analytics._country", return_value=76
    ), patch(
        "pipeline.analytics._coverage",
        return_value=(
            {first: "VIIRS_SNPP_SP", second: "VIIRS_SNPP_SP"},
            {first: "MODIS_SP", third: "MODIS_SP"},
        ),
    ), patch(
        "pipeline.analytics._raw", return_value=rows
    ), patch(
        "pipeline.analytics._upsert_cell", return_value=1
    ), patch(
        "pipeline.analytics.calibrate", return_value=model
    ):
        engine.return_value.begin.return_value = nullcontext(conn)
        harmonize()
    return {row["day"]: row for row in conn.inserted if row["kind"] == "day"}


def test_covered_zero_viirs_is_not_replaced_by_positive_modis():
    rows = run_unification({"factor": 2, "low": 1.5, "high": 2.5, "validated": True})
    assert date(2020, 1, 1) not in rows
    assert rows[date(2020, 1, 2)]["value"] == 3


def test_modis_contributes_only_as_calibrated_viirs_equivalent():
    rows = run_unification({"factor": 2, "low": 1.5, "high": 2.5, "validated": True})
    row = rows[date(2020, 1, 3)]
    assert row["value"] == 8 and row["lo"] == 6 and row["hi"] == 10
    assert row["source"] == "modis_harmonized"


def test_no_neutral_conversion_when_model_is_missing():
    rows = run_unification(None)
    assert set(rows) == {date(2020, 1, 2)}
