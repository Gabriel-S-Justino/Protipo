from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
REGION = {"id": 76, "name": "Brasil", "level": "country"}


def test_calendar_preserves_location_and_uncertainty():
    row = {
        "cell_id": 2,
        "cell_key": "-100:-20",
        "lat": -9.75,
        "lon": -49.75,
        "probability": 0.5,
        "ci_low": 0.2,
        "ci_high": 0.8,
        "years_used": 8,
        "period_of_year": 10,
    }
    with patch("backend.app.api.dashboard.region", return_value=REGION), patch(
        "backend.app.api.dashboard.query", return_value=[row]
    ):
        response = client.get("/api/calendar/locations?period_type=week&period=10")
    assert response.status_code == 200
    feature = response.json()["features"][0]
    assert feature["geometry"]["coordinates"] == [-49.75, -9.75]
    assert feature["properties"]["years_used"] == 8
    assert feature["properties"]["probability"] == 0.5


def test_invalid_month_and_date_range_are_rejected():
    assert (
        client.get("/api/calendar/locations?period_type=month&period=13").status_code
        == 422
    )
    assert client.get("/api/map/heat?from=2026-02-01&to=2026-01-01").status_code == 422
    assert client.get("/api/map/heat?from=nonsense").status_code == 422


def test_historical_heat_uses_only_unified_grid():
    with patch("backend.app.api.dashboard.region", return_value=REGION), patch(
        "backend.app.api.dashboard.query", return_value=[]
    ) as mock:
        response = client.get("/api/map/heat")
        sql = mock.call_args.args[0]
    assert response.json()["features"] == []
    assert "fire_detections" not in sql
    assert "value_viirs" in sql and "h.is_demo=false" in sql


def test_missing_polygons_gives_actionable_error():
    with patch("backend.app.api.national.query", return_value=[]):
        response = client.get("/api/map/heat")
    assert response.status_code == 503
    assert "IBGE" in response.json()["detail"]
