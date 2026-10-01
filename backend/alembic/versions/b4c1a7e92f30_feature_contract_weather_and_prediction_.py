"""feature contract: real daily temperature extremes, 10 m wind, prediction target window

Phase 2 and Phase 20 of the evidence-based correction programme.

weather_observations gains the three columns the trained model actually requires:
  * temperature_max_c  (NASA POWER T2M_MAX)
  * temperature_min_c  (NASA POWER T2M_MIN)
  * wind_speed_10m_ms  (NASA POWER WS10M)

Before this migration the ingestion path stored neither temperature extreme and stored
2 m wind (WS2M) where the model expects 10 m wind. The inference path compensated by
passing the daily mean temperature three times, which flipped the alert decision on
49.8% of rows on the locked test split. The legacy `wind_speed_ms` column is kept, not
dropped, so historical rows are not retroactively reinterpreted as 10 m wind.

predictions gains the fields needed to verify a forecast after the fact:
  * observation_date        the date of the weather that produced the prediction
  * target_window_start/end the (t, t+7] window the prediction actually refers to
  * feature_contract_version which contract the inputs conformed to
  * is_stale                whether the prediction has been superseded

Revision ID: b4c1a7e92f30
Revises: 927a162df6ca
Create Date: 2026-09-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4c1a7e92f30"
down_revision: Union[str, Sequence[str], None] = "927a162df6ca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("weather_observations", sa.Column("temperature_max_c", sa.Float(), nullable=True))
    op.add_column("weather_observations", sa.Column("temperature_min_c", sa.Float(), nullable=True))
    op.add_column("weather_observations", sa.Column("wind_speed_10m_ms", sa.Float(), nullable=True))

    op.add_column("predictions", sa.Column("observation_date", sa.DateTime(), nullable=True))
    op.add_column("predictions", sa.Column("target_window_start", sa.DateTime(), nullable=True))
    op.add_column("predictions", sa.Column("target_window_end", sa.DateTime(), nullable=True))
    op.add_column(
        "predictions",
        sa.Column("feature_contract_version", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "predictions",
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_predictions_location_predicted_at",
        "predictions",
        ["location_id", "predicted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_predictions_location_predicted_at", table_name="predictions")
    for col in ("is_stale", "feature_contract_version", "target_window_end",
                "target_window_start", "observation_date"):
        op.drop_column("predictions", col)
    for col in ("wind_speed_10m_ms", "temperature_min_c", "temperature_max_c"):
        op.drop_column("weather_observations", col)
