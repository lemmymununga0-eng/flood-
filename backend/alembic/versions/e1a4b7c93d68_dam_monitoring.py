"""add dam monitoring tables (additive only)

Revision ID: e1a4b7c93d68
Revises: d8e3f6a92b57

Creates new tables and seeds two registry rows with identity fields only. Coordinates,
capacity, district and province are deliberately left NULL pending verified sources.
No existing table is altered.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1a4b7c93d68"
down_revision: Union[str, Sequence[str], None] = "d8e3f6a92b57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MEAS = [
    "reservoir_level_m", "storage_m3", "storage_pct", "inflow_m3s", "outflow_m3s", "spillway_m3s",
    "turbine_m3s", "downstream_level_m", "downstream_discharge_m3s",
    "rainfall_observed_mm", "rainfall_forecast_mm",
]


def upgrade() -> None:
    dams = op.create_table(
        "dams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(60), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("river_system", sa.String(120)),
        sa.Column("district", sa.String(120)),
        sa.Column("province", sa.String(80)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("coordinate_source", sa.Text()),
        sa.Column("capacity_m3", sa.Float()),
        sa.Column("capacity_source", sa.Text()),
        sa.Column("data_provider", sa.String(160)),
        sa.Column("data_status", sa.String(20), nullable=False, server_default="no_data"),
        sa.Column("last_successful_update", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("verification_required", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_dams_slug", "dams", ["slug"], unique=True)

    op.create_table(
        "dam_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dam_id", sa.Integer(), sa.ForeignKey("dams.id"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_published_at", sa.DateTime(timezone=True)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_kind", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(160), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("quality_flag", sa.String(20), nullable=False, server_default="unverified"),
        *[sa.Column(m, sa.Float()) for m in _MEAS],
        sa.UniqueConstraint("dam_id", "observed_at", "provider", name="uq_dam_obs_dam_time_provider"),
    )
    op.create_index("ix_dam_obs_dam_time", "dam_observations", ["dam_id", "observed_at"])

    op.create_table(
        "dam_release_notices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dam_id", sa.Integer(), sa.ForeignKey("dams.id"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("issuing_body", sa.String(160), nullable=False),
    )
    op.create_index("ix_dam_release_notices_dam_id", "dam_release_notices", ["dam_id"])

    op.bulk_insert(dams, [
        {"slug": "kariba", "name": "Kariba Dam", "river_system": "Zambezi", "data_status": "no_data",
         "verification_required": True,
         "notes": "Proposed research case study. Coordinates, capacity, district/province and a data "
                  "provider are NOT yet verified. No live feed confirmed."},
        {"slug": "itezhi-tezhi", "name": "Itezhi-Tezhi Dam", "river_system": "Kafue", "data_status": "no_data",
         "verification_required": True,
         "notes": "Proposed research case study. Coordinates, capacity, district/province and a data "
                  "provider are NOT yet verified. No live feed confirmed."},
    ])


def downgrade() -> None:
    op.drop_index("ix_dam_release_notices_dam_id", table_name="dam_release_notices")
    op.drop_table("dam_release_notices")
    op.drop_index("ix_dam_obs_dam_time", table_name="dam_observations")
    op.drop_table("dam_observations")
    op.drop_index("ix_dams_slug", table_name="dams")
    op.drop_table("dams")
