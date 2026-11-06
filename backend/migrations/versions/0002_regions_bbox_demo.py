"""0002: regions recebe bbox analítico + flag de dados demo.

Motivo: sem malha IBGE ingestada ainda, regiões analíticas (Ceará) são
delimitadas por bbox (proveniência documentada em boundary_file/version).
`is_demo` marca regiões EXEMPLO (DEMO) para nunca se misturarem aos reais.

Revision ID: 0002_regions_bbox_demo
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_regions_bbox_demo"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("regions", sa.Column("is_demo", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.add_column("regions", sa.Column("bbox_w", sa.Float, nullable=True))
    op.add_column("regions", sa.Column("bbox_e", sa.Float, nullable=True))
    op.add_column("regions", sa.Column("bbox_s", sa.Float, nullable=True))
    op.add_column("regions", sa.Column("bbox_n", sa.Float, nullable=True))
    op.create_index("ix_regions_is_demo", "regions", ["is_demo"])


def downgrade() -> None:
    op.drop_index("ix_regions_is_demo", table_name="regions")
    op.drop_column("regions", "bbox_n")
    op.drop_column("regions", "bbox_s")
    op.drop_column("regions", "bbox_e")
    op.drop_column("regions", "bbox_w")
    op.drop_column("regions", "is_demo")
