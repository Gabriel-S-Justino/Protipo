"""Unified grid MVT for external consumers; properties carry a single VIIRS-equivalent weight."""

from datetime import date
from fastapi import APIRouter, Query, Path, HTTPException, Response
from backend.app.api.national import region, query

router = APIRouter(tags=["tiles"])


@router.get("/tiles/{layer}/{z}/{x}/{y}.mvt")
def tile(
    layer: str = Path(pattern="^grid_points$"),
    z: int = Path(ge=0, le=14),
    x: int = Path(ge=0),
    y: int = Path(ge=0),
    region_id: int | None = None,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    if x >= 2**z or y >= 2**z:
        raise HTTPException(400, "Tile fora do intervalo.")
    if from_date and to_date and from_date >= to_date:
        raise HTTPException(422, "Intervalo de datas inválido.")
    selected = region(region_id)
    rows = query(
        """
        WITH bounds AS(SELECT ST_TileEnvelope(:z,:x,:y) AS geom),
        points AS(
          SELECT c.id,SUM(h.value_viirs) AS weight,
            ST_Transform(ST_SetSRID(ST_MakePoint(c.center_lon,c.center_lat),4326),3857) AS geom
          FROM harmonized_series h JOIN spatial_cells c ON c.id=h.cell_id
          JOIN regions country ON country.id=h.region_id AND country.geocode='BR' AND country.level='country'
          JOIN regions r ON r.id=:r AND r.geom IS NOT NULL AND r.is_demo=false
          WHERE h.period_type='day' AND h.is_demo=false AND c.resolution='br_05deg'
            AND ST_Covers(r.geom,ST_SetSRID(ST_MakePoint(c.center_lon,c.center_lat),4326))
            AND (CAST(:start AS date) IS NULL OR h.period_start>=:start)
            AND (CAST(:end AS date) IS NULL OR h.period_start<:end)
            AND ST_Intersects(ST_Transform((SELECT geom FROM bounds),4326),
                    ST_SetSRID(ST_MakePoint(c.center_lon,c.center_lat),4326))
          GROUP BY c.id
        ), geometries AS(
          SELECT id,weight,ST_AsMVTGeom(p.geom,b.geom,4096,64,true) AS geom FROM points p,bounds b
        ) SELECT ST_AsMVT(g.*,'grid_points',4096,'geom') AS mvt FROM geometries g
    """,
        {
            "z": z,
            "x": x,
            "y": y,
            "r": selected["id"],
            "start": from_date,
            "end": to_date,
        },
    )
    payload = rows[0]["mvt"] if rows else None
    return Response(
        content=bytes(payload) if payload else b"",
        status_code=200 if payload else 204,
        media_type="application/vnd.mapbox-vector-tile",
    )
