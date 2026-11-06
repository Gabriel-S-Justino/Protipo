"""Modelagem declarativa (SQLAlchemy 2.x) espelhando as migrations Alembic.

Objetivo: tipagem/FastAPI (schemas) e consistência com o schema do banco.
A fonte da verdade do DDL são as migrations em backend/migrations.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)  # ex.: VIIRS_SNPP_SP, MODIS_SP
    sensor: Mapped[str] = mapped_column(String(16))  # MODIS | VIIRS
    satellite: Mapped[str] = mapped_column(String(24))  # Terra | Aqua | S-NPP | NOAA-20 | NOAA-21
    product: Mapped[str] = mapped_column(String(32))  # C6.1 (SP/NRT) | VNP14IMGML | VNP14IMGTDL ...
    mode: Mapped[str] = mapped_column(String(8))  # SP (reprocessado) | NRT
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestionBatch(Base):
    """Um lote de ingestão: arquivo(s) baixado(s)/processado(s) + resultado."""

    __tablename__ = "ingestion_batches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_code: Mapped[str] = mapped_column(String(32))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str] = mapped_column(Text)  # URL SEM a MAP_KEY
    checksum: Mapped[str] = mapped_column(String(64))
    records_total: Mapped[int] = mapped_column(Integer, default=0)
    records_accepted: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    records_duplicated: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|ok|error|partial
    pipeline_version: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    errors: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    duration_s: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_ingestion_batches_checksum", "checksum", unique=True),)


class PipelineRun(Base):
    """Execução de um comando do pipeline (fetch/harmonize/calendar...)."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    command: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="running")  # running|ok|error
    pipeline_version: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    errors: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class FireDetection(Base):
    """Detecção original NORMALIZADA (originais intactos — harmonização nunca altera aqui)."""

    __tablename__ = "fire_detections"

    detection_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"))
    source_record_id: Mapped[str | None] = mapped_column(String(64))
    satellite: Mapped[str] = mapped_column(String(24))  # Terra/Aqua/Suomi-NPP/NOAA-20/NOAA-21
    instrument: Mapped[str] = mapped_column(String(12))  # MODIS | VIIRS
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    # geom é criado pela migration (geometry(Point,4326) com índice GiST)
    daynight: Mapped[str] = mapped_column(String(1), default="D")  # D|N
    confidence_raw: Mapped[str | None] = mapped_column(String(16))  # 0-100 ou l/n/h (original)
    confidence_norm: Mapped[float | None] = mapped_column(Float)  # escala comum documentada
    frp: Mapped[float | None] = mapped_column(Float)
    brightness: Mapped[float | None] = mapped_column(Float)
    bright_t31: Mapped[float | None] = mapped_column(Float)
    scan: Mapped[float | None] = mapped_column(Float)
    track: Mapped[float | None] = mapped_column(Float)
    version: Mapped[float | None] = mapped_column(Float)
    raw_attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_fire_detections_idem", "satellite", "acquired_at", "lat", "lon", "daynight",
              "confidence_raw", unique=True),
        Index("ix_fire_detections_date_sat", "acquired_at", "instrument"),
        Index("ix_fire_detections_demo", "is_demo"),
    )


class Region(Base):
    """Regiões analíticas: estado, município IBGE ou região personalizada.

    `is_demo` marca regiões de exemplo (dados DEMO NUNCA se misturam aos reais).
    bbox_w/e/s/n: delimitação analítica (proposta provisória até ingestar a
    malha IBGE oficial — a proveniência vem em boundary_file/boundary_version).
    """

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(12))  # state | municipality | custom
    name: Mapped[str] = mapped_column(String(128))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"))
    geocode: Mapped[str | None] = mapped_column(String(16))  # código IBGE do município
    boundary_file: Mapped[str | None] = mapped_column(Text)  # proveniência do shape/geojson
    boundary_version: Mapped[str | None] = mapped_column(String(64))  # versão/data da malha
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    bbox_w: Mapped[float | None] = mapped_column(Float, nullable=True)  # longitude oeste
    bbox_e: Mapped[float | None] = mapped_column(Float, nullable=True)  # longitude leste
    bbox_s: Mapped[float | None] = mapped_column(Float, nullable=True)  # latitude sul
    bbox_n: Mapped[float | None] = mapped_column(Float, nullable=True)  # latitude norte

    __table_args__ = (
        Index("ix_regions_is_demo", "is_demo"),
    )


class SpatialCell(Base):
    """Células de grade (múltiplas resoluções) para agregação e série harmonizada."""

    __tablename__ = "spatial_cells"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    resolution: Mapped[str] = mapped_column(String(12))  # ex.: "viirs375m" | "modis1km" | "h3_10km"
    cell_key: Mapped[str] = mapped_column(String(64))
    center_lat: Mapped[float] = mapped_column(Float)
    center_lon: Mapped[float] = mapped_column(Float)

    __table_args__ = (Index("ix_spatial_cells_res_key", "resolution", "cell_key", unique=True),)


