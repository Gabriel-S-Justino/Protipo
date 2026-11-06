"""Brazil-wide, spatial harmonization. Derived tables are rebuilt atomically.
Original detections remain unchanged. One reference VIIRS satellite per UTC day.
"""

from collections import defaultdict
from itertools import groupby
import json
from sqlalchemy import text
from pipeline.db import get_engine
from pipeline.science import calibrate, calendar_rows, period_start, period_days
from pipeline.version import PIPELINE_VERSION

GRID = 0.5
REFERENCE = [
    "VIIRS_SNPP_SP",
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_SP",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_SP",
    "VIIRS_NOAA21_NRT",
]
MODIS = ["MODIS_SP", "MODIS_NRT"]


def _country(conn):
    row = (
        conn.execute(
            text(
                "SELECT id,name FROM regions WHERE geocode='BR' AND level='country' AND geom IS NOT NULL"
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise RuntimeError(
            "Importe os limites nacionais: python -m pipeline boundaries"
        )
    return row["id"]


def _coverage(conn):
    sources = defaultdict(set)
    for row in conn.execute(
        text(
            "SELECT source_code,day FROM acquisition_coverage WHERE scope='BR' AND day<(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date"
        )
    ):
        sources[row.day].add(row.source_code)
    viirs, modis = {}, {}
    for day, choices in sources.items():
        if chosen := next((s for s in REFERENCE if s in choices), None):
            viirs[day] = chosen
        if chosen := next((s for s in MODIS if s in choices), None):
            modis[day] = chosen
    return viirs, modis


def _raw(conn, country):
    # Deduplicate SP/NRT through canonical source selection later, and satellite
    # revisits through 0.01-degree occupied subcells x daynight x UTC day.
    return conn.execute(
        text("""
        SELECT FLOOR(d.lon/0.5)::int AS gx,FLOOR(d.lat/0.5)::int AS gy,
          (d.acquired_at AT TIME ZONE 'UTC')::date AS day,s.code,d.instrument,
          COUNT(DISTINCT (FLOOR(d.lon/0.01),FLOOR(d.lat/0.01),d.daynight))::float AS value
        FROM fire_detections d JOIN data_sources s ON s.id=d.source_id
        JOIN regions r ON r.id=:r
        WHERE d.is_demo=false AND ST_Covers(r.geom,d.geom)
          AND (d.instrument='VIIRS' OR (d.instrument='MODIS' AND d.satellite='Aqua'))
        GROUP BY 1,2,3,4,5 ORDER BY 1,2,3
    """).execution_options(stream_results=True),
        {"r": country},
    ).mappings()


def _upsert_cell(conn, gx, gy, country):
    return conn.execute(
        text("""
        WITH area AS (
          SELECT ST_PointOnSurface(ST_Intersection(r.geom,
            ST_MakeEnvelope(:x,:y,:x+0.5,:y+0.5,4326))) AS point
          FROM regions r WHERE id=:r
        )
        INSERT INTO spatial_cells(resolution,cell_key,center_lat,center_lon)
        SELECT 'br_05deg',:key,ST_Y(point),ST_X(point) FROM area WHERE NOT ST_IsEmpty(point)
        ON CONFLICT(resolution,cell_key) DO UPDATE SET center_lat=EXCLUDED.center_lat,center_lon=EXCLUDED.center_lon
        RETURNING id
    """),
        {"x": gx * GRID, "y": gy * GRID, "key": f"{gx}:{gy}", "r": country},
    ).scalar_one()


def harmonize(region_id=None, start=None, end=None):
    if start or end:
        raise ValueError(
            "A reconstrução nacional usa toda a cobertura; filtre datas na interface."
        )
    with get_engine().begin() as conn:
        country = _country(conn)
        viirs_days, modis_days = _coverage(conn)
        if not viirs_days:
            raise RuntimeError(
                "Sem cobertura VIIRS verificada. Faça fetch + ingest nacional antes de harmonizar."
            )
        # Shared calendar months; same acquisition dates for both sensors, zeros included.
        common = set(viirs_days) & set(modis_days)
        shared = defaultdict(list)
        for day in sorted(common):
            shared[day.replace(day=1)].append(day)
        shared = {
            p: ds for p, ds in shared.items() if set(period_days(p, "month")) <= common
        }
        conn.execute(
            text(
                "DELETE FROM calendar_probabilities WHERE region_id IN (SELECT id FROM regions WHERE geom IS NOT NULL AND is_demo=false)"
            )
        )
        conn.execute(
            text(
                "DELETE FROM harmonized_series WHERE region_id IN (SELECT id FROM regions WHERE geom IS NOT NULL AND is_demo=false)"
            )
        )
        # Derived models are retained for provenance (their id identifies the build).
        calibrated = 0
        cells_count = 0
        rows_count = 0
        insert = text("""
            INSERT INTO harmonized_series(region_id,cell_id,period_type,period_start,value_source,
                instrument_used,value_raw,value_viirs,ci_low,ci_high,model_id,quality_flag,is_demo,coverage_fraction,method)
            VALUES(:r,:cell,:kind,:day,:source,:instrument,:raw,:value,:lo,:hi,:model,:quality,false,:coverage,'grid_01deg_occupied')
        """)
        # Server-side cursor and one cell in memory at a time for national histories.
        raw_rows = _raw(conn, country)
        for (gx, gy), group in groupby(
            raw_rows, key=lambda row: (row["gx"], row["gy"])
        ):
            counts = {"MODIS": {}, "VIIRS": {}}
            for row in group:
                selection = viirs_days if row["instrument"] == "VIIRS" else modis_days
                if selection.get(row["day"]) == row["code"]:
                    counts[row["instrument"]][row["day"]] = row["value"]
            if not counts["MODIS"] and not counts["VIIRS"]:
                continue
            cells_count += 1
            inserts = []
            cell = _upsert_cell(conn, gx, gy, country)
            pairs = [
                (
                    p.year,
                    sum(counts["MODIS"].get(d, 0) for d in ds),
                    sum(counts["VIIRS"].get(d, 0) for d in ds),
                )
                for p, ds in shared.items()
            ]
            model = calibrate(pairs)
            model_id = None
            usable = bool(model and model["validated"])
            if usable:
                calibrated += 1
                model_id = conn.execute(
                    text("""
                    INSERT INTO harmonization_models(name,method,region_level,params,metrics,quality,pipeline_version)
                    VALUES(:name,'cell_ratio_bootstrap','grid',CAST(:params AS jsonb),CAST(:metrics AS jsonb),'medium',:v)
                    RETURNING id
                """),
                    {
                        "name": f"BR {gx}:{gy}",
                        "params": json.dumps({"cell_id": cell, **model}),
                        "metrics": json.dumps(model),
                        "v": PIPELINE_VERSION,
                    },
                ).scalar_one()
            covered = set(viirs_days) | (set(modis_days) if usable else set())
            daily = []
            # Sparse positives in the database; negatives recovered only from verified coverage.
            for day in sorted(set(counts["VIIRS"]) | set(counts["MODIS"])):
                if day not in covered:
                    continue
                direct = day in viirs_days
                raw = (
                    counts["VIIRS"].get(day, 0)
                    if direct
                    else counts["MODIS"].get(day, 0)
                )
                value = raw if direct else raw * model["factor"]
                if value <= 0:
                    continue
                daily.append(
                    {
                        "r": country,
                        "cell": cell,
                        "day": day,
                        "kind": "day",
                        "raw": raw,
                        "value": value,
                        "lo": None if direct else raw * model["low"],
                        "hi": None if direct else raw * model["high"],
                        "source": "viirs_raw" if direct else "modis_harmonized",
                        "instrument": "VIIRS" if direct else "MODIS",
                        "model": None if direct else model_id,
                        "quality": "ok" if direct else "low_confidence",
                        "coverage": 1.0,
                    }
                )
            inserts.extend(daily)
            for kind in ("week", "month"):
                groups = defaultdict(list)
                for row in daily:
                    groups[period_start(row["day"], kind)].append(row)
                for begin, rows in groups.items():
                    days = period_days(begin, kind)
                    fraction = sum(d in covered for d in days) / len(days)
                    inserts.append(
                        {
                            "r": country,
                            "cell": cell,
                            "day": begin,
                            "kind": kind,
                            "raw": sum(r["raw"] for r in rows),
                            "value": sum(r["value"] for r in rows),
                            "lo": None,
                            "hi": None,
                            "source": (
                                "modis_harmonized"
                                if any(r["model"] for r in rows)
                                else "viirs_raw"
                            ),
                            "instrument": "VIIRS",
                            "model": model_id,
                            "quality": "ok" if fraction == 1 else "insufficient",
                            "coverage": fraction,
                        }
                    )
            if inserts:
                for offset in range(0, len(inserts), 5000):
                    conn.execute(insert, inserts[offset : offset + 5000])
                rows_count += len(inserts)
        raw_rows.close()
        if not rows_count:
            raise RuntimeError(
                "Nenhuma detecção nacional com cobertura verificada; preservado o produto anterior."
            )
        # Regional total rows are not necessary: the API sums the national grid after spatial selection.
    return {
        "status": "ok",
        "cells": cells_count,
        "calibrated_cells": calibrated,
        "rows": rows_count,
        "unit": "occupied 0.01 degree subcells × UTC day × daynight (VIIRS scale)",
        "note": "Uncalibrated MODIS periods are excluded; 0.5 degree analysis grid.",
    }


def calendar(region_id=None):
    with get_engine().begin() as conn:
        country = _country(conn)
        viirs_days, modis_days = _coverage(conn)
        direct = set(viirs_days)
        model_cells = set()
        # Models may be valid even when historical MODIS has no positive rows.
        for row in conn.execute(
            text("""
            SELECT DISTINCT h.cell_id FROM harmonized_series h
            JOIN harmonization_models m ON h.model_id=m.id WHERE h.region_id=:r
              AND h.is_demo=false AND m.method='cell_ratio_bootstrap'
        """),
            {"r": country},
        ):
            model_cells.add(row.cell_id)
        conn.execute(
            text("DELETE FROM calendar_probabilities WHERE region_id=:r"),
            {"r": country},
        )
        written = 0
        insert = text("""
            INSERT INTO calendar_probabilities(region_id,cell_id,period_type,period_of_year,
                probability,ci_low,ci_high,years_used,eligible_years,expected_count,harmonized_share,
                method,pipeline_version,confidence,is_demo,validation)
            VALUES(:r,:cell,:kind,:bucket,:probability,:ci_low,:ci_high,:years_used,:years_used,
                :expected_count,:share,'coverage_empirical',:version,:confidence,false,CAST(:validation AS jsonb))
        """)
        rows = conn.execute(
            text("""
            SELECT h.cell_id,h.period_start,h.value_viirs FROM harmonized_series h
            JOIN spatial_cells c ON c.id=h.cell_id
            WHERE h.region_id=:r AND h.period_type='day' AND h.is_demo=false AND c.resolution='br_05deg'
            ORDER BY h.cell_id,h.period_start
        """).execution_options(stream_results=True),
            {"r": country},
        ).mappings()
        for cell, group in groupby(rows, key=lambda row: row["cell_id"]):
            values = {row["period_start"]: row["value_viirs"] for row in group}
            covered = direct | (set(modis_days) if cell in model_cells else set())
            for kind in ("week", "month"):
                for period, result in calendar_rows(values, covered, kind).items():
                    conn.execute(
                        insert,
                        {
                            "r": country,
                            "cell": cell,
                            "kind": kind,
                            "bucket": period,
                            **{k: v for k, v in result.items() if k != "validation"},
                            "validation": json.dumps(result["validation"]),
                            "share": None,
                            "version": PIPELINE_VERSION,
                        },
                    )
                    written += 1
        rows.close()
        if not written:
            raise RuntimeError(
                "Sem estimativas: são necessários pelo menos 3 anos com cobertura completa."
            )
    return {
        "status": "ok",
        "rows": written,
        "note": "Complete weeks/months; >=3 years; Wilson interval; rolling-origin Brier.",
    }


def anomalies(region_id=None):
    # Anomalies use the same unified grid, never sums of MODIS and VIIRS.
    with get_engine().begin() as conn:
        country = _country(conn)
        conn.execute(
            text("DELETE FROM anomaly_results WHERE region_id=:r AND is_demo=false"),
            {"r": country},
        )
        result = conn.execute(
            text("""
            INSERT INTO anomaly_results(region_id,cell_id,period_start,period_end,observed,expected,score,
                level,method,notes,pipeline_version,is_demo)
            WITH history AS (
              SELECT h.*, EXTRACT(MONTH FROM period_start) AS month
              FROM harmonized_series h WHERE region_id=:r AND period_type='month'
                AND is_demo=false AND coverage_fraction=1
            ), scored AS (
              SELECT h.*,b.expected,b.sd,b.n FROM history h
              LEFT JOIN LATERAL (
                SELECT AVG(x.value_viirs) AS expected,STDDEV(x.value_viirs) AS sd,COUNT(*) AS n
                FROM history x WHERE x.cell_id=h.cell_id AND x.month=h.month
                  AND x.period_start<h.period_start
              ) b ON true
            )
            SELECT :r,cell_id,period_start,(period_start+interval '1 month'-interval '1 day')::date,
              value_viirs,expected,CASE WHEN n>=3 AND sd>0 THEN (value_viirs-expected)/sd END,
              CASE WHEN n>=3 AND sd>0 AND (value_viirs-expected)/sd>=3 THEN 'alert'
                   WHEN n>=3 AND sd>0 AND (value_viirs-expected)/sd>=2 THEN 'warning' ELSE 'info' END,
              'unified_prior_zscore','Base anterior; série esparsa, zeros não usados nesta análise exploratória.',:v,false
            FROM scored
        """),
            {"r": country, "v": PIPELINE_VERSION},
        )
    return {"status": "ok", "rows": result.rowcount}
