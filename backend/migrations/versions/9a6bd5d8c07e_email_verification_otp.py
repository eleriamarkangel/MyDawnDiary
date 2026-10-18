"""email verification otp

Revision ID: 9a6bd5d8c07e
Revises: 33bbd8f9f146
"""

from alembic import op
import sqlalchemy as sa


revision = "9a6bd5d8c07e"
down_revision = "33bbd8f9f146"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_otp_hash", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("email_otp_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_otp_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_otp_attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("email_otp_window_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_otp_sends_in_window", sa.Integer(), server_default="0", nullable=False))
    # Existing accounts were created before email verification was offered.
    op.execute("UPDATE users SET email_verified_at = created_at")


def downgrade() -> None:
    op.drop_column("users", "email_otp_sends_in_window")
    op.drop_column("users", "email_otp_window_started_at")
    op.drop_column("users", "email_otp_attempts")
    op.drop_column("users", "email_otp_sent_at")
    op.drop_column("users", "email_otp_expires_at")
    op.drop_column("users", "email_otp_hash")
    op.drop_column("users", "email_verified_at")
