"""Add expires_at column to memories

Revision ID: 0002_add_expires_at_to_memories
Revises: 0001_add_tier_and_constraints
Create Date: 2025-09-25 22:50:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_expires_at_to_memories"
down_revision = "0001_add_tier_and_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable expires_at column to memories table
    with op.batch_alter_table("memories") as batch_op:
        batch_op.add_column(
            sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("memories") as batch_op:
        batch_op.drop_column("expires_at")
