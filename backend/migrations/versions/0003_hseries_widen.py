"""0003: harmonized_series.value_source e quality_flag are widened —
'modis_harmonized' / 'low_confidence' passam de 12/20 chars (evita truncamento).

Revision ID: 0003_hseries_widen
Revises: 0002_regions_bbox_demo
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_hseries_widen"
down_revision = "0002_regions_bbox_demo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "harmonized_series", "value_source",
        existing_type=sa.String(12), type_=sa.String(24),
    )
    op.alter_column(
        "harmonized_series", "quality_flag",
        existing_type=sa.String(20), type_=sa.String(24),
    )


def downgrade() -> None:
    op.alter_column(
        "harmonized_series", "quality_flag",
        existing_type=sa.String(24), type_=sa.String(20),
    )
    op.alter_column(
        "harmonized_series", "value_source",
        existing_type=sa.String(24), type_=sa.String(12),
    )
