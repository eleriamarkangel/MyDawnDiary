"""Add expiring password reset challenges."""
from alembic import op
import sqlalchemy as sa

revision = "c91d70a325be"
down_revision = "b46c9d8a210f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reset_code_hash", sa.String(64), nullable=True))
    for name in ("reset_expires_at", "reset_sent_at", "reset_window_started_at"):
        op.add_column("users", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    for name in ("reset_attempts", "reset_sends_in_window"):
        op.add_column("users", sa.Column(name, sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    for name in ("reset_code_hash", "reset_expires_at", "reset_sent_at", "reset_window_started_at", "reset_attempts", "reset_sends_in_window"):
        op.drop_column("users", name)
