"""SMS consent fields, broadcasts and per-message delivery records

Revision ID: d8e3f6a92b57
Revises: c7d2e5f81a46
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8e3f6a92b57"
down_revision: Union[str, Sequence[str], None] = "c7d2e5f81a46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing subscribers get NULL consent_at: they were added before consent was
    # recorded, so they will not be texted until an administrator records consent.
    op.add_column("sms_subscribers", sa.Column("consent_at", sa.DateTime(), nullable=True))
    op.add_column(
        "sms_subscribers",
        sa.Column("consent_note", sa.String(length=200), nullable=False, server_default=""),
    )
    op.add_column("sms_subscribers", sa.Column("opted_out_at", sa.DateTime(), nullable=True))

    op.create_table(
        "sms_broadcasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("segments", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("environment", sa.String(length=20), nullable=False, server_default="none"),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="sending"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sms_broadcasts_content_hash", "sms_broadcasts", ["content_hash"])

    op.create_table(
        "sms_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("broadcast_id", sa.Integer(), sa.ForeignKey("sms_broadcasts.id"), nullable=False),
        sa.Column(
            "subscriber_id",
            sa.Integer(),
            sa.ForeignKey("sms_subscribers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("phone_masked", sa.String(length=20), nullable=False),
        sa.Column("submission_status", sa.String(length=12), nullable=False, server_default="pending"),
        sa.Column("submission_detail", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("provider_message_id", sa.String(length=80), nullable=True),
        sa.Column("provider_status", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("provider_status_code", sa.Integer(), nullable=True),
        sa.Column("cost", sa.String(length=30), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("delivery_status", sa.String(length=14), nullable=False, server_default="not_reported"),
        sa.Column("delivery_reported_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.String(length=200), nullable=False, server_default=""),
    )
    op.create_index("ix_sms_messages_broadcast_id", "sms_messages", ["broadcast_id"])
    op.create_index("ix_sms_messages_provider_message_id", "sms_messages", ["provider_message_id"])


def downgrade() -> None:
    op.drop_index("ix_sms_messages_provider_message_id", table_name="sms_messages")
    op.drop_index("ix_sms_messages_broadcast_id", table_name="sms_messages")
    op.drop_table("sms_messages")
    op.drop_index("ix_sms_broadcasts_content_hash", table_name="sms_broadcasts")
    op.drop_table("sms_broadcasts")
    op.drop_column("sms_subscribers", "opted_out_at")
    op.drop_column("sms_subscribers", "consent_note")
    op.drop_column("sms_subscribers", "consent_at")
