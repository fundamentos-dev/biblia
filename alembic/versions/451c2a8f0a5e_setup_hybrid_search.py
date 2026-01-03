"""setup_hybrid_search

Revision ID: 451c2a8f0a5e
Revises: 9994a58b562c
Create Date: 2026-01-03 01:38:41.547615

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '451c2a8f0a5e'
down_revision: Union[str, None] = '9994a58b562c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) EXTENSIONS
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    # 2) REMOVE OLD EMBEDDING
    # Using execute for IF EXISTS safety
    op.execute("ALTER TABLE versiculo DROP COLUMN IF EXISTS embedding_2560_qwen3_4b")
    op.execute("DROP INDEX IF EXISTS idx_versiculo_embedding_2560_qwen3_4b")

    # 3) CREATE NEW EMBEDDING (SERAFIM 900M – 1536)
    op.add_column('versiculo', sa.Column('embedding_1536_serafim_900m', Vector(1536)))

    # Index HNSW
    op.create_index(
        'idx_versiculo_embedding_1536_serafim_900m_hnsw',
        'versiculo',
        ['embedding_1536_serafim_900m'],
        postgresql_using='hnsw',
        postgresql_ops={'embedding_1536_serafim_900m': 'vector_cosine_ops'}
    )

    # 4) CREATE COLUNA TSVECTOR
    op.add_column('versiculo', sa.Column('tsv', TSVECTOR))

    # POPULATE TSVECTOR
    op.execute("UPDATE versiculo SET tsv = to_tsvector('portuguese', unaccent(texto))")

    # Index GIN
    op.create_index(
        'idx_versiculo_tsv',
        'versiculo',
        ['tsv'],
        postgresql_using='gin'
    )

    # 5) TRIGGER
    op.execute("""
        CREATE OR REPLACE FUNCTION versiculo_tsv_trigger()
        RETURNS trigger AS $$
        BEGIN
          NEW.tsv := to_tsvector('portuguese', unaccent(NEW.texto));
          RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_versiculo_tsv ON versiculo")
    op.execute("""
        CREATE TRIGGER trg_versiculo_tsv
        BEFORE INSERT OR UPDATE OF texto
        ON versiculo
        FOR EACH ROW
        EXECUTE FUNCTION versiculo_tsv_trigger();
    """)

    # 6) AUXILIARY INDICES
    op.execute("CREATE INDEX IF NOT EXISTS idx_versiculo_versao ON versiculo (versao_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_versiculo_livro ON versiculo (livro_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_livro_abrev ON livro (abrev)")


def downgrade() -> None:
    # Reverse of upgrade
    op.execute("DROP INDEX IF EXISTS idx_livro_abrev")
    op.execute("DROP INDEX IF EXISTS idx_versiculo_livro")
    op.execute("DROP INDEX IF EXISTS idx_versiculo_versao")

    op.execute("DROP TRIGGER IF EXISTS trg_versiculo_tsv ON versiculo")
    op.execute("DROP FUNCTION IF EXISTS versiculo_tsv_trigger")

    op.drop_index('idx_versiculo_tsv', table_name='versiculo')
    op.drop_column('versiculo', 'tsv')

    op.drop_index('idx_versiculo_embedding_1536_serafim_900m_hnsw', table_name='versiculo')
    op.drop_column('versiculo', 'embedding_1536_serafim_900m')

    # Re-add old column schema
    op.add_column('versiculo', sa.Column('embedding_2560_qwen3_4b', Vector(2560)))
