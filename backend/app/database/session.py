"""
Async database session management for DBStudio's local SQLite store.

Provides:
  * A shared ``async_engine`` created once at import time from application config.
  * An ``async_sessionmaker`` used by the FastAPI dependency injector.
  * ``get_db``  — an async generator suitable for ``Depends()`` in route handlers.
  * ``init_db`` — a coroutine that creates all tables declared in ``models.py``.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database.models import Base

# ── Engine ─────────────────────────────────────────────────────────────────────
# SQLite over aiosqlite requires check_same_thread=False because the same
# connection may be used from different asyncio tasks.  For PostgreSQL / MySQL
# (used only by the remote-DB proxy layer, not this local store) the argument
# is harmless and simply ignored.

_CONNECT_ARGS: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _CONNECT_ARGS["check_same_thread"] = False

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=_CONNECT_ARGS,
    pool_pre_ping=True,
)

# ── Session factory ────────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── FastAPI dependency ─────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an ``AsyncSession`` and guarantee it is closed when the request ends.

    Usage in a route handler::

        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.database.session import get_db

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Table initialisation ───────────────────────────────────────────────────────

async def init_db() -> None:
    """
    Create every table declared in ``models.py`` that does not already exist.

    Safe to call repeatedly; ``create_all`` is idempotent.  Called once during
    application startup inside the lifespan context manager.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
