"""Unified summary, coverage and spatial weekly/monthly calendar."""

from datetime import date
from fastapi import APIRouter, Query, HTTPException
from backend.app.api.national import query, region, GRID_FROM, feature_collection, UNIT

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary")
def dashboard_summary(region_id: int | None = None):
    selected = region(region_id)
    rows = query(
        """
        SELECT COALESCE(SUM(value_viirs),0) AS total,
          COALESCE(SUM(value_viirs) FILTER(WHERE period_start>=CURRENT_DATE-30),0) AS last_30d,
          AVG(value_viirs) FILTER(WHERE period_start<CURRENT_DATE-30 AND period_start>=CURRENT_DATE-365) AS last_30d_avg_hist
    """ + GRID_FROM + " AND h.period_type='day'",
        {"region": selected["id"]},
    )
    return {
        **rows[0],
        "unit": UNIT,
        "region": selected["name"],
        "unified_series_note": "Uma única série: VIIRS de referência e MODIS convertido onde a calibração foi validada. Lacunas de cobertura não equivalem a zero.",
    }


@router.get("/metadata/coverage")
def coverage():
    rows = query("""
        SELECT MIN(day) AS period_start,MAX(day) AS period_end,
          COUNT(DISTINCT day) AS covered_days FROM acquisition_coverage WHERE scope='BR'
    """)
    share = query("""
        SELECT AVG(CASE WHEN value_source='modis_harmonized' THEN 1.0 ELSE 0.0 END) AS share
        FROM harmonized_series h JOIN spatial_cells c ON c.id=h.cell_id
        WHERE h.is_demo=false AND h.period_type='day' AND c.resolution='br_05deg'
    """)
    return {
        **rows[0],
        "instruments": ["série VIIRS equivalente"],
        "harmonized_share": share[0]["share"],
    }


CALENDAR_FROM = """
    FROM calendar_probabilities p JOIN spatial_cells c ON c.id=p.cell_id
    JOIN regions country ON country.id=p.region_id AND country.level='country' AND country.geocode='BR'
    JOIN regions r ON r.id=:region AND r.geom IS NOT NULL AND r.is_demo=false
    WHERE p.is_demo=false AND c.resolution='br_05deg' AND p.period_type=:kind
      AND ST_Covers(r.geom,ST_SetSRID(ST_MakePoint(c.center_lon,c.center_lat),4326))
"""
COLUMNS = """p.cell_id,c.cell_key,c.center_lat AS lat,c.center_lon AS lon,p.period_of_year,
    p.probability,p.ci_low,p.ci_high,p.years_used,p.expected_count,p.confidence,
    p.validation,p.calculated_at,
    (SELECT name FROM regions state WHERE state.level='state' AND state.is_demo=false
        AND ST_Covers(state.geom,ST_SetSRID(ST_MakePoint(c.center_lon,c.center_lat),4326)) LIMIT 1) AS state"""


@router.get("/calendar/probability")
def calendar_probability(
    region_id: int | None = None,
    period_type: str = Query("week", pattern="^(week|month)$"),
):
    selected = region(region_id)
    params = {"region": selected["id"], "kind": period_type}
    # Most active 20 cells, all their periods. Stable identity avoids mixing locations.
    return query(
        "WITH eligible AS (SELECT " + COLUMNS + CALENDAR_FROM + """),
        selected_cells AS (SELECT cell_id FROM eligible GROUP BY cell_id
                           ORDER BY AVG(expected_count) DESC,cell_id LIMIT 20)
        SELECT * FROM eligible WHERE cell_id IN(SELECT cell_id FROM selected_cells)
        ORDER BY cell_id,period_of_year
    """,
        params,
    )


@router.get("/calendar/locations")
def calendar_locations(
    region_id: int | None = None,
    period_type: str = Query("week", pattern="^(week|month)$"),
    period: int = Query(1, ge=1, le=53),
):
    if period_type == "month" and period > 12:
        raise HTTPException(422, "Mês deve estar entre 1 e 12.")
    selected = region(region_id)
    rows = query(
        "SELECT "
        + COLUMNS
        + CALENDAR_FROM
        + " AND p.period_of_year=:period ORDER BY p.cell_id",
        {"region": selected["id"], "kind": period_type, "period": period},
    )
    result = feature_collection(rows)
    result["metadata"] = {
        "region": selected["name"],
        "period_type": period_type,
        "period": period,
        "meaning": "Probabilidade histórica de pelo menos uma subcélula ativa na área de 0,5°. Não é previsão meteorológica.",
        "resolution_degrees": 0.5,
    }
    return result


@router.get("/map/heat")
def map_heat(
    region_id: int | None = None,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    if from_date and to_date and from_date >= to_date:
        raise HTTPException(
            422, "A data final deve ser posterior à inicial (fim exclusivo)."
        )
    selected = region(region_id)
    rows = query(
        """
        SELECT h.cell_id,c.center_lon AS lon,c.center_lat AS lat,
          SUM(h.value_viirs) AS weight,MIN(h.period_start) AS first_date,MAX(h.period_start) AS last_date
    """
        + GRID_FROM
        + """
        AND h.period_type='day'
        AND (CAST(:start AS date) IS NULL OR h.period_start>=:start)
        AND (CAST(:end AS date) IS NULL OR h.period_start<:end)
        GROUP BY h.cell_id,c.center_lon,c.center_lat ORDER BY h.cell_id
    """,
        {"region": selected["id"], "start": from_date, "end": to_date},
    )
    return {
        **feature_collection(rows),
        "metadata": {
            "unit": UNIT,
            "region": selected["name"],
            "resolution_degrees": 0.5,
        },
    }
