"""Added document lineage id

Revision ID: 7e798efd23a3
Revises: ee9d828098ff
Create Date: 2025-10-01 15:08:16.264026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e798efd23a3'
down_revision: Union[str, Sequence[str], None] = 'ee9d828098ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('document_records', sa.Column('lineage_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('document_records', 'lineage_id')
