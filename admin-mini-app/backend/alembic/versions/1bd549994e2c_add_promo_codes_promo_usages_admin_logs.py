"""add promo_codes promo_usages admin_logs

Revision ID: 1bd549994e2c
Revises: 3c4eeb62ed1f
Create Date: 2026-03-05 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1bd549994e2c"
down_revision: str | Sequence[str] | None = "3c4eeb62ed1f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create promo_codes, promo_usages, and admin_logs tables."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    if "promo_codes" in existing_tables:
        # Table exists — check for missing columns and add them if needed.
        existing_columns = {
            col["name"]
            for col in inspector.get_columns("promo_codes")
        }
        if "valid_until" not in existing_columns:
            op.add_column(
                "promo_codes",
                sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
            )
            op.execute(
                "UPDATE promo_codes SET valid_until = now() WHERE valid_until IS NULL"
            )
            op.alter_column("promo_codes", "valid_until", nullable=False)
        # Skip creating tables that already exist.
        return

    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("max_activations", sa.Integer(), nullable=False),
        sa.Column(
            "current_activations",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "valid_until", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_promo_codes_code"), "promo_codes", ["code"], unique=True
    )

    op.create_table(
        "promo_usages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("promo_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["promo_id"], ["promo_codes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "admin_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("admin_username", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_logs_admin_telegram_id"),
        "admin_logs",
        ["admin_telegram_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_logs_action"),
        "admin_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_logs_created_at"),
        "admin_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop admin_logs, promo_usages, and promo_codes tables."""
    op.drop_index(
        op.f("ix_admin_logs_created_at"), table_name="admin_logs"
    )
    op.drop_index(
        op.f("ix_admin_logs_action"), table_name="admin_logs"
    )
    op.drop_index(
        op.f("ix_admin_logs_admin_telegram_id"), table_name="admin_logs"
    )
    op.drop_table("admin_logs")
    op.drop_table("promo_usages")
    op.drop_index(
        op.f("ix_promo_codes_code"), table_name="promo_codes"
    )
    op.drop_table("promo_codes")
