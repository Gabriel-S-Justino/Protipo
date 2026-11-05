"""Schema inicial: PostGIS + tabelas do núcleo (fontes, ingestões, detecções,
regiões, células, agregados, harmonização, série, calendário, anomalias).

Importante: extensão PostGIS via `CREATE EXTENSION IF NOT EXISTS postgis`
executada em ambiente de teste exige superusuário/plano com suporte — no Neon/Supabase é habilitada.

Revision ID: 0001_initial
Revises: None
Create Date: 2026-11-05
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensões espaciais (PostGIS) — habilitar antes de qualquer geometry().
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # --- data_sources -------------------------------------------------------
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("sensor", sa.String(16), nullable=False),
        sa.Column("satellite", sa.String(24), nullable=False),
        sa.Column("product", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, default=True),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # --- ingestion_batches --------------------------------------------------
    op.create_table(
        "ingestion_batches",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("source_code", sa.String(32), nullable=False),
        sa.Column("period_start", sa.Date, nullable=True),
        sa.Column("period_end", sa.Date, nullable=True),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("records_total", sa.Integer, nullable=False, default=0),
        sa.Column("records_accepted", sa.Integer, nullable=False, default=0),
        sa.Column("records_rejected", sa.Integer, nullable=False, default=0),
        sa.Column("records_duplicated", sa.Integer, nullable=False, default=0),
        sa.Column(
            "status", sa.String(16), nullable=False, default="pending"
        ),  # pending|ok|error|partial
        sa.Column("pipeline_version", sa.String(32), nullable=False),
        sa.Column("params", pg.JSONB, nullable=True),
        sa.Column("errors", pg.JSONB, nullable=True),
        sa.Column("duration_s", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_ingestion_batches_checksum", "ingestion_batches", ["checksum"], unique=True
    )

    # --- pipeline_runs ------------------------------------------------------
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("command", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, default="running"),
        sa.Column("pipeline_version", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("params", pg.JSONB, nullable=True),
        sa.Column("result", pg.JSONB, nullable=True),
        sa.Column("errors", pg.JSONB, nullable=True),
    )

    # --- fire_detections: originais normalizados (NUNCA alterados) ----------
    op.create_table(
        "fire_detections",
        sa.Column("detection_id", sa.BigInteger, primary_key=True),
        sa.Column(
            "source_id", sa.Integer, sa.ForeignKey("data_sources.id", ondelete="RESTRICT")
        ),
        sa.Column("source_record_id", sa.String(64), nullable=True),
        sa.Column("satellite", sa.String(24), nullable=False),
        sa.Column("instrument", sa.String(12), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lon", sa.Float, nullable=False),
        # geometry criada a seguir (psycopg/SQLAlchemy não tem geometry nativa aqui):
        sa.Column("daynight", sa.String(1), nullable=False, default="D"),
        sa.Column("confidence_raw", sa.String(16), nullable=True),
        sa.Column("confidence_norm", sa.Float, nullable=True),
        sa.Column("frp", sa.Float, nullable=True),
        sa.Column("brightness", sa.Float, nullable=True),
        sa.Column("bright_t31", sa.Float, nullable=True),
        sa.Column("scan", sa.Float, nullable=True),
        sa.Column("track", sa.Float, nullable=True),
        sa.Column("version", sa.Float, nullable=True),
        sa.Column("raw_attributes", pg.JSONB, nullable=True),
        sa.Column("is_demo", sa.Boolean, nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE fire_detections ADD COLUMN geom geometry(Point, 4326);")
    op.create_index(
        "ix_fire_detections_idem",
        "fire_detections",
        ["satellite", "acquired_at", "lat", "lon", "daynight", "confidence_raw"],
        unique=True,
    )
    op.create_index("ix_fire_detections_date_sat", "fire_detections", ["acquired_at", "instrument"])
    op.create_index("ix_fire_detections_geom", "fire_detections", ["geom"], postgresql_using="gist")
    op.create_index("ix_fire_detections_demo", "fire_detections", ["is_demo"])

    # --- regions ------------------------------------------------------------
    op.create_table(
        "regions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("level", sa.String(12), nullable=False),  # state|municipality|custom
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("regions.id", ondelete="CASCADE")),
        sa.Column("geocode", sa.String(16), nullable=True),  # código IBGE do município
        sa.Column("boundary_file", sa.Text, nullable=True),
        sa.Column("boundary_version", sa.String(64), nullable=True),
    )
    op.create_index("ix_regions_level_name", "regions", ["level", "name"], unique=True)

    # --- spatial_cells ------------------------------------------------------
    op.create_table(
        "spatial_cells",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("resolution", sa.String(12), nullable=False),
        sa.Column("cell_key", sa.String(64), nullable=False),
        sa.Column("center_lat", sa.Float, nullable=False),
        sa.Column("center_lon", sa.Float, nullable=False),
    )
    op.create_index(
        "ix_spatial_cells_res_key", "spatial_cells", ["resolution", "cell_key"], unique=True
    )

    # --- cell_period_aggregates --------------------------------------------
    op.create_table(
        "cell_period_aggregates",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("cell_id", sa.BigInteger, sa.ForeignKey("spatial_cells.id", ondelete="CASCADE")),
        sa.Column("period_type", sa.String(8), nullable=False),  # day|week|month
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("satellite", sa.String(24), nullable=False),
        sa.Column("instrument", sa.String(12), nullable=False),
        sa.Column("daynight", sa.String(1), nullable=True),
        sa.Column("count", sa.Integer, nullable=False, default=0),
        sa.Column("frp_sum", sa.Float, nullable=True),
        sa.Column("confidence_dist", pg.JSONB, nullable=True),
        sa.Column("is_demo", sa.Boolean, nullable=False, default=False),
    )
    op.create_index(
        "ix_cpa_lookup",
        "cell_period_aggregates",
        ["cell_id", "period_type", "period_start", "instrument"],
    )

    # --- harmonization_models ----------------------------------------------
    op.create_table(
        "harmonization_models",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("region_level", sa.String(12), nullable=True),
        sa.Column("calib_start", sa.Date, nullable=True),
        sa.Column("calib_end", sa.Date, nullable=True),
        sa.Column("daynight", sa.String(1), nullable=True),
        sa.Column("params", pg.JSONB, nullable=True),
        sa.Column("metrics", pg.JSONB, nullable=True),
        sa.Column("quality", sa.String(20), nullable=False, default="low"),
        sa.Column("pipeline_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- harmonized_series --------------------------------------------------
    op.create_table(
        "harmonized_series",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("cell_id", sa.BigInteger, sa.ForeignKey("spatial_cells.id", ondelete="CASCADE"), nullable=True),
        sa.Column("period_type", sa.String(8), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("value_source", sa.String(12), nullable=False),  # viirs_raw|modis_harmonized
        sa.Column("instrument_used", sa.String(12), nullable=False),
        sa.Column("value_raw", sa.Float, nullable=False),
        sa.Column("value_viirs", sa.Float, nullable=False),
        sa.Column("ci_low", sa.Float, nullable=True),
        sa.Column("ci_high", sa.Float, nullable=True),
        sa.Column("frp_sum", sa.Float, nullable=True),
        sa.Column("method", sa.String(32), nullable=True),
        sa.Column("model_id", sa.Integer, sa.ForeignKey("harmonization_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quality_flag", sa.String(20), nullable=False, default="ok"),
        sa.Column("is_demo", sa.Boolean, nullable=False, default=False),
    )
    op.create_index(
        "ix_hseries_lookup",
        "harmonized_series",
        ["region_id", "cell_id", "period_type", "period_start"],
    )

    # --- calendar_probabilities --------------------------------------------
    op.create_table(
        "calendar_probabilities",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cell_id", sa.BigInteger, sa.ForeignKey("spatial_cells.id", ondelete="CASCADE"), nullable=True),
        sa.Column("period_type", sa.String(8), nullable=False, default="week"),
        sa.Column("period_of_year", sa.Integer, nullable=False),  # 1-53 (semana), 1-12 (mês), doy
        sa.Column("probability", sa.Float, nullable=False),
        sa.Column("ci_low", sa.Float, nullable=True),
        sa.Column("ci_high", sa.Float, nullable=True),
        sa.Column("years_used", sa.Integer, nullable=False, default=0),
        sa.Column("expected_count", sa.Float, nullable=True),
        sa.Column("harmonized_share", sa.Float, nullable=True),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("pipeline_version", sa.String(32), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False, default="low"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_demo", sa.Boolean, nullable=False, default=False),
    )
    op.create_index(
        "ix_calendar_lookup", "calendar_probabilities", ["region_id", "period_type", "period_of_year"]
    )

    # --- anomaly_results ----------------------------------------------------
    op.create_table(
        "anomaly_results",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("cell_id", sa.BigInteger, sa.ForeignKey("spatial_cells.id", ondelete="CASCADE"), nullable=True),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("observed", sa.Float, nullable=False),
        sa.Column("expected", sa.Float, nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("level", sa.String(12), nullable=False, default="info"),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("pipeline_version", sa.String(32), nullable=False),
        sa.Column("is_demo", sa.Boolean, nullable=False, default=False),
    )


def downgrade() -> None:
    for table in (
        "anomaly_results",
        "calendar_probabilities",
        "harmonized_series",
        "harmonization_models",
        "cell_period_aggregates",
        "spatial_cells",
        "regions",
        "fire_detections",
        "pipeline_runs",
        "ingestion_batches",
        "data_sources",
    ):
        op.drop_table(table)
    op.execute("DROP EXTENSION IF EXISTS postgis;")
