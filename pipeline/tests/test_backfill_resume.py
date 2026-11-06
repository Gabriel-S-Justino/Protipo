from datetime import date, timedelta
from unittest.mock import patch
from pipeline.backfill import run_backfill


def test_resume_skips_verified_windows_before_applying_limit():
    covered = {date(2023, 1, 1) + timedelta(days=n) for n in range(5)}
    with patch("pipeline.backfill._covered_days", return_value=covered), patch(
        "pipeline.backfill.fetch_area"
    ) as fetch, patch(
        "pipeline.backfill.ingest",
        return_value={"files": [{"accepted": 3, "coverage_days": 5}]},
    ), patch(
        "pipeline.backfill.time.sleep"
    ):
        report = run_backfill("VIIRS_NOAA20_SP", "2023-01-01", "2023-01-15", limit=1)
    assert fetch.call_args.args[3] == "2023-01-06"
    assert report["windows_already_covered"] == 1
    assert report["windows_remaining"] == 1
    assert report["status"] == "in_progress"


def test_complete_history_does_not_call_nasa_or_ingest():
    covered = {date(2023, 1, 1) + timedelta(days=n) for n in range(10)}
    with patch("pipeline.backfill._covered_days", return_value=covered), patch(
        "pipeline.backfill.fetch_area"
    ) as fetch, patch("pipeline.backfill.ingest") as ingest:
        report = run_backfill("VIIRS_NOAA20_SP", "2023-01-01", "2023-01-10", limit=1)
    fetch.assert_not_called()
    ingest.assert_not_called()
    assert report["status"] == "ok" and report["windows_attempted"] == 0


def test_failed_window_remains_pending():
    with patch("pipeline.backfill._covered_days", return_value=set()), patch(
        "pipeline.backfill.fetch_area", side_effect=RuntimeError("source unavailable")
    ), patch("pipeline.backfill.time.sleep"):
        report = run_backfill("VIIRS_NOAA20_SP", "2023-01-01", "2023-01-05")
    assert report["status"] == "partial"
    assert report["windows_remaining"] == 1


def test_empty_valid_window_counts_as_completed_coverage():
    with patch("pipeline.backfill._covered_days", return_value=set()), patch(
        "pipeline.backfill.fetch_area", return_value=""
    ), patch(
        "pipeline.backfill.ingest",
        return_value={"files": [{"accepted": 0, "coverage_days": 1}]},
    ), patch(
        "pipeline.backfill.time.sleep"
    ):
        report = run_backfill("VIIRS_NOAA20_SP", "2023-01-01", "2023-01-01")
    assert report["status"] == "ok" and report["accepted"] == 0


def test_rejected_records_do_not_complete_window():
    with patch("pipeline.backfill._covered_days", return_value=set()), patch(
        "pipeline.backfill.fetch_area"
    ), patch(
        "pipeline.backfill.ingest",
        return_value={"files": [{"rejected": 1, "coverage_days": 0}]},
    ), patch(
        "pipeline.backfill.time.sleep"
    ):
        report = run_backfill("VIIRS_NOAA20_SP", "2023-01-01", "2023-01-05")
    assert report["status"] == "partial" and report["windows_completed"] == 0
