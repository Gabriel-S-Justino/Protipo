"""FIRMS downloads with dated cache and a coverage sidecar (including valid empty CSVs)."""

import csv
import hashlib
import io
import json
import logging
import time
from datetime import date as Date, datetime, timedelta, timezone
from pathlib import Path
import requests
from pipeline.config import get_settings
from pipeline.geography import BRAZIL_BBOX

logger = logging.getLogger(__name__)
FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api"
MAX_DAY_RANGE = 5


def _dates(day_range, date=None):
    today = datetime.now(timezone.utc).date()
    start = Date.fromisoformat(date) if date else today - timedelta(days=day_range - 1)
    return start, start + timedelta(days=day_range - 1)


def _cache_path(source, bbox, day_range, date=None):
    start, end = _dates(day_range, date)
    digest = hashlib.sha256(f"{source}|{bbox}|{start}|{end}".encode()).hexdigest()[:16]
    return Path(get_settings().data_dir) / "raw" / f"{source}_{digest}.csv"


def _key():
    key = get_settings().map_key
    if not key:
        raise RuntimeError("MAP_KEY ausente; configure a chave NASA FIRMS no ambiente.")
    return key


def data_availability(source):
    response = requests.get(
        f"{FIRMS_BASE}/data_availability/csv/{_key()}/{source}", timeout=60
    )
    if not response.ok:
        raise RuntimeError(
            f"Disponibilidade FIRMS indisponível (HTTP {response.status_code})."
        )
    return response.text


def fetch_area(source, bbox=BRAZIL_BBOX, day_range=1, date=None):
    if not 1 <= day_range <= MAX_DAY_RANGE:
        raise ValueError("day_range deve estar entre 1 e 5")
    start, end = _dates(day_range, date)
    path = _cache_path(source, bbox, day_range, date)
    sidecar = path.with_suffix(".json")
    # Recent windows are mutable; never cache them indefinitely.
    immutable = end < datetime.now(timezone.utc).date() - timedelta(days=7)
    if immutable and path.is_file() and sidecar.is_file():
        return path.read_text(encoding="utf-8")
    availability = list(csv.DictReader(io.StringIO(data_availability(source))))
    valid = any(
        row.get("min_date")
        and row.get("max_date")
        and Date.fromisoformat(row["min_date"][:10]) <= start
        and Date.fromisoformat(row["max_date"][:10]) >= end
        for row in availability
    )
    if not valid:
        raise ValueError(
            f"{source}: janela {start} a {end} fora da disponibilidade confirmada."
        )
    url = f"{FIRMS_BASE}/area/csv/{_key()}/{source}/{','.join(map(str,bbox))}/{day_range}/{start}"
    payload = None
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=90)
            if response.ok:
                payload = response.text
                break
            logger.warning(
                "FIRMS %s HTTP %s (tentativa %s)",
                source,
                response.status_code,
                attempt + 1,
            )
        except requests.RequestException:
            logger.warning("FIRMS %s: erro de rede (tentativa %s)", source, attempt + 1)
        time.sleep(2**attempt)
    if payload is None:
        raise RuntimeError(f"Falha ao baixar {source}: {start} a {end}.")
    if payload.strip():
        header = next(csv.reader(io.StringIO(payload)))
        if not {"latitude", "longitude", "acq_date"}.issubset(
            {h.strip().lower() for h in header}
        ):
            raise ValueError(
                f"Resposta FIRMS inválida para {source}; cobertura não registrada."
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    sidecar.write_text(
        json.dumps(
            {
                "source": source,
                "start": str(start),
                "end": str(end),
                "bbox": list(bbox),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "availability_verified": True,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    return payload
