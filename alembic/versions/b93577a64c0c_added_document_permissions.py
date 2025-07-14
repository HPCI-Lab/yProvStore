"""Added document permissions

Revision ID: b93577a64c0c
Revises: 64531e081b4f
Create Date: 2025-07-13 19:44:18.911886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b93577a64c0c'
down_revision: Union[str, Sequence[str], None] = '64531e081b4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('document_permissions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('pid', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('permission_level', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['pid'], ['document_records.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_permissions_id'), 'document_permissions', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_document_permissions_id'), table_name='document_permissions')
    op.drop_table('document_permissions')
