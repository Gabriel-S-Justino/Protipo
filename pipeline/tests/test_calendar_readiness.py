from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch
from pipeline.analytics import calendar
from pipeline.commands import run


class Rows(list):
    def close(self):
        pass


class Connection:
    def execute(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter([])

    def mappings(self):
        return Rows([])


def test_empty_calendar_is_an_explicit_data_state_not_runtime_failure():
    with patch("pipeline.analytics.get_engine") as engine, patch(
        "pipeline.analytics._country", return_value=76
    ), patch("pipeline.analytics._coverage", return_value=({}, {})):
        engine.return_value.begin.return_value = nullcontext(Connection())
        result = calendar()
    assert result["status"] == "insufficient_data" and result["rows"] == 0
    assert result["minimum_years"] == 3


def test_calendar_cli_returns_success_for_insufficient_history():
    with patch(
        "pipeline.analytics.calendar",
        return_value={"status": "insufficient_data", "rows": 0},
    ):
        assert run(SimpleNamespace(command="calendar")) == 0


def test_backfill_cli_returns_success_for_bounded_progress():
    args = SimpleNamespace(
        command="backfill",
        source="VIIRS_NOAA20_SP",
        start="2023-01-01",
        end="2025-12-31",
        sleep=1,
        limit=30,
    )
    with patch(
        "pipeline.backfill.run_backfill",
        return_value={"status": "in_progress", "windows_remaining": 20},
    ):
        assert run(args) == 0


def test_real_download_failure_still_fails_cli():
    args = SimpleNamespace(
        command="backfill",
        source="VIIRS_NOAA20_SP",
        start="2023-01-01",
        end="2025-12-31",
        sleep=1,
        limit=30,
    )
    with patch(
        "pipeline.backfill.run_backfill",
        return_value={"status": "partial", "errors": [{"error": "network failure"}]},
    ):
        assert run(args) == 1


def test_update_succeeds_while_calendar_is_waiting_for_history(capsys):
    import json

    with patch("pipeline.firms.fetch_area"), patch("pipeline.ingest.ingest"), patch(
        "pipeline.analytics.harmonize", return_value={"status": "ok", "rows": 2}
    ), patch(
        "pipeline.analytics.calendar",
        return_value={"status": "insufficient_data", "rows": 0},
    ), patch(
        "pipeline.analytics.anomalies", return_value={"status": "ok", "rows": 0}
    ):
        assert run(SimpleNamespace(command="update")) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ok"
    assert result["calendar"]["status"] == "insufficient_data"
    assert result["calendar"]["rows"] == 0
