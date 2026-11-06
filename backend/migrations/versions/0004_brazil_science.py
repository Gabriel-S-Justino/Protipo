"""National boundaries, auditable acquisition coverage and calibrated calendar metrics."""

from alembic import op

revision = "0004_brazil_science"
down_revision = "0003_hseries_widen"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP INDEX ix_ingestion_batches_checksum")
    op.execute(
        "CREATE UNIQUE INDEX ix_ingestion_batches_checksum ON ingestion_batches(source_code,checksum)"
    )
    op.execute("DROP INDEX ix_fire_detections_idem")
    op.execute(
        "CREATE UNIQUE INDEX ix_fire_detections_idem ON fire_detections(source_id,satellite,acquired_at,lat,lon,daynight,confidence_raw)"
    )
    op.execute("ALTER TABLE regions ADD COLUMN geom geometry(MultiPolygon,4326)")
    op.execute("CREATE INDEX ix_regions_geom ON regions USING gist(geom)")
    op.execute("""
        INSERT INTO regions (level,name,geocode,is_demo,bbox_w,bbox_s,bbox_e,bbox_n)
        VALUES ('country','Brasil','BR',false,-74,-34,-28,6)
        ON CONFLICT (level,name) DO NOTHING
    """)
    op.execute("""
        CREATE TABLE acquisition_coverage (
            source_code varchar(32) NOT NULL,
            day date NOT NULL,
            scope varchar(16) NOT NULL DEFAULT 'BR',
            verified_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (source_code,day,scope)
        )
    """)
    op.execute("ALTER TABLE calendar_probabilities ADD COLUMN validation jsonb")
    op.execute("ALTER TABLE calendar_probabilities ADD COLUMN eligible_years integer")
    op.execute("ALTER TABLE harmonized_series ADD COLUMN coverage_fraction float")
    op.execute(
        "CREATE INDEX ix_hseries_cells_time ON harmonized_series(period_type,period_start,cell_id) WHERE is_demo=false"
    )


def downgrade():
    raise RuntimeError(
        "Downgrade manual necessário: a versão anterior perde proveniência SP/NRT."
    )
