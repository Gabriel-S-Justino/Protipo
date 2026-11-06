"""Import a verified official IBGE snapshot without a runtime network dependency."""

import hashlib
import json
import math
from pathlib import Path

from sqlalchemy import text
from pipeline.db import get_engine

BRAZIL_BBOX = (-74.0, -34.0, -28.0, 6.0)
IBGE_BASE = "https://servicodados.ibge.gov.br/api/v3/malhas"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
STATE_NAMES = {
    "11": "Rondônia",
    "12": "Acre",
    "13": "Amazonas",
    "14": "Roraima",
    "15": "Pará",
    "16": "Amapá",
    "17": "Tocantins",
    "21": "Maranhão",
    "22": "Piauí",
    "23": "Ceará",
    "24": "Rio Grande do Norte",
    "25": "Paraíba",
    "26": "Pernambuco",
    "27": "Alagoas",
    "28": "Sergipe",
    "29": "Bahia",
    "31": "Minas Gerais",
    "32": "Espírito Santo",
    "33": "Rio de Janeiro",
    "35": "São Paulo",
    "41": "Paraná",
    "42": "Santa Catarina",
    "43": "Rio Grande do Sul",
    "50": "Mato Grosso do Sul",
    "51": "Mato Grosso",
    "52": "Goiás",
    "53": "Distrito Federal",
}


def validate_snapshot(payload):
    """Reject partial, duplicate, malformed or out-of-country data before any DB write."""
    if payload.get("type") != "FeatureCollection":
        raise ValueError("A malha IBGE precisa ser uma FeatureCollection.")
    features = payload.get("features", [])
    codes = [str(f.get("properties", {}).get("codarea", "")) for f in features]
    if len(codes) != 27 or set(codes) != set(STATE_NAMES):
        raise ValueError(
            "A malha IBGE precisa conter exatamente as 27 UFs, sem duplicação."
        )
    for feature in features:
        geometry = feature.get("geometry") or {}
        kind = geometry.get("type")
        if kind not in ("Polygon", "MultiPolygon"):
            raise ValueError("Geometria IBGE inválida: esperado Polygon/MultiPolygon.")
        coordinates = geometry.get("coordinates", [])
        polygons = [coordinates] if kind == "Polygon" else coordinates
        if not polygons:
            raise ValueError("Geometria IBGE vazia.")
        for polygon in polygons:
            if not polygon:
                raise ValueError("Polígono IBGE vazio.")
            for ring in polygon:
                if len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError("Anel IBGE aberto ou incompleto.")
                for point in ring:
                    if len(point) < 2:
                        raise ValueError("Coordenada IBGE incompleta.")
                    lon, lat = point[:2]
                    if (
                        not isinstance(lon, (int, float))
                        or not isinstance(lat, (int, float))
                        or not math.isfinite(lon)
                        or not math.isfinite(lat)
                        or not (-74 <= lon <= -28 and -34 <= lat <= 6)
                    ):
                        raise ValueError("Coordenadas IBGE incompatíveis com o Brasil.")
    return features


def load_snapshot(asset_dir=None):
    directory = Path(asset_dir) if asset_dir is not None else ASSET_DIR
    payload = (directory / "br_ufs.geojson").read_bytes()
    metadata = json.loads(
        (directory / "br_ufs.provenance.json").read_text(encoding="utf-8")
    )
    if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
        raise ValueError("Checksum da malha IBGE inválido; nenhum dado foi importado.")
    features = validate_snapshot(json.loads(payload))
    return features, metadata


def boundaries():
    features, metadata = load_snapshot()
    # Country geometry is the union of the same official state polygons.
    places = [("BR", "Brasil", "country", features)] + [
        (
            str(f["properties"]["codarea"]),
            STATE_NAMES[str(f["properties"]["codarea"])],
            "state",
            [f],
        )
        for f in features
    ]
    version = "IBGE v3 " + metadata["retrieved_at"][:10] + " minima"
    with get_engine().begin() as conn:
        for code, name, level, items in places:
            geometries = [json.dumps(f["geometry"]) for f in items]
            conn.execute(
                text("""
                INSERT INTO regions (level,name,geocode,is_demo,boundary_file,boundary_version)
                VALUES (:level,:name,:code,false,:url,:version)
                ON CONFLICT (level,name) DO UPDATE SET geocode=EXCLUDED.geocode,
                    boundary_file=EXCLUDED.boundary_file, boundary_version=EXCLUDED.boundary_version,
                    is_demo=false
            """),
                {
                    "level": level,
                    "name": name,
                    "code": code,
                    "url": metadata["source_url"],
                    "version": version,
                },
            )
            conn.execute(
                text("""
                UPDATE regions SET geom=(
                    SELECT ST_Multi(ST_CollectionExtract(ST_UnaryUnion(ST_Collect(
                        ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(g),4326)))),3))
                    FROM jsonb_array_elements_text(CAST(:shapes AS jsonb)) AS items(g)
                ) WHERE level=:level AND name=:name
            """),
                {"shapes": json.dumps(geometries), "level": level, "name": name},
            )
        conn.execute(text("""
            UPDATE regions SET bbox_w=ST_XMin(geom),bbox_s=ST_YMin(geom),
              bbox_e=ST_XMax(geom),bbox_n=ST_YMax(geom)
            WHERE geom IS NOT NULL AND is_demo=false
        """))
        conn.execute(text("""
            UPDATE regions SET parent_id=(SELECT id FROM regions WHERE level='country' AND geocode='BR')
            WHERE level='state' AND geom IS NOT NULL AND is_demo=false
        """))
        result = conn.execute(text("""
            SELECT COUNT(*) AS total FROM regions WHERE is_demo=false
              AND geom IS NOT NULL AND NOT ST_IsEmpty(geom) AND ST_IsValid(geom)
              AND ((level='country' AND geocode='BR') OR (level='state' AND geocode IN
                  ('11','12','13','14','15','16','17','21','22','23','24','25','26','27',
                   '28','29','31','32','33','35','41','42','43','50','51','52','53')))
        """)).scalar_one()
        if result != 28:
            raise ValueError(
                "A importação não produziu Brasil e 27 UFs válidos; transação cancelada."
            )
    return {
        "status": "ok",
        "regions": 28,
        "source": metadata["source"],
        "snapshot": metadata["retrieved_at"],
        "sha256": metadata["sha256"],
        "network_required": False,
    }
