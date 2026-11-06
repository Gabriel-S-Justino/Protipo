"""Idempotent ingestion; coverage comes from acquisition metadata, never from positive rows."""

import hashlib
import json
import time
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from sqlalchemy import text
from pipeline.db import INSERT_DETECTION_SQL, get_engine
from pipeline.normalization import SOURCES, SAT_BY_SOURCE, normalize_csv_text
from pipeline.geography import BRAZIL_BBOX
from pipeline.version import PIPELINE_VERSION


def get_source_id(source_code, conn):
    info = SOURCES[source_code]
    return conn.execute(
        text("""
        INSERT INTO data_sources(code,sensor,satellite,product,mode,active)
        VALUES(:code,:sensor,:satellite,:product,:mode,true)
        ON CONFLICT(code) DO UPDATE SET active=true RETURNING id
    """),
        {
            "code": source_code,
            "sensor": info["sensor"],
            "satellite": SAT_BY_SOURCE.get(source_code, "Aqua"),
            "product": "FIRMS",
            "mode": "SP" if source_code.endswith("_SP") else "NRT",
        },
    ).scalar_one()


def _coverage(path, source, checksum, conn):
    sidecar = path.with_suffix(".json")
    if not sidecar.exists():
        return 0
    meta = json.loads(sidecar.read_text(encoding="utf-8"))
    if (
        not meta.get("availability_verified")
        or meta.get("source") != source
        or meta.get("sha256") != checksum
        or tuple(meta.get("bbox", [])) != BRAZIL_BBOX
    ):
        return 0
    day, end = date.fromisoformat(meta["start"]), date.fromisoformat(meta["end"])
    inserted = 0
    while day <= end and day < datetime.now(timezone.utc).date():
        conn.execute(
            text("""
            INSERT INTO acquisition_coverage(source_code,day,scope) VALUES(:source,:day,'BR')
            ON CONFLICT(source_code,day,scope) DO UPDATE SET verified_at=now()
        """),
            {"source": source, "day": day},
        )
        day += timedelta(days=1)
        inserted += 1
    return inserted


def ingest_file(path, source_code):
    payload = path.read_bytes()
    checksum = hashlib.sha256(payload).hexdigest()
    normalized = normalize_csv_text(payload.decode("utf-8-sig"), source_code)
    with get_engine().begin() as conn:
        seen = conn.execute(
            text(
                "SELECT 1 FROM ingestion_batches WHERE checksum=:checksum AND source_code=:source AND status='ok'"
            ),
            {"checksum": checksum, "source": source_code},
        ).first()
        if seen:
            covered = (
                _coverage(path, source_code, checksum, conn)
                if not normalized.rejects
                else 0
            )
            return {"file": str(path), "status": "skipped", "coverage_days": covered}
        source_id = get_source_id(source_code, conn)
        accepted = 0
        t0 = time.monotonic()
        for rec in normalized.records:
            values = {k: v for k, v in vars(rec).items() if k != "raw_attributes"}
            values.update(
                source_id=source_id,
                raw_attributes=json.dumps(rec.raw_attributes),
                is_demo=False,
            )
            accepted += max(0, conn.execute(INSERT_DETECTION_SQL, values).rowcount)
        duplicated = len(normalized.records) - accepted + normalized.duplicates_in_file
        conn.execute(
            text("""
            INSERT INTO ingestion_batches(source_code,source_url,checksum,records_total,records_accepted,
               records_rejected,records_duplicated,status,pipeline_version,duration_s)
            VALUES(:source,:url,:checksum,:total,:accepted,:rejected,:duplicated,'ok',:version,:duration)
        """),
            {
                "source": source_code,
                "url": f"local:{path.name}",
                "checksum": checksum,
                "total": len(normalized.records)
                + len(normalized.rejects)
                + normalized.duplicates_in_file,
                "accepted": accepted,
                "rejected": len(normalized.rejects),
                "duplicated": duplicated,
                "version": PIPELINE_VERSION,
                "duration": time.monotonic() - t0,
            },
        )
        covered = (
            _coverage(path, source_code, checksum, conn)
            if not normalized.rejects
            else 0
        )
    return {
        "file": str(path),
        "status": "ok",
        "accepted": accepted,
        "rejected": len(normalized.rejects),
        "duplicated": duplicated,
        "coverage_days": covered,
    }


def ingest(paths, source_code):
    if source_code not in SOURCES:
        raise ValueError(f"Fonte inválida: {source_code}")
    results = []
    for value in paths:
        path = Path(value)
        if not path.is_file():
            raise FileNotFoundError(path)
        results.append(ingest_file(path, source_code))
    return {"source": source_code, "files": results}
