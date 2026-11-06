"""One unified series; no side-by-side sensor counts."""

from fastapi import APIRouter, Query
from backend.app.api.national import query, region, GRID_FROM, UNIT

router = APIRouter(tags=["series"])


@router.get("/series/unified")
def unified_series(
    region_id: int | None = None,
    period_type: str = Query("month", pattern="^(day|week|month)$"),
    limit: int = Query(360, ge=1, le=1000),
):
    selected = region(region_id)
    points = query(
        """
        SELECT h.period_start,SUM(value_viirs) AS value_viirs,
          MIN(coverage_fraction) AS coverage_fraction,
          CASE WHEN MIN(coverage_fraction)<1 THEN 'insufficient' ELSE 'ok' END AS quality
    """
        + GRID_FROM
        + """ AND h.period_type=:kind GROUP BY h.period_start
        ORDER BY h.period_start DESC LIMIT :limit
    """,
        {"region": selected["id"], "kind": period_type, "limit": limit},
    )
    return {
        "unit": UNIT,
        "region": selected["name"],
        "provenance": "VIIRS de referência; MODIS harmonizado por área com calibração e validação por ano.",
        "points": list(reversed(points)),
    }
