"""Tiles vetoriais MVT gerados pelo PostGIS (ST_AsMVT) — NENHUM processamento
científico em requisição; apenas agregações espaciais leves + parâmetros limitados.

Camada: `grid_points` — pontos-cell de grade dinâmica (8×8 por tile) com contagens
por instrumento, respeitando o filtro temporal. Cache HTTP via vercel.json headers.
"""

import datetime as dt
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Path as FPath, Query, Response

from backend.app.core import db
from backend.app.core.config import get_settings

router = APIRouter(tags=["tiles"])


def _parse_date(value: str | None) -> dt.date | None:
    if value is None:
        return None
    return dt.date.fromisoformat(unquote(value))


@router.get("/tiles/{layer}/{z}/{x}/{y}.mvt")
def tile(
    layer: str = FPath(pattern="^grid_points$"),
    z: int = FPath(ge=0, le=14),
    x: int = FPath(ge=0),
    y: int = FPath(ge=0),
    include_demo: bool = Query(False),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
) -> Response:
    settings = get_settings()
    if not settings.api_database_url:
        raise HTTPException(status_code=503, detail="Banco não conectado; ver docs/SETUP.md.")

    if layer != "grid_points":
        raise HTTPException(status_code=404, detail="Camada inexistente.")

    # Verificação barata por divisão: 2^z grid/ESPG3857
    if z >= 0 and (x >= 2**z or y >= 2**z):
        raise HTTPException(status_code=400, detail="Coordenada de tile fora do intervalo.")

    size = 360.0 / (2**z * 8.0)  # graus; célula de grade = tile/8
    date_from = _parse_date(from_date)
    date_to = _parse_date(to_date)
    if date_from and date_to and date_from >= date_to:
        raise HTTPException(status_code=400, detail="janela 'from' deve preceder 'to'.")

    # filtro temporal com PARÂMETROS (anti-SQL injection): datas devem vir válido ISO.
    clauses = []
    if date_from:
        clauses.append("d.acquired_at >= CAST(:from_date AS timestamptz)")
    if date_to:
        clauses.append("d.acquired_at < CAST(:to_date AS timestamptz)")
    if not include_demo:
        clauses.append("d.is_demo = FALSE")
    time_where = (" AND " + " AND ".join(clauses)) if clauses else ""

    params: dict[str, object] = {"z": z, "x": x, "y": y, "size": size}
    if date_from:
        params["from_date"] = date_from.isoformat()
    if date_to:
        params["to_date"] = date_to.isoformat()

    sql = f"""
        WITH env AS (
            SELECT ST_TileEnvelope(CAST(:z AS int), CAST(:x AS int), CAST(:y AS int)) AS b3857
        ),
        env4326 AS (SELECT ST_Transform(e.b3857, 4326) AS b4326, e.b3857 FROM env e),
        bounds AS (
            SELECT b3857,
                   ST_XMin(b4326) AS xmin, ST_YMin(b4326) AS ymin,
                   ST_XMax(b4326) AS xmax, ST_YMax(b4326) AS ymax,
                   CAST((:size * 1.0) AS float) AS size
            FROM env4326
        ),
        pts AS (
            SELECT
                FLOOR((d.lon - b.xmin) / b.size)::int AS ix,
                FLOOR((d.lat - b.ymin) / b.size)::int AS iy,
                COUNT(*)::int AS n,
                COALESCE(SUM((d.instrument = 'MODIS')::int), 0)::int AS m,
                COALESCE(SUM((d.instrument = 'VIIRS')::int), 0)::int AS v
            FROM fire_detections d, bounds b
            WHERE d.lon >= b.xmin AND d.lon < b.xmax
              AND d.lat >= b.ymin AND d.lat < b.ymax{time_where}
            GROUP BY 1, 2
        ),
        ctr AS (
            SELECT p.ix, p.iy, p.n, p.m, p.v,
                   ST_Transform(
                     ST_SetSRID(ST_MakePoint(b.xmin + (p.ix + 0.5) * b.size,
                                             b.ymin + (p.iy + 0.5) * b.size), 4326), 3857
                   ) AS geom3857,
                   b.b3857
            FROM pts p, bounds b
        ),
        mvtgeom AS (
            SELECT c.ix, c.iy, c.n, c.m, c.v,
                   ST_AsMVTGeom(c.geom3857, c.b3857, 4096, 64, true) AS geom
            FROM ctr c
        )
        SELECT ST_AsMVT(mvtgeom.*, 'grid_points', 4096, 'geom') AS mvt
        FROM mvtgeom
    """
    try:
        row = db.fetch_one(sql, params)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Tile indisponível: {exc}") from exc

    mvt = row["mvt"] if row else None
    if not mvt or len(mvt) < 64:  # MVT mínimo significativo
        raise HTTPException(status_code=204, detail="")
    return Response(content=mvt, media_type="application/vnd.mapbox-vector-tile")
