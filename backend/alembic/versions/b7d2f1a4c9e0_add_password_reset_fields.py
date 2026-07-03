"""add_password_reset_fields

Adds the password reset columns that exist on the User model
(app/models/user.py) but were never captured in a migration. Without
this, a fresh deployment that runs only `alembic upgrade head` produces
a `users` table lacking `password_reset_token` / `password_reset_sent_at`,
and the forgot-password / reset-password flows raise UndefinedColumn
(HTTP 500) on PostgreSQL.

This migration is intentionally IDEMPOTENT: some existing databases were
bootstrapped from the ORM models via `Base.metadata.create_all` and
already contain these columns while still being stamped at the previous
head (9b4f94021a3d). Adding the columns unconditionally would raise
DuplicateColumn on those databases, so we inspect the live schema first
and only create what is missing. This makes the migration safe on both
clean (Alembic-only) and create_all-bootstrapped databases.

Revision ID: b7d2f1a4c9e0
Revises: 9b4f94021a3d
Create Date: 2026-07-02 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2f1a4c9e0'
down_revision: Union[str, Sequence[str], None] = '9b4f94021a3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "users"
INDEX_NAME = "ix_users_password_reset_token"


def _existing_columns(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(TABLE)}


def _existing_indexes(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return {ix["name"] for ix in inspector.get_indexes(TABLE)}


def upgrade() -> None:
    """Upgrade schema (idempotent)."""
    bind = op.get_bind()
    columns = _existing_columns(bind)

    if "password_reset_token" not in columns:
        op.add_column(TABLE, sa.Column("password_reset_token", sa.String(length=512), nullable=True))
    if "password_reset_sent_at" not in columns:
        op.add_column(TABLE, sa.Column("password_reset_sent_at", sa.DateTime(timezone=True), nullable=True))

    if INDEX_NAME not in _existing_indexes(bind):
        op.create_index(op.f(INDEX_NAME), TABLE, ["password_reset_token"], unique=False)


def downgrade() -> None:
    """Downgrade schema (idempotent)."""
    bind = op.get_bind()

    if INDEX_NAME in _existing_indexes(bind):
        op.drop_index(op.f(INDEX_NAME), table_name=TABLE)

    columns = _existing_columns(bind)
    if "password_reset_sent_at" in columns:
        op.drop_column(TABLE, "password_reset_sent_at")
    if "password_reset_token" in columns:
        op.drop_column(TABLE, "password_reset_token")
