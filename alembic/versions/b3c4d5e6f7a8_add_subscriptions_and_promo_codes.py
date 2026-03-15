"""add subscriptions and promo codes

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-02 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: str | Sequence[str] | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(name: str) -> bool:
    """Check if a table already exists in the database."""
    bind = op.get_bind()
    return inspect(bind).has_table(name)


def upgrade() -> None:
    """Create subscriptions and promo_codes tables."""
    if not _table_exists('subscriptions'):
        op.create_table(
            'subscriptions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('source', sa.String(length=20), nullable=False),
            sa.Column('promo_code', sa.String(length=64), nullable=True),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('now()'),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(
            'ix_subscriptions_user_expires',
            'subscriptions',
            ['user_id', 'expires_at'],
            unique=False,
        )

    if not _table_exists('promo_codes'):
        op.create_table(
            'promo_codes',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('code', sa.String(length=64), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('use_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('now()'),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code'),
        )


def downgrade() -> None:
    """Drop subscriptions and promo_codes tables."""
    op.drop_index('ix_subscriptions_user_expires', table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_table('promo_codes')
