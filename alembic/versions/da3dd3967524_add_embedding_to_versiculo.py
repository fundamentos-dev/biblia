"""add embedding to versiculo

Revision ID: da3dd3967524
Revises: 25bc0bd9b8f0
Create Date: 2025-12-30 03:38:50.936847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da3dd3967524'
down_revision: Union[str, None] = '25bc0bd9b8f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('ALTER TABLE versiculo ADD COLUMN embedding vector(1024)')


def downgrade() -> None:
    op.execute('ALTER TABLE versiculo DROP COLUMN embedding')
