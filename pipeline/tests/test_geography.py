import copy
from contextlib import nullcontext
import json
from unittest.mock import patch

import pytest
from pipeline.geography import load_snapshot, validate_snapshot, boundaries


def test_bundled_official_snapshot_is_complete_and_valid():
    features, metadata = load_snapshot()
    assert len(features) == 27
    assert metadata["source_url"].startswith("https://servicodados.ibge.gov.br/")
    assert metadata["quality"] == "minima"


def test_missing_state_is_rejected():
    features, _ = load_snapshot()
    with pytest.raises(ValueError, match="27 UFs"):
        validate_snapshot({"type": "FeatureCollection", "features": features[:-1]})


def test_duplicate_state_is_rejected():
    features, _ = load_snapshot()
    with pytest.raises(ValueError, match="27 UFs"):
        validate_snapshot(
            {"type": "FeatureCollection", "features": features[:-1] + [features[0]]}
        )


def test_unclosed_polygon_is_rejected():
    features, _ = load_snapshot()
    payload = copy.deepcopy({"type": "FeatureCollection", "features": features})
    payload["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]],
    }
    with pytest.raises(ValueError, match="Anel"):
        validate_snapshot(payload)


def test_changed_asset_checksum_is_rejected(tmp_path):
    features, metadata = load_snapshot()
    (tmp_path / "br_ufs.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features})
    )
    (tmp_path / "br_ufs.provenance.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="Checksum"):
        load_snapshot(tmp_path)


def test_offline_import_uses_complete_snapshot_without_network():
    class Connection:
        def __init__(self):
            self.places = []

        def execute(self, statement, params=None):
            if params and "code" in params:
                self.places.append(params["code"])
            return self

        def scalar_one(self):
            return 28

    conn = Connection()
    with patch("requests.get", side_effect=AssertionError("network forbidden")), patch(
        "pipeline.geography.get_engine"
    ) as engine:
        engine.return_value.begin.return_value = nullcontext(conn)
        result = boundaries()
    assert result["regions"] == 28 and result["network_required"] is False
    assert len(set(conn.places)) == 28 and "BR" in conn.places


def test_invalid_postgis_result_aborts_transaction():
    class Connection:
        def execute(self, *args, **kwargs):
            return self

        def scalar_one(self):
            return 27

    with patch("pipeline.geography.get_engine") as engine:
        engine.return_value.begin.return_value = nullcontext(Connection())
        with pytest.raises(ValueError, match="transação cancelada"):
            boundaries()
