"""Shared read-only access to the unified national grid."""

import logging
from fastapi import HTTPException
from backend.app.core import db

logger = logging.getLogger(__name__)
UNIT = "subcélulas ocupadas de 0,01° × dia × passagem diurna/noturna, na escala VIIRS"


def query(sql, params=None):
    try:
        return db.fetch_all(sql, params)
    except Exception as exc:
        logger.warning("Consulta nacional indisponível: %s", type(exc).__name__)
        raise HTTPException(
            503,
            "Dados indisponíveis. Verifique DATABASE_URL, as migrações e o processamento nacional.",
        ) from exc


def region(region_id=None):
    rows = query(
        """
        SELECT id,name,level,bbox_w,bbox_s,bbox_e,bbox_n
        FROM regions WHERE is_demo=false AND geom IS NOT NULL AND
          ((CAST(:id AS int) IS NULL AND level='country' AND geocode='BR') OR id=:id)
        LIMIT 1
    """,
        {"id": region_id},
    )
    if not rows:
        raise HTTPException(
            503 if region_id is None else 404,
            "Limites geográficos indisponíveis. Importe as malhas do IBGE.",
        )
    return rows[0]


# All public products use only the rebuilt national grid, excluding legacy/Demo rows.
GRID_FROM = """
    FROM harmonized_series h JOIN spatial_cells c ON c.id=h.cell_id
    JOIN regions country ON country.id=h.region_id AND country.level='country' AND country.geocode='BR'
    JOIN regions r ON r.id=:region AND r.is_demo=false AND r.geom IS NOT NULL
    WHERE h.is_demo=false AND c.resolution='br_05deg'
      AND ST_Covers(r.geom,ST_SetSRID(ST_MakePoint(c.center_lon,c.center_lat),4326))
"""


def feature_collection(rows):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                "properties": {k: v for k, v in r.items() if k not in ("lon", "lat")},
            }
            for r in rows
        ],
    }
