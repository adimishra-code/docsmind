"""add audit_logs and graph_checkpoints

Revision ID: 3e973ee3309e
Revises: a00000000001
Create Date: 2026-07-01 15:58:12.424505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e973ee3309e'
down_revision: Union[str, Sequence[str], None] = 'a00000000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('audit_logs',
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('detail', sa.String(length=500), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('extra', sa.JSON(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_table('graph_checkpoints',
    sa.Column('thread_id', sa.String(length=255), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('session_id', sa.Uuid(), nullable=True),
    sa.Column('node', sa.String(length=100), nullable=True),
    sa.Column('state_json', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_graph_checkpoints_session_id'), 'graph_checkpoints', ['session_id'], unique=False)
    op.create_index(op.f('ix_graph_checkpoints_thread_id'), 'graph_checkpoints', ['thread_id'], unique=False)
    op.create_index(op.f('ix_graph_checkpoints_user_id'), 'graph_checkpoints', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_graph_checkpoints_user_id'), table_name='graph_checkpoints')
    op.drop_index(op.f('ix_graph_checkpoints_thread_id'), table_name='graph_checkpoints')
    op.drop_index(op.f('ix_graph_checkpoints_session_id'), table_name='graph_checkpoints')
    op.drop_table('graph_checkpoints')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
