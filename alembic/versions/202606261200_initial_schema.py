"""initial schema: sentiment_scores table

Revision ID: initial_schema
Revises:
Create Date: 2026-06-26 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sentiment_scores",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("headline", sa.String(), nullable=True),
        sa.Column("compound", sa.Float(), nullable=True),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("scored_at", sa.DateTime(), nullable=True),
        sa.Column("raw_scores", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sentiment_scores_symbol"), "sentiment_scores", ["symbol"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sentiment_scores_symbol"), table_name="sentiment_scores")
    op.drop_table("sentiment_scores")
