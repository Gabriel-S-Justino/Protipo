"""Endpoints de anomalias (leitura de anomaly_results — pré-calculadas pelo pipeline)
e de lotes de ingestão (dados e qualidade)."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.core import db
from backend.app.core.config import get_settings

router = APIRouter(tags=["analytics"])


@router.get("/analytics/anomalies")
def list_anomalies(
    region_id: int | None = Query(None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    from backend.app.api.national import query, region

    selected = region(region_id)
    rows = query(
        """
        SELECT a.id,a.cell_id,c.center_lat AS lat,c.center_lon AS lon,
          a.period_start,a.period_end,a.observed,a.expected,a.score,a.level,a.method,a.notes,
          (SELECT name FROM regions state WHERE state.level='state' AND state.is_demo=false
              AND ST_Covers(state.geom,ST_SetSRID(ST_MakePoint(c.center_lon,c.center_lat),4326))
              LIMIT 1) AS state
        FROM anomaly_results a JOIN spatial_cells c ON c.id=a.cell_id
        JOIN regions country ON country.id=a.region_id AND country.geocode='BR' AND country.level='country'
        JOIN regions r ON r.id=:region AND r.geom IS NOT NULL AND r.is_demo=false
        WHERE a.is_demo=false AND c.resolution='br_05deg'
          AND ST_Covers(r.geom,ST_SetSRID(ST_MakePoint(c.center_lon,c.center_lat),4326))
        ORDER BY a.period_start DESC,a.score DESC NULLS LAST LIMIT :limit
    """,
        {"region": selected["id"], "limit": limit},
    )
    return [
        {
            **row,
            "region": row["state"] or selected["name"],
            "period": [row["period_start"], row["period_end"]],
        }
        for row in rows
    ]


@router.get("/ingestion/batches")
def ingestion_batches(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    settings = get_settings()
    if not settings.api_database_url:
        raise HTTPException(
            status_code=503, detail="Banco não conectado; ver docs/SETUP.md."
        )
    sql = """
        SELECT b.id, b.source_code, b.source_url, b.period_start, b.period_end,
               b.records_total, b.records_accepted, b.records_rejected,
               b.records_duplicated, b.status, b.pipeline_version, b.created_at
        FROM ingestion_batches b
        ORDER BY b.id DESC
        LIMIT :limit
    """
    try:
        rows = db.fetch_all(sql, {"limit": min(limit, settings.max_limit)})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503, detail=f"Consulta indisponível: {exc}"
        ) from exc
    return [dict(r) for r in rows]


@router.get("/metadata/sources")
def metadata_sources() -> list[dict]:
    settings = get_settings()
    if not settings.api_database_url:
        raise HTTPException(
            status_code=503, detail="Banco não conectado; ver docs/SETUP.md."
        )
    sql = """
        SELECT s.code, s.sensor, s.satellite, s.product, s.mode, s.active,
               COALESCE(c.total, 0)::int AS detections,
               c.first_seen, c.last_seen
        FROM data_sources s
        LEFT JOIN LATERAL (
            SELECT COUNT(*)::int AS total,
                   MIN(acquired_at)::date AS first_seen,
                   MAX(acquired_at)::date AS last_seen
            FROM fire_detections d WHERE d.source_id = s.id
        ) c ON TRUE
        ORDER BY s.code
    """
    try:
        rows = db.fetch_all(sql)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503, detail=f"Consulta indisponível: {exc}"
        ) from exc
    return [dict(r) for r in rows]
