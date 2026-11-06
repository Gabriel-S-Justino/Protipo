"""Official country/states and spatial summaries from the unified grid."""

from fastapi import APIRouter, Query
from backend.app.api.national import query, region, GRID_FROM, UNIT

router = APIRouter(tags=["regions"])


@router.get("/regions")
def list_regions(limit: int = Query(100, ge=1, le=200)):
    return query(
        """
        SELECT id,level,name,geocode,false AS is_demo,bbox_w,bbox_s,bbox_e,bbox_n
        FROM regions WHERE is_demo=false AND geom IS NOT NULL AND level IN('country','state')
        ORDER BY CASE WHEN level='country' THEN 0 ELSE 1 END,name LIMIT :limit
    """,
        {"limit": limit},
    )


@router.get("/regions/{region_id}/summary")
def region_summary(region_id: int):
    selected = region(region_id)
    values = query(
        "SELECT COALESCE(SUM(value_viirs),0) AS total,"
        + "COALESCE(SUM(value_viirs) FILTER(WHERE period_start>=CURRENT_DATE-30),0) AS last_30d,"
        + "COUNT(DISTINCT period_start) AS active_days,MIN(period_start) AS period_start,MAX(period_start) AS period_end"
        + GRID_FROM
        + " AND h.period_type='day'",
        {"region": region_id},
    )[0]
    monthly = query(
        "SELECT h.period_start AS month,SUM(h.value_viirs) AS total"
        + GRID_FROM
        + " AND h.period_type='month' GROUP BY 1 ORDER BY 1 DESC LIMIT 36",
        {"region": region_id},
    )
    return {
        "region": selected,
        "totals": values,
        "monthly_recent": list(reversed(monthly)),
        "note": "Grade nacional de 0,5°; seleção estadual pelo ponto representativo de cada célula.",
        "unit": UNIT,
    }
