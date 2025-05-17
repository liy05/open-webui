"""add_phone_number_field

Revision ID: ed4e89e9f9f3
Revises: 9f0c9cd09105
Create Date: 2025-05-16 15:58:33.729604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'ed4e89e9f9f3'
down_revision: Union[str, None] = '9f0c9cd09105'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加phone_number字段到user表（注意：这里使用user而不是users）
    op.add_column('user', sa.Column('phone_number', sa.String(20), nullable=True))
    
    # 为phone_number创建唯一索引
    op.create_index('ix_user_phone_number', 'user', ['phone_number'], unique=True)


def downgrade() -> None:
    # 移除索引
    op.drop_index('ix_user_phone_number', table_name='user')
    
    # 移除phone_number字段
    op.drop_column('user', 'phone_number')