"""Acesso ao banco pelo pipeline (conexão DIRETA, nunca a pooled)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipeline.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url_direct:
            raise RuntimeError(
                "DATABASE_URL_DIRECT (ou DATABASE_URL) não configurada — ver .env.example "
                "e docs/SETUP.md. O pipeline usa a conexão DIRETA (não pooled)."
            )
        _engine = create_engine(settings.database_url_direct, pool_pre_ping=True)
    return _engine


def fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with get_engine().connect() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]


def fetch_one(query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    rows = fetch_all(query, params)
    return rows[0] if rows else None


INSERT_DETECTION_SQL = text(
    """
    INSERT INTO fire_detections (
      source_id, satellite, instrument, acquired_at, lat, lon, geom, daynight,
      confidence_raw, confidence_norm, frp, brightness, bright_t31, scan, track,
      version, raw_attributes, is_demo
    ) VALUES (
      :source_id, :satellite, :instrument, :acquired_at, :lat, :lon,
      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :daynight,
      :confidence_raw, :confidence_norm, :frp, :brightness, :bright_t31, :scan, :track,
      :version, CAST(:raw_attributes AS jsonb), :is_demo
    )
    ON CONFLICT DO NOTHING
    """
)
