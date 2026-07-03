"""Migration-path integrity tests.

These tests exercise the REAL production schema path — `alembic upgrade
head` against PostgreSQL — which the default SQLite unit suite bypasses
(conftest builds the schema with `Base.metadata.create_all`). That bypass
is exactly why model<->migration drift (e.g. the password_reset columns)
could ship undetected.

They are opt-in: set RUN_MIGRATION_TESTS=1 and provide a reachable
PostgreSQL via the standard POSTGRES_* settings. CI runs them in a job
with a Postgres service container. Locally they skip by default so the
fast unit suite is unaffected.
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MIGRATION_TESTS") != "1",
    reason="Set RUN_MIGRATION_TESTS=1 (with a reachable PostgreSQL) to run migration-path tests.",
)


def _upgrade_to_head() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def test_alembic_upgrade_head_produces_full_model_parity() -> None:
    """Running migrations from scratch must yield a schema matching the ORM models.

    This is the guard that would have caught the password_reset drift: it fails
    if any model column is absent from the migrated database.
    """
    import sqlalchemy as sa

    from app.core.config import settings
    from app.db.base import Base
    import app.models  # noqa: F401 — register all tables on Base.metadata

    _upgrade_to_head()

    engine = sa.create_engine(settings.sync_database_url)
    inspector = sa.inspect(engine)
    db_tables = set(inspector.get_table_names())

    missing: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in db_tables:
            missing.append(f"{table.name} (entire table)")
            continue
        db_columns = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name not in db_columns:
                missing.append(f"{table.name}.{column.name}")

    assert not missing, (
        "Model columns missing from the migrated schema (migration drift): "
        + ", ".join(sorted(missing))
    )


def test_password_reset_columns_exist_after_migration() -> None:
    """Explicit regression guard for the specific drift found in the audit."""
    import sqlalchemy as sa

    from app.core.config import settings

    _upgrade_to_head()

    engine = sa.create_engine(settings.sync_database_url)
    columns = {col["name"] for col in sa.inspect(engine).get_columns("users")}
    assert "password_reset_token" in columns
    assert "password_reset_sent_at" in columns
