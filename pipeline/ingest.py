"""Ingestão idempotente de CSVs FIRMS no banco.

Etapas: identificar fonte, checksum, normalizar (validação de coordenadas/datas/confiança),
deduplicar e persistir em lote; relatório em ingestion_batches. Originais nunca alterados:
reprocessar o mesmo arquivo é seguro (checksum + ON CONFLICT DO NOTHING).
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from sqlalchemy import text

from pipeline.db import INSERT_DETECTION_SQL, get_engine
from pipeline.normalization import SOURCES, SAT_BY_SOURCE, normalize_csv_text

from pipeline.version import PIPELINE_VERSION


def get_source_id(source_code: str, conn) -> int:
    """ID da data_source, inserindo-a de forma idempotente se não existir."""
    row = conn.execute(
        text("SELECT id FROM data_sources WHERE code = :c"), {"c": source_code}
    ).fetchone()
    if row is None:
        info = SOURCES[source_code]
        hint = SAT_BY_SOURCE.get(source_code, "Terra")
        conn.execute(
            text(
                """
                INSERT INTO data_sources (code, sensor, satellite, product, mode, active)
                VALUES (:code, :sensor, :satellite, :product, :mode, TRUE)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {
                "code": source_code,
                "sensor": info["sensor"],
                "satellite": hint,
                "product": "C6.1" if info["sensor"] == "MODIS" else "VNP14IMGML",
                "mode": "SP" if "_SP" in source_code else "NRT",
            },
        )
        row = conn.execute(
            text("SELECT id FROM data_sources WHERE code = :c"), {"c": source_code}
        ).fetchone()
    return int(row[0])


def ingest_file(path: Path, source_code: str) -> dict:
    engine = get_engine()
    raw_bytes = path.read_bytes()
    checksum = hashlib.sha256(raw_bytes).hexdigest()
    started = time.perf_counter()

    with engine.begin() as conn:
        # Idempotência por checksum confirmado anteriormente.
        seen = conn.execute(
            text(
                "SELECT 1 FROM ingestion_batches WHERE checksum = :c AND status = 'ok' LIMIT 1"
            ),
            {"c": checksum},
        ).fetchone()
        if seen:
            return {"file": str(path), "status": "skipped", "reason": "checksum já processado"}

        result = normalize_csv_text(raw_bytes.decode("utf-8", errors="replace"), source_code)
        source_id = get_source_id(source_code, conn)

        conn.execute(
            text(
                """
                INSERT INTO pipeline_runs (command, status, pipeline_version, params)
                VALUES ('ingest', 'running', :v, CAST(:p AS jsonb))
                """
            ),
            {"v": PIPELINE_VERSION, "p": json.dumps({"file": path.name})},
        )

        accepted = 0
        for rec in result.records:
            conn.execute(
                INSERT_DETECTION_SQL,
                {
                    "source_id": source_id,
                    "satellite": rec.satellite,
                    "instrument": rec.instrument,
                    "acquired_at": rec.acquired_at,
                    "lat": rec.lat,
                    "lon": rec.lon,
                    "daynight": rec.daynight,
                    "confidence_raw": rec.confidence_raw,
                    "confidence_norm": rec.confidence_norm,
                    "frp": rec.frp,
                    "brightness": rec.brightness,
                    "bright_t31": rec.bright_t31,
                    "scan": rec.scan,
                    "track": rec.track,
                    "version": rec.version,
                    "raw_attributes": json.dumps(rec.raw_attributes),
                    "is_demo": False,
                },
            )
            accepted += 1

        conn.execute(
            text(
                """
                INSERT INTO ingestion_batches (
                  source_code, source_url, checksum, records_total, records_accepted,
                  records_rejected, records_duplicated, status, pipeline_version
                ) VALUES (
                  :source_code, :url, :checksum, :total, :accepted,
                  :rejected, :duplicated, 'ok', :version
                )
                """
            ),
            {
                "source_code": source_code,
                "url": f"local:{path.name}",
                "checksum": checksum,
                "total": accepted + len(result.rejects),
                "accepted": accepted,
                "rejected": len(result.rejects),
                "duplicated": result.duplicates_in_file,
                "version": PIPELINE_VERSION,
            },
        )

    duration = time.perf_counter() - started
    return {
        "file": str(path),
        "status": "ok",
        "accepted": accepted,
        "rejected": len(result.rejects),
        "duplicated_in_file": result.duplicates_in_file,
        "rejects_sample": [r.__dict__ for r in result.rejects[:20]],
        "duration_s": round(duration, 2),
    }


def ingest(paths: list[str], source_code: str) -> dict:
    if source_code not in SOURCES:
        raise ValueError(f"Fonte inválida: {source_code} (válidas: {', '.join(sorted(SOURCES))})")
    results = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            results.append({"file": p, "status": "error", "reason": "arquivo não encontrado"})
            continue
        results.append(ingest_file(path, source_code))
    return {"source": source_code, "files": results}
