"""Added artifacts and presigned URLs

Revision ID: 7e66b42e31ea
Revises: 7e798efd23a3
Create Date: 2025-12-11 15:41:00.278311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e66b42e31ea'
down_revision: Union[str, Sequence[str], None] = '7e798efd23a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('artifact_records',
    sa.Column('id', sa.String(length=255), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('storage_id', sa.String(length=255), nullable=False),
    sa.Column('owner_id', sa.String(length=255), nullable=False),
    sa.Column('hash', sa.String(length=64), nullable=True),
    sa.Column('valid', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_artifact_records_id'), 'artifact_records', ['id'], unique=False)
    op.create_table('presigned_urls',
    sa.Column('id', sa.String(length=255), nullable=False),
    sa.Column('user_id', sa.String(length=255), nullable=False),
    sa.Column('storage_id', sa.String(length=255), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('operation_type', sa.Enum('UPLOAD', 'DOWNLOAD', name='presignedurloperationtype'), nullable=False),
    sa.Column('expires_at', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_presigned_urls_id'), 'presigned_urls', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_presigned_urls_id'), table_name='presigned_urls')
    op.drop_table('presigned_urls')
    op.drop_index(op.f('ix_artifact_records_id'), table_name='artifact_records')
    op.drop_table('artifact_records')
