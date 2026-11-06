"""Endpoints de regiões (estado/município/custom) com agregados pré-calculados OU
consultas leves direto nas detecções (tabela pequena na região-alvo).

Modelagem honesta: sem malha IBGE vínculada ainda, o "Ceará" usa bbox do estado
(documentado); municípios chegam na fase de malHAS IBGE (fase de regiões)."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.core import db
from backend.app.core.config import get_settings

router = APIRouter(tags=["regions"])


@router.get("/regions")
def list_regions(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    settings = get_settings()
    if not settings.api_database_url:
        raise HTTPException(status_code=503, detail="Banco não conectado; ver docs/SETUP.md.")
    sql = """
        SELECT r.id, r.level, r.name, r.geocode, r.is_demo,
               (r.bbox_w IS NOT NULL) AS has_bbox,
               COALESCE(s.total, 0)::int AS total,
               COALESCE(s.last_30d, 0)::int AS last_30d,
               COALESCE(s.instruments, ARRAY[]::text[]) AS instruments
        FROM regions r
        LEFT JOIN LATERAL (
            SELECT COUNT(*)::int AS total,
                   COUNT(*) FILTER (
                     WHERE acquired_at >= now() - interval '30 days')::int AS last_30d,
                   ARRAY_AGG(DISTINCT instrument::text) AS instruments
            FROM fire_detections d
            WHERE r.bbox_w IS NULL OR (
                d.lon >= r.bbox_w AND d.lon <= r.bbox_e
                AND d.lat >= r.bbox_s AND d.lat <= r.bbox_n)
        ) s ON TRUE
        ORDER BY COALESCE(s.total, 0) DESC
        LIMIT :limit
    """
    try:
        rows = db.fetch_all(sql, {"limit": min(limit, settings.max_limit)})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Consulta indisponível: {exc}") from exc
    return [
        {
            "id": r["id"],
            "level": r["level"],
            "name": r["name"],
            "geocode": r["geocode"],
            "is_demo": r["is_demo"],
            "total": r["total"],
            "last_30d": r["last_30d"],
            "instruments": r["instruments"],
        }
        for r in rows
    ]


@router.get("/regions/{region_id}/summary")
def region_summary(region_id: int) -> dict:
    settings = get_settings()
    if not settings.api_database_url:
        raise HTTPException(status_code=503, detail="Banco não conectado; ver docs/SETUP.md.")
    region = db.fetch_one(
        "SELECT id, level, name, geocode, is_demo, bbox_w, bbox_e, bbox_s, bbox_n "
        "FROM regions WHERE id = :id",
        {"id": region_id},
    )
    if region is None:
        raise HTTPException(status_code=404, detail="Região não encontrada.")

    has_bbox = region["bbox_w"] is not None
    where_bbox = "(:has_bbox = FALSE OR (d.lon >= :w AND d.lon <= :e AND d.lat >= :s AND d.lat <= :n))"

    base_sql = f"""
        SELECT COUNT(*)::int AS total,
               COALESCE(SUM((d.instrument = 'MODIS')::int), 0)::int AS modis_count,
               COALESCE(SUM((d.instrument = 'VIIRS')::int), 0)::int AS viirs_count,
               COUNT(*) FILTER (WHERE acquired_at >= now() - interval '30 days')::int AS last_30d,
               COUNT(*) FILTER (WHERE daynight = 'N')::int AS night_count,
               COUNT(DISTINCT DATE(acquired_at))::int AS active_days,
               MIN(acquired_at)::date AS period_start,
               MAX(acquired_at)::date AS period_end
        FROM fire_detections d
        WHERE d.is_demo = FALSE
          AND ({where_bbox})
        """
    params = {"has_bbox": has_bbox, "w": region["bbox_w"], "e": region["bbox_e"],
              "s": region["bbox_s"], "n": region["bbox_n"]}
    try:
        totals = db.fetch_one(base_sql, params)

        monthly = db.fetch_all(
            f"""
            SELECT DATE_TRUNC('month', acquired_at)::date AS month,
                   COUNT(*)::int AS total,
                   COALESCE(SUM((d.instrument='MODIS')::int),0)::int AS modis_count
            FROM fire_detections d
            WHERE d.is_demo = FALSE AND ({where_bbox})
              AND acquired_at >= now() - interval '36 months'
            GROUP BY 1 ORDER BY 1
            """,
            params,
        )
        # Top células de grade (0.25°) — proxies espaciais honestos até a malha IBGE.
        top_cells = db.fetch_all(
            f"""
            SELECT ROUND(d.lat::numeric / 0.25, 2)::float AS lat_center,
                   ROUND(d.lon::numeric / 0.25, 2)::float AS lon_center,
                   COUNT(*)::int AS total,
                   COUNT(*) FILTER (WHERE d.daynight='N')::int AS night_count
            FROM fire_detections d
            WHERE d.is_demo = FALSE AND ({where_bbox})
            GROUP BY 1, 2
            ORDER BY total DESC
            LIMIT 12
            """,
            params,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Consulta indisponível: {exc}") from exc

    return {
        "region": {k: region[k] for k in ("id", "level", "name", "geocode", "is_demo")},
        "totals": totals,
        "monthly_recent": monthly,
        "top_grid_cells": top_cells,
        "note": "Total/células excluem dados DEMO. Células = grade 0.25° (proxy até malha IBGE).",
    }
