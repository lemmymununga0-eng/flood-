"""add sms_subscribers table

Revision ID: c7d2e5f81a46
Revises: b4c1a7e92f30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7d2e5f81a46"
down_revision: Union[str, Sequence[str], None] = "b4c1a7e92f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sms_subscribers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sms_subscribers_phone", "sms_subscribers", ["phone"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_sms_subscribers_phone", table_name="sms_subscribers")
    op.drop_table("sms_subscribers")
