"""phase b decision journal

Revision ID: 255f02549581
Revises: 87fc5ed94d49
Create Date: 2026-05-06 00:39:56.761850

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "255f02549581"
down_revision: str | Sequence[str] | None = "87fc5ed94d49"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "decision_journal_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listing.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_journal_entry_listing_id",
        "decision_journal_entry",
        ["listing_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_decision_journal_entry_listing_id", table_name="decision_journal_entry")
    op.drop_table("decision_journal_entry")
