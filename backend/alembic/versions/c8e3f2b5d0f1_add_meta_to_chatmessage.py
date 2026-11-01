"""add_meta_to_chatmessage

Revision ID: c8e3f2b5d0f1
Revises: b7d2f1a4c9e0
Create Date: 2026-07-04 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c8e3f2b5d0f1'
down_revision = 'b7d2f1a4c9e0'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('chat_messages', sa.Column('meta', sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column('chat_messages', 'meta')
