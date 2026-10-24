"""Persist the account color theme."""
from alembic import op
import sqlalchemy as sa

revision = "b46c9d8a210f"
down_revision = "9a6bd5d8c07e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("theme", sa.String(20), server_default="orange-yellow", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "theme")
