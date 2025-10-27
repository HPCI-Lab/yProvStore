"""Added document hash

Revision ID: ee9d828098ff
Revises: b93577a64c0c
Create Date: 2025-09-23 17:57:14.718202

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee9d828098ff'
down_revision: Union[str, Sequence[str], None] = 'b93577a64c0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('document_records', sa.Column('hash', sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('document_records', 'hash')