class CellPeriodAggregate(Base):
    """Agregados pré-calculados (célula × período × satélite). Nada de estatística pesada por requisição."""

    __tablename__ = "cell_period_aggregates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cell_id: Mapped[int] = mapped_column(ForeignKey("spatial_cells.id", ondelete="CASCADE"))
    period_type: Mapped[str] = mapped_column(String(8))  # day | week | month
    period_start: Mapped[date] = mapped_column(Date)
    satellite: Mapped[str] = mapped_column(String(24))
    instrument: Mapped[str] = mapped_column(String(12))
    daynight: Mapped[str | None] = mapped_column(String(1))
    count: Mapped[int] = mapped_column(Integer, default=0)
    frp_sum: Mapped[float | None] = mapped_column(Float)
    confidence_dist: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # {l:..,n:..,h:..} ou buckets
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_cpa_lookup", "cell_id", "period_type", "period_start", "instrument"),
    )


class HarmonizationModel(Base):
    """Modelo de harmonização MODIS→VIIRS: método, parâmetros, calibração, métricas, versão."""

    __tablename__ = "harmonization_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(String(32))  # ratio | robust_regression | count_model | quantile_map
    region_level: Mapped[str | None] = mapped_column(String(12))
    calib_start: Mapped[date | None] = mapped_column(Date)
    calib_end: Mapped[date | None] = mapped_column(Date)
    daynight: Mapped[str | None] = mapped_column(String(1))
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # MAE, viés, correlação, cobertura...
    quality: Mapped[str] = mapped_column(String(20), default="low")  # low | medium | high
    pipeline_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HarmonizedSeries(Base):
    """Série unificada na escala VIIRS (valor original, valor harmonizado, incerteza, proveniência)."""

    __tablename__ = "harmonized_series"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"))
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("spatial_cells.id", ondelete="CASCADE"))
    period_type: Mapped[str] = mapped_column(String(8))  # day | week | month
    period_start: Mapped[date] = mapped_column(Date)
    value_source: Mapped[str] = mapped_column(String(24))  # viirs_raw | modis_harmonized
    instrument_used: Mapped[str] = mapped_column(String(12))  # MODIS | VIIRS
    value_raw: Mapped[float] = mapped_column(Float)
    value_viirs: Mapped[float] = mapped_column(Float)  # contagem na escala VIIRS
    ci_low: Mapped[float | None] = mapped_column(Float)
    ci_high: Mapped[float | None] = mapped_column(Float)
    frp_sum: Mapped[float | None] = mapped_column(Float)
    method: Mapped[str | None] = mapped_column(String(32))
    model_id: Mapped[int | None] = mapped_column(ForeignKey("harmonization_models.id", ondelete="SET NULL"))
    quality_flag: Mapped[str] = mapped_column(String(24), default="ok")  # ok | low_confidence | insufficient
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_hseries_lookup", "region_id", "cell_id", "period_type", "period_start"),
    )


class CalendarProbability(Base):
    """Calendário probabilístico pré-calculado (pipeline) — a API só lê aqui."""

    __tablename__ = "calendar_probabilities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"))
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("spatial_cells.id", ondelete="CASCADE"))
    period_type: Mapped[str] = mapped_column(String(8), default="week")  # day | week | month
    period_of_year: Mapped[int] = mapped_column(Integer)  # semana 1-53, mês 1-12 ou doy
    probability: Mapped[float] = mapped_column(Float)  # P(≥1 foco VIIRS-equiv. no período)
    ci_low: Mapped[float | None] = mapped_column(Float)
    ci_high: Mapped[float | None] = mapped_column(Float)
    years_used: Mapped[int] = mapped_column(Integer, default=0)
    expected_count: Mapped[float | None] = mapped_column(Float)
    harmonized_share: Mapped[float | None] = mapped_column(Float)  # fração da amostra harmonizada
    method: Mapped[str] = mapped_column(String(32))
    pipeline_version: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[str] = mapped_column(String(20), default="low")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_calendar_lookup", "region_id", "period_type", "period_of_year"),
    )


class AnomalyResult(Base):
    """Períodos/regiões historicamente atípicos, com metodologia e versão."""

    __tablename__ = "anomaly_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"))
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("spatial_cells.id", ondelete="CASCADE"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    observed: Mapped[float] = mapped_column(Float)
    expected: Mapped[float | None] = mapped_column(Float)
    score: Mapped[float | None] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(12), default="info")  # info | warning | alert
    method: Mapped[str] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)
    pipeline_version: Mapped[str] = mapped_column(String(32))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
