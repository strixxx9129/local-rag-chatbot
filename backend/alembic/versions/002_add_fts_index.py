# backend/alembic/versions/002_add_fts_index.py
"""add full text search index to document_chunks

Revision ID: 002
Revises: 11f5b9ed2781
Create Date: 2024-01-01
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "11f5b9ed2781"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add a generated tsvector column for English full-text search.
    # STORED means PostgreSQL computes and persists it automatically
    # whenever the content column is updated — zero application code needed.
    op.execute("""
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
    """)

    # GIN index — the right index type for tsvector columns.
    # GIN handles the multi-key nature of tsvector efficiently.
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_content_tsv
        ON document_chunks
        USING GIN (content_tsv);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_tsv;")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS content_tsv;")