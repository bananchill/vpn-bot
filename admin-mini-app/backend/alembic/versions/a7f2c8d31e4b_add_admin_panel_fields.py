"""add admin panel fields

Revision ID: a7f2c8d31e4b
Revises: 1bd549994e2c
Create Date: 2026-03-07 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7f2c8d31e4b"
down_revision: str | Sequence[str] | None = "1bd549994e2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists in a table."""
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns(table)]
    return column in columns


def upgrade() -> None:
    """Add per-admin panel credentials and config-bot token fields to admins table."""
    new_columns = [
        ("username", sa.String(length=255)),
        ("panel_url", sa.String(length=512)),
        ("panel_username", sa.String(length=255)),
        ("panel_password_encrypted", sa.String(length=1024)),
        ("panel_sub_url", sa.String(length=512)),
        ("config_bot_token_encrypted", sa.String(length=1024)),
    ]
    for col_name, col_type in new_columns:
        if not _column_exists("admins", col_name):
            op.add_column("admins", sa.Column(col_name, col_type, nullable=True))


def downgrade() -> None:
    """Remove per-admin panel fields from admins table."""
    op.drop_column("admins", "config_bot_token_encrypted")
    op.drop_column("admins", "panel_sub_url")
    op.drop_column("admins", "panel_password_encrypted")
    op.drop_column("admins", "panel_username")
    op.drop_column("admins", "panel_url")
    op.drop_column("admins", "username")
