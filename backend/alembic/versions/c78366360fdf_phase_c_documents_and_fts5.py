"""phase c documents and fts5

Revision ID: c78366360fdf
Revises: 255f02549581
Create Date: 2026-05-06 00:47:41.113122

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c78366360fdf"
down_revision: str | Sequence[str] | None = "255f02549581"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "listing_document",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listing.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_listing_document_listing_id",
        "listing_document",
        ["listing_id"],
        unique=False,
    )

    # FTS5 virtual table — Alembic autogen doesn't handle these, so we emit raw SQL.
    # `tokenize='porter unicode61'` gives stem-aware matching across Unicode text;
    # `UNINDEXED` columns are stored but not searched, just retrievable.
    op.execute(
        """
        CREATE VIRTUAL TABLE listing_document_chunk_fts USING fts5(
            document_id UNINDEXED,
            listing_id UNINDEXED,
            chunk_index UNINDEXED,
            page_hint UNINDEXED,
            content,
            tokenize='porter unicode61'
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS listing_document_chunk_fts")
    op.drop_index("ix_listing_document_listing_id", table_name="listing_document")
    op.drop_table("listing_document")
