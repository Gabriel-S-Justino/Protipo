"""Schemas Pydantic v2 da API."""

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    env: str
    database: Optional[str] = None  # "up" | "down" | None (indisponível)
    version: str


class ApiError(BaseModel):
    error: str
    detail: Optional[str] = None


class DetectionOut(BaseModel):
    detection_id: int
    satellite: str
    instrument: str
    acquired_at: datetime
    lat: float
    lon: float
    daynight: str
    confidence_raw: Optional[str] = None
    confidence_norm: Optional[float] = None
    frp: Optional[float] = None
    is_demo: bool


class DashboardSummary(BaseModel):
    total: int = 0
    last_30d: int = 0
    last_30d_avg_hist: Optional[float] = None
    unified_series_note: str = (
        "Série unificada na escala VIIRS: MODIS (2000–2011) harmonizado + VIIRS direto (2012→)."
    )


class CoverageOut(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    instruments: list[str] = Field(default_factory=list)
    harmonized_share: Optional[float] = None


class CalendarCell(BaseModel):
    period_of_year: int
    probability: float
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    years_used: int
    expected_count: Optional[float] = None
    harmonized_share: Optional[float] = None
    confidence: str


class RegionOut(BaseModel):
    id: int
    level: str
    name: str
    geocode: Optional[str] = None
