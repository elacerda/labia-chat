"""chat_users_table

Revision ID: 20260527_chat_users
Revises: bf3b094e6dbb
Create Date: 2026-05-27 20:16:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260527_chat_users"
down_revision: str | None = "bf3b094e6dbb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Criar tabela chat_users
    op.create_table(
        "chat_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("adss_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "is_staff", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("adss_id", name="uq_chat_users_adss_id"),
    )

    # Criar índices
    op.create_index("ix_chat_users_username", "chat_users", ["username"])
    op.create_index("ix_chat_users_email", "chat_users", ["email"])


def downgrade() -> None:
    # Remover índices
    op.drop_index("ix_chat_users_email", table_name="chat_users")
    op.drop_index("ix_chat_users_username", table_name="chat_users")

    # Remover tabela
    op.drop_table("chat_users")