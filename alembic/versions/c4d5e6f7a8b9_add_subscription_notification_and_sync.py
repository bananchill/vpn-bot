"""add subscription notification and sync fields

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-03-02 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: str | Sequence[str] | None = 'b3c4d5e6f7a8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add notification and sync-pending flags to subscriptions."""
    op.add_column(
        'subscriptions',
        sa.Column(
            'notified_3d',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'subscriptions',
        sa.Column(
            'notified_expired',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'subscriptions',
        sa.Column(
            'configs_sync_pending',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    """Remove notification and sync-pending flags from subscriptions."""
    op.drop_column('subscriptions', 'configs_sync_pending')
    op.drop_column('subscriptions', 'notified_expired')
    op.drop_column('subscriptions', 'notified_3d')
