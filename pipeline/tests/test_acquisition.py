from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from pipeline.firms import fetch_area, _cache_path
from pipeline.geography import BRAZIL_BBOX
from pipeline.backfill import _window_iter


def test_inclusive_final_backfill_window():
    windows = list(_window_iter(date(2020, 1, 1), date(2020, 1, 11)))
    assert [(a.day, b.day) for a, b in windows] == [(1, 5), (6, 10), (11, 11)]


def test_empty_valid_acquisition_preserves_coverage_sidecar(tmp_path):
    settings = SimpleNamespace(data_dir=str(tmp_path), map_key="secret")
    response = SimpleNamespace(ok=True, text="", status_code=200)
    with patch("pipeline.firms.get_settings", return_value=settings), patch(
        "pipeline.firms.data_availability",
        return_value="data_id,min_date,max_date\nX,2020-01-01,2020-12-31",
    ), patch("pipeline.firms.requests.get", return_value=response):
        assert fetch_area("MODIS_SP", BRAZIL_BBOX, 5, "2020-01-01") == ""
        path = _cache_path("MODIS_SP", BRAZIL_BBOX, 5, "2020-01-01")
    meta = json.loads(path.with_suffix(".json").read_text())
    assert path.exists()
    assert meta["start"] == "2020-01-01" and meta["end"] == "2020-01-05"
    assert meta["bbox"] == list(BRAZIL_BBOX)
    assert "secret" not in json.dumps(meta)


def test_non_csv_success_response_is_not_coverage(tmp_path):
    import pytest

    with patch(
        "pipeline.firms.get_settings",
        return_value=SimpleNamespace(data_dir=str(tmp_path), map_key="secret"),
    ), patch(
        "pipeline.firms.data_availability",
        return_value="data_id,min_date,max_date\nX,2020-01-01,2020-12-31",
    ), patch(
        "pipeline.firms.requests.get",
        return_value=SimpleNamespace(ok=True, text="Invalid request", status_code=200),
    ):
        with pytest.raises(ValueError, match="inválida"):
            fetch_area("MODIS_SP", BRAZIL_BBOX, 5, "2020-01-01")
    assert not list(tmp_path.rglob("*.json"))


def test_unavailable_window_does_not_download_or_mark_coverage(tmp_path):
    import pytest

    with patch(
        "pipeline.firms.get_settings",
        return_value=SimpleNamespace(data_dir=str(tmp_path), map_key="secret"),
    ), patch(
        "pipeline.firms.data_availability",
        return_value="data_id,min_date,max_date\nX,2020-01-01,2020-12-31",
    ), patch(
        "pipeline.firms.requests.get"
    ) as download:
        with pytest.raises(ValueError, match="disponibilidade"):
            fetch_area("MODIS_SP", BRAZIL_BBOX, 5, "2022-01-01")
    download.assert_not_called()


def test_reference_choice_never_sums_satellites():
    from pipeline.analytics import _coverage

    class Connection:
        def execute(self, *args):
            return [
                SimpleNamespace(day=date(2020, 1, 1), source_code=source)
                for source in [
                    "VIIRS_NOAA20_NRT",
                    "VIIRS_SNPP_SP",
                    "MODIS_NRT",
                    "MODIS_SP",
                ]
            ]

    viirs, modis = _coverage(Connection())
    assert viirs[date(2020, 1, 1)] == "VIIRS_SNPP_SP"
    assert modis[date(2020, 1, 1)] == "MODIS_SP"
