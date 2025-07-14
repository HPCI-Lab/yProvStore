"""Added provenance document records

Revision ID: 64531e081b4f
Revises: 62e22748bee9
Create Date: 2025-07-12 23:17:34.575115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64531e081b4f'
down_revision: Union[str, Sequence[str], None] = '62e22748bee9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('document_records',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('version', sa.String(), nullable=False),
    sa.Column('storage_id', sa.String(), nullable=False),
    sa.Column('owner_id', sa.String(), nullable=False),
    sa.Column('parent_doc_pid', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_records_id'), 'document_records', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_document_records_id'), table_name='document_records')
    op.drop_table('document_records')
