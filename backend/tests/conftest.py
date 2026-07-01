from __future__ import annotations

from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.session as db_session
from app.api.deps import get_db, get_redis
from app.db.base import Base
from app.main import app
from app.models.checkpoint import GraphCheckpoint  # noqa: F401 — register with Base.metadata
from app.models.audit import AuditLog  # noqa: F401 — register with Base.metadata
from app.workers.celery_app import celery

# Configure Celery for synchronous task execution during testing
celery.conf.task_always_eager = True

# --------------------------------------------------------------------------- #
# Redis Mocking
# --------------------------------------------------------------------------- #
class MockRedis:
    """In-memory mock of Async Redis client for unit testing."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, *args, **kwargs) -> bool:
        self.data[key] = value
        return True

    async def setex(self, key: str, time: int, value: str) -> bool:
        self.data[key] = value
        self.ttls[key] = time
        return True

    async def delete(self, key: str) -> int:
        if key in self.data:
            del self.data[key]
            return 1
        return 0

    async def incr(self, key: str) -> int:
        self.data[key] = str(int(self.data.get(key, "0")) + 1)
        return int(self.data[key])

    async def expire(self, key: str, time: int) -> bool:
        self.ttls[key] = time
        return True

    def pipeline(self):
        return _MockPipeline(self)


class _MockPipeline:
    def __init__(self, redis: MockRedis) -> None:
        self._redis = redis
        self._commands: list[tuple] = []

    def incr(self, key: str):
        self._commands.append(("incr", key))
        return self

    def expire(self, key: str, time: int):
        self._commands.append(("expire", key, time))
        return self

    async def execute(self) -> list:
        results = []
        for cmd in self._commands:
            if cmd[0] == "incr":
                results.append(await self._redis.incr(cmd[1]))
            elif cmd[0] == "expire":
                results.append(await self._redis.expire(cmd[1], cmd[2]))
        return results


# --------------------------------------------------------------------------- #
# Database Setup
# --------------------------------------------------------------------------- #
# Use file-based SQLite to allow shared state across concurrent worker threads
TEST_DATABASE_URL = "sqlite+aiosqlite:///test_temp.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Monkey-patch backend session factory to use TestSessionLocal during testing
db_session.AsyncSessionLocal = TestSessionLocal


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Re-create schema on file DB for every test function to guarantee isolation."""
    import os
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Remove file after test completion
    await test_engine.dispose()
    if os.path.exists("test_temp.db"):
        try:
            os.remove("test_temp.db")
        except Exception:
            pass


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional session scoped to a single test case."""
    async with TestSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="function")
def mock_redis() -> MockRedis:
    return MockRedis()


# --------------------------------------------------------------------------- #
# FastAPI Test Client Setup
# --------------------------------------------------------------------------- #
@pytest_asyncio.fixture(scope="function")
async def client(
    db_session: AsyncSession, mock_redis: MockRedis
) -> AsyncGenerator[AsyncClient, None]:
    """Yield an HTTPX async client with overridden dependency providers."""
    # Override database dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Override redis dependency
    async def override_get_redis() -> MockRedis:
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    # Use ASGITransport for testing async routes directly
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver/api/v1"
    ) as client:
        yield client

    app.dependency_overrides.clear()
