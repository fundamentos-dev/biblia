"""rename embedding_2560 and drop old embedding

Revision ID: 9994a58b562c
Revises: b6623f9e1158
Create Date: 2025-12-30 17:21:46.706890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9994a58b562c'
down_revision: Union[str, None] = 'b6623f9e1158'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('ALTER TABLE versiculo DROP COLUMN embedding')
    op.execute('ALTER TABLE versiculo RENAME COLUMN embedding_2560 TO embedding_2560_qwen3_4b')


def downgrade() -> None:
    op.execute('ALTER TABLE versiculo RENAME COLUMN embedding_2560_qwen3_4b TO embedding_2560')
    op.execute('ALTER TABLE versiculo ADD COLUMN embedding vector(1024)')
