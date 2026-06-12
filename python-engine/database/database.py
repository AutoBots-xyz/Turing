"""
database/database.py — Async Database Engine & Session Factory

Fixes Error 8 (Batch 4): This file was completely empty.
Configures an async SQLAlchemy engine backed by SQLite for local development
and exposes a session dependency for use in FastAPI routes.
"""
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Import Base and all models so create_all() can discover every table
from database.models import Base  # noqa: F401 — side effect: registers RunModel


# ---------------------------------------------------------------------------
# Engine — defaults to async SQLite, overridable via DATABASE_URL env var
# ---------------------------------------------------------------------------
_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./causal_nexus.db")

_connect_args = {"check_same_thread": False} if "sqlite" in _DATABASE_URL else {}

engine = create_async_engine(
    _DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# DB Initialisation — called on application startup (via lifespan in main.py)
# ---------------------------------------------------------------------------
async def init_db():
    """Creates all tables that do not yet exist. Safe to call on every startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a session per HTTP request
# ---------------------------------------------------------------------------
async def get_db() -> AsyncSession:
    """
    FastAPI dependency injection helper.

    Usage in a router:
        @router.post("/")
        async def create_run(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
