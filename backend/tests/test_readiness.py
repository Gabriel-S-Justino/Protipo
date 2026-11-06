from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.health import health_snapshot
from backend.app.api.national import query
import pytest
from fastapi import HTTPException

client = TestClient(app)
SETTINGS = SimpleNamespace(
    app_name="Fire Intelligence Platform",
    app_env="production",
    api_database_url="configured",
)


def test_connected_database_is_not_reported_ready_before_migration():
    with patch("backend.app.api.health.get_settings", return_value=SETTINGS), patch(
        "backend.app.api.health.db.fetch_one",
        side_effect=[
            {"ok": 1},
            {
                "coverage_table": False,
                "region_geometry": False,
                "migrations_table": True,
            },
            {"version_num": "0003_hseries_widen"},
        ],
    ):
        body = client.get("/api/health").json()
    assert body["database"] == "up"
    assert body["status"] == "degraded"
    assert body["readiness"] == "migration_pending"
    assert body["schema_revision"] == "0003_hseries_widen"
    assert "0004_brazil_science" in body["next_action"]


def test_healthy_schema_with_no_boundaries_has_specific_action():
    with patch("backend.app.api.health.get_settings", return_value=SETTINGS), patch(
        "backend.app.api.health.db.fetch_one",
        side_effect=[
            {"ok": 1},
            {"coverage_table": True, "region_geometry": True, "migrations_table": True},
            {"version_num": "0004_brazil_science"},
            {
                "boundaries": False,
                "coverage": False,
                "unified": False,
                "calendar": False,
            },
        ],
    ):
        result = health_snapshot()
    assert result["readiness"] == "boundaries_missing"
    assert result["checks"]["database"] is True


def test_postgres_missing_column_reports_migration_not_missing_database():
    class MissingColumn(Exception):
        sqlstate = "42703"

    with patch(
        "backend.app.api.national.db.fetch_all",
        side_effect=MissingColumn("private internal details"),
    ):
        with pytest.raises(HTTPException) as raised:
            query("SELECT something")
    assert "0004_brazil_science" in raised.value.detail
    assert "private" not in raised.value.detail


def test_query_timeout_is_not_misreported_as_missing_database():
    class Timeout(Exception):
        sqlstate = "57014"

    with patch("backend.app.api.national.db.fetch_all", side_effect=Timeout()):
        with pytest.raises(HTTPException) as raised:
            query("SELECT something")
    assert "tempo" in raised.value.detail
