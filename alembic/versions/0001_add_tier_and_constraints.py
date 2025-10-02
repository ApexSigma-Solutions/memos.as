"""Add tier column and ensure constraints

Revision ID: 0001_add_tier_and_constraints
Revises: 
Create Date: 2025-09-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_add_tier_and_constraints"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Add 'tier' column to 'memories' if missing
    cols = [c["name"] for c in inspector.get_columns("memories")]
    if "tier" not in cols:
        op.add_column(
            "memories",
            sa.Column(
                "tier", sa.String(length=255), nullable=False, server_default="default"
            ),
        )

    # Registered tools: ensure 'name' unique constraint exists (if not, create)
    # Note: If duplicate names already exist this will fail; expect the application to handle duplicates.
    try:
        constraints = inspector.get_unique_constraints("registered_tools")
        has_name_unique = any("name" in c["column_names"] for c in constraints)
    except Exception:
        has_name_unique = False

    if not has_name_unique:
        # Create a unique constraint on name
        op.create_unique_constraint(
            "uq_registered_tools_name", "registered_tools", ["name"]
        )


def downgrade() -> None:
    # Downgrade: remove the unique constraint and drop the tier column if present
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    cols = [c["name"] for c in inspector.get_columns("memories")]
    if "tier" in cols:
        op.drop_column("memories", "tier")

    try:
        constraints = inspector.get_unique_constraints("registered_tools")
        for c in constraints:
            constraint_name = c.get("name")
            if constraint_name and "name" in c.get("column_names", []):
                op.drop_constraint(constraint_name, "registered_tools", type_="unique")
                break
    except Exception:
        pass
