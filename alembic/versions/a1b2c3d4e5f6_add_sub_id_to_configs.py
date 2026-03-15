"""add sub_id to configs

Revision ID: a1b2c3d4e5f6
Revises: 38d89f8abb36
Create Date: 2026-03-01 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | Sequence[str] | None = '38d89f8abb36'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists in a table."""
    bind = op.get_bind()
    columns = [c['name'] for c in inspect(bind).get_columns(table)]
    return column in columns


def upgrade() -> None:
    """Add sub_id column to configs table.

    Existing rows get an empty string as default. New configs will always
    have a generated 16-char hex sub_id set by the application layer.
    """
    if not _column_exists('configs', 'sub_id'):
        op.add_column(
            'configs',
            sa.Column('sub_id', sa.String(length=16), server_default='', nullable=False),
        )


def downgrade() -> None:
    """Remove sub_id column from configs table."""
    op.drop_column('configs', 'sub_id')
