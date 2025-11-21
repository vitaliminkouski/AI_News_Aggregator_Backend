"""Add article ingestion fields

Revision ID: 7b9e6c079f27
Revises: 64dbdcf44b91
Create Date: 2025-10-24 11:27:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b9e6c079f27"
down_revision: Union[str, Sequence[str], None] = "64dbdcf44b91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "Source",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "Source",
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "Articles",
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "Articles",
        sa.Column("url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "Articles",
        sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column(
        "Articles",
        sa.Column("sentiment_label", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "Articles",
        sa.Column("sentiment_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "Articles",
        sa.Column("entities", sa.JSON(), nullable=True),
    )

    op.create_index(
        "ix_Articles_content_hash", "Articles", ["content_hash"], unique=True
    )

    op.alter_column("Articles", "content", server_default=None)
    op.alter_column("Articles", "content_hash", server_default=None)


def downgrade() -> None:
    op.alter_column("Articles", "content", server_default="")
    op.alter_column("Articles", "content_hash", server_default="")
    op.drop_index("ix_Articles_content_hash", table_name="Articles")
    op.drop_column("Articles", "entities")
    op.drop_column("Articles", "sentiment_score")
    op.drop_column("Articles", "sentiment_label")
    op.drop_column("Articles", "content_hash")
    op.drop_column("Articles", "url")
    op.drop_column("Articles", "content")

    op.drop_column("Source", "last_fetched_at")
    op.drop_column("Source", "is_active")

