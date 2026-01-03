"""add embedding_2560 and clear embedding

Revision ID: b6623f9e1158
Revises: da3dd3967524
Create Date: 2025-12-30 17:14:35.698887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6623f9e1158'
down_revision: Union[str, None] = 'da3dd3967524'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('ALTER TABLE versiculo ADD COLUMN embedding_2560 vector(2560)')
    op.execute('UPDATE versiculo SET embedding = NULL')


def downgrade() -> None:
    op.execute('ALTER TABLE versiculo DROP COLUMN embedding_2560')
