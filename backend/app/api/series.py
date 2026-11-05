"""Endpoints da série unificada (escala VIIRS) com incerteza e proveniência."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.core import db
from backend.app.core.config import get_settings
from backend.app.schemas import ApiError

router = APIRouter(tags=["series"])


@router.get("/series/unified")
def unified_series(
    region_id: int | None = Query(None),
    period_type: str = Query("month", pattern="^(day|week|month)$"),
    limit: int = Query(default=240, ge=1),
) -> dict:
    """Série unificada: cada ponto marca MODIS harmonizado x VIIRS direto + intervalo."""
    settings = get_settings()
    if not settings.api_database_url:
        raise HTTPException(
            status_code=503,
            detail="Banco não conectado: crie o banco pela integração da Vercel ou defina DATABASE_URL. Ver docs/SETUP.md.",
        )
    limit = min(limit, settings.max_limit)
    sql = """
        SELECT h.period_start, h.value_raw, h.value_viirs, h.ci_low, h.ci_high, h.value_source,
               h.quality_flag, h.method
        FROM harmonized_series h
        WHERE h.period_type = :period_type
          AND (:region_id IS NULL OR h.region_id = :region_id)
          AND h.is_demo = FALSE
        ORDER BY h.period_start
        LIMIT :limit
    """
    try:
        rows = db.fetch_all(sql, {"period_type": period_type, "region_id": region_id, "limit": limit})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Consulta indisponível: {exc}") from exc
    return {
        "unit": "contagens de focos (escala VIIRS)",
        "provenance": "MODIS harmonizado p/ escala VIIRS (2012↓) + VIIRS direto (2012→)",
        "points": [
            {
                "period_start": r["period_start"].isoformat(),
                "value_raw": r["value_raw"],
                "value_viirs": r["value_viirs"],
                "ci_low": r["ci_low"],
                "ci_high": r["ci_high"],
                "source": r["value_source"],
                "quality": r["quality_flag"],
                "method": r["method"],
            }
            for r in rows
        ],
    }


@router.get("/series/seasonality")
def seasonality(region_id: int | None = Query(None)) -> dict:
    """Sazonalidade média por semana do ano (climatologia interna p/ comparação)."""
    settings = get_settings()
    if not settings.api_database_url:
        raise HTTPException(status_code=503, detail="Banco não conectado; ver docs/SETUP.md.")
    sql = """
        SELECT EXTRACT(WEEK FROM period_start)::int AS week,
               AVG(value_viirs)::float AS mean, STDDEV(value_viirs)::float AS sd
        FROM harmonized_series
        WHERE is_demo = FALSE AND period_type = 'week'
          AND (:region_id IS NULL OR region_id = :region_id)
        GROUP BY 1 ORDER BY 1
    """
    try:
        rows = db.fetch_all(sql, {"region_id": region_id})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Consulta indisponível: {exc}") from exc
    return {"weeks": rows}
