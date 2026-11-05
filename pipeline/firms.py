"""Cliente da NASA FIRMS (Area API, Data Availability, status da chave).

Regras:
- MAP_KEY só em variável de ambiente; log de cada chamada SEM a chave.
- Cache por checksum (não baixar duas vezes); retry com backoff; respeito aos limites.
- Antes de implementar em produção: validar formato real e especificado em
  docs/DATA_PIPELINE.md (instrução do PromptMaster §5).
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import requests

from pipeline.config import get_settings

logger = logging.getLogger("pipeline.firms")

FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api"
MAX_DAY_RANGE = 10  # limite documentado da Area API — CONFIRMAR no runtime real
RETRIES = 3
BACKOFF_S = 2.0

TIMEOUT_S = 60

_cache_dir = Path("data/raw")


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _url_for_area(source: str, bbox: tuple[float, float, float, float],
                  day_range: int, date: str | None = None) -> str:
    west, south, east, north = bbox
    key = get_settings().map_key
    if not key:
        raise RuntimeError(
            "MAP_KEY ausente: registre em https://firms.modaps.eosdis.nasa.gov/api/map_key/ "
            "e defina-a em .env. A chave é da sua conta Earthdata (gratuita)."
        )
    window = min(day_range, MAX_DAY_RANGE)
    url_date = f"/{date}" if date else ""
    return (
        f"{FIRMS_BASE}/area/csv/{key}/{source}/{west},{south},{east},{north}/{window}{url_date}"
    )


def fetch_area(source: str, bbox: tuple[float, float, float, float],
               day_range: int = 1, date: str | None = None) -> str:
    """Baixa CSV da Area API com cache local por checksum (evita re-download e conta menos
    transações contra o limite da chave)."""
    _cache_dir.mkdir(parents=True, exist_ok=True)
    payload_key = f"{source}|{','.join(str(x) for x in bbox)}|{day_range}|{date}"
    cache_name = _cache_dir / (hashlib.sha256(payload_key.encode()).hexdigest() + ".csv")
    if cache_name.is_file():
        logger.info("cache hit: %s", cache_name.name)
        return cache_name.read_text(encoding="utf-8")

    url = _url_for_area(source, bbox, day_range, date)
    logged_url = url.replace(get_settings().map_key or "", "***")
    for attempt in range(1, RETRIES + 1):
        try:
            logger.info("GET %s (tentativa %d/%d)", logged_url, attempt, RETRIES)
            resp = requests.get(url, timeout=TIMEOUT_S)
            resp.raise_for_status()
            text = resp.text
            if not text.strip():
                # FIRMS devolve string vazia quando não há detecções; não é erro.
                break
            cache_name.write_text(text, encoding="utf-8")
            return text
        except requests.RequestException as exc:
            logger.warning("Falha FIRMS (%s): %s", logged_url, exc)
            time.sleep(BACKOFF_S * attempt)
    raise RuntimeError(f"Download FIRMS falhou após {RETRIES} tentativas: {logged_url}")


def map_key_status() -> str:
    """Status de transações da MAP_KEY (endpoint público da FIRMS)."""
    key = get_settings().map_key
    if not key:
        raise RuntimeError(
            "MAP_KEY ausente; obtenha em https://firms.modaps.eosdis.nasa.gov/api/map_key/"
        )
    resp = requests.get(f"{FIRMS_BASE}/map_key_status/csv/{key}", timeout=TIMEOUT_S)
    resp.raise_for_status()
    return resp.text
