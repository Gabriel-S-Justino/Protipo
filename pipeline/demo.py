"""Dados sintéticos DEMO — sempre identificados com is_demo = true.

Regras do projeto: apenas para testes/demonstração; nunca misturados com dados
reais sem identificação visível; comandos explícitos para popular (seed-demo) e
limpar (clear-demo).

Modelagem sintética (didática, NÃO científica):
- Grade 10×10 células cobrindo o bbox do Ceará.
- Peso sazonal mensal com pico no 2º semestre (nível baixo de realismo).
- Qtde por célula/mês: Poisson(viirs_eq * scale), com scale=0.35 para MODIS
  (2000-2011) simulando o coeficiente calibrário MODIS→VIIRS, e scale=1.0 com
  instrumento VIIRS (S-NPP) a partir de 2012 — para exercitar a série unificada.
- Confiança: VIIRS l/n/h; MODIS numérica 0-100 (aproximação DEMO).
- Padroniza comparação UI/API nos modos "DEMO" (exibição sempre rotulada).
"""

from __future__ import annotations

import datetime as dt
import json

import numpy as np
from sqlalchemy import text

from pipeline.db import get_engine

CEARA_BBOX = (-39.3, -7.9, -37.2, -2.8)  # west, south, east, north
GRID = 10
from pipeline.version import PIPELINE_VERSION

RNG = np.random.default_rng(seed=42)

# Peso sazonal mensal didático (seca/queimadas no 2º semestre no Ceará)
SEASONAL = np.array([0.2, 0.2, 0.3, 0.3, 0.4, 0.6, 0.9, 1.2, 1.5, 1.0, 0.5, 0.3])
SEASONAL = SEASONAL / SEASONAL.sum()


def seed_demo(rows: int = 5000, years: int = 5) -> dict:
    engine = get_engine()
    now_utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    start_year = now_utc.year - years
    end_year = now_utc.year

    west, south, east, north = CEARA_BBOX
    lat_step = (north - south) / GRID
    lon_step = (east - west) / GRID
    lats = np.arange(GRID) * lat_step + south + lat_step / 2
    lons = np.arange(GRID) * lon_step + west + lon_step / 2

    detections: list[tuple] = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Contagem média de focos mês/célula na escala VIIRS (didática)
            viirs_eq = SEASONAL[month - 1] * 24.0
            for la in lats:
                for lo in lons:
                    if year >= 2012:
                        instrument, satellite = "VIIRS", "Suomi-NPP"
                        conf_raw = str(RNG.choice(["l", "n", "h"], p=[0.3, 0.5, 0.2]))
                        conf_norm = {"l": 0.0, "n": 50.0, "h": 100.0}[conf_raw]
                        scale = 1.0
                    else:
                        instrument, satellite = "MODIS", "Aqua" if year >= 2002 else "Terra"
                        conf_num = int(RNG.integers(10, 90))
                        conf_raw, conf_norm = str(conf_num), float(conf_num)
                        scale = 0.35  # MODIS detecta ~35% da contagem na escala VIIRS (DEMO)
                    count = int(RNG.poisson(max(viirs_eq * scale, 0.01)))
                    for _ in range(count):
                        if len(detections) >= rows:
                            break
                        ts = dt.datetime(
                            year, month, int(RNG.integers(1, 29)), int(RNG.choice([1, 13, 10])), int(RNG.integers(0, 60))
                        )
                        if ts > now_utc:
                            continue
                        daynight = "N" if ts.hour < 6 else "D"
                        frp = float(RNG.lognormal(0, 1.0 if instrument == "MODIS" else 0.6))
                        lat = float(la + RNG.normal(0, lat_step / 3))
                        lon = float(lo + RNG.normal(0, lon_step / 3))
                        detections.append((satellite, instrument, ts, lat, lon, daynight, conf_raw, conf_norm, frp))

    stats = {"inserted": 0, "duplicated": 0}
    with engine.begin() as conn:
        src_row = conn.execute(
            text(
                """
                INSERT INTO data_sources (code, sensor, satellite, product, mode, active, notes)
                VALUES ('DEMO_SYNTHETIC', 'VIIRS', 'DEMO', 'synthetic', 'SP', FALSE,
                        'Dados sintéticos DEMO — nunca apresentados como reais')
                ON CONFLICT (code) DO UPDATE SET notes = EXCLUDED.notes
                RETURNING id
                """
            )
        ).fetchone()
        if src_row is None:
            src_row = conn.execute(
                text("SELECT id FROM data_sources WHERE code = 'DEMO_SYNTHETIC'")
            ).fetchone()
        source_id = int(src_row[0])

        inserted_batch = conn.execute(
            text(
                """
                INSERT INTO pipeline_runs (command, status, pipeline_version, params)
                VALUES ('seed-demo', 'running', :v, CAST(:p AS jsonb))
                RETURNING id
                """
            ),
            {"v": PIPELINE_VERSION, "p": json.dumps({"rows": rows, "years": years})},
        ).fetchone()
        _ = inserted_batch

        for satellite, instrument, ts, lat, lon, daynight, conf_raw, conf_norm, frp in detections:
            res = conn.execute(
                text(
                    """
                    INSERT INTO fire_detections (
                      source_id, satellite, instrument, acquired_at, lat, lon,
                      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), daynight,
                      confidence_raw, confidence_norm, frp, is_demo
                    ) VALUES (
                      :source_id, :satellite, :instrument, :acquired_at, :lat, :lon,
                      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :daynight,
                      :confidence_raw, :confidence_norm, :frp, TRUE
                    )
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "source_id": source_id,
                    "satellite": satellite,
                    "instrument": instrument,
                    "acquired_at": ts,
                    "lat": lat,
                    "lon": lon,
                    "daynight": daynight,
                    "confidence_raw": conf_raw,
                    "confidence_norm": conf_norm,
                    "frp": frp,
                },
            ).rowcount
            if res:
                stats["inserted"] += 1
            else:
                stats["duplicated"] += 1

        conn.execute(
            text(
                "UPDATE pipeline_runs SET status='ok', finished_at=now(), result=CAST(:r AS jsonb) "
                "WHERE id = :id AND command = 'seed-demo'"
            ),
            {"r": json.dumps(stats), "id": int(inserted_batch[0])},
        )

    return {
        "status": "ok",
        "rows_requested": rows,
        "detections_generated": len(detections),
        **stats,
    }


def clear_demo() -> dict:
    engine = get_engine()
    with engine.begin() as conn:
        deleted = conn.execute(
            text("DELETE FROM fire_detections WHERE is_demo = TRUE")
        ).rowcount
        conn.execute(
            text(
                "INSERT INTO pipeline_runs (command, status, pipeline_version, result) "
                "VALUES ('clear-demo', 'ok', :v, CAST(:r AS jsonb))"
            ),
            {"v": PIPELINE_VERSION, "r": json.dumps({"deleted": int(deleted)})},
        )
    return {"status": "ok", "deleted": int(deleted)}
