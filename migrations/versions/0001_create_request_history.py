"""create request history table

Revision ID: 0001
Revises:
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "request_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("block_id", sa.String(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("processing_ms", sa.Float(), nullable=False),
        sa.Column("num_log_lines", sa.Integer(), nullable=True),
        sa.Column("num_events", sa.Integer(), nullable=True),
        sa.Column("num_windows", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("request_history")
