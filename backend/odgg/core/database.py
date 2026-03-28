"""SQLite session database setup with async support."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from odgg.core.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

    pass


# WAL mode for better concurrent read performance; single writer is fine for MVP
engine = create_async_engine(
    settings.session_db_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
    pool_size=1,
    max_overflow=0,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Yield an async database session."""
    async with async_session() as session:
        yield session
