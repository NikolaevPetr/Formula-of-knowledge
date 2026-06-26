"""Async-движок SQLAlchemy и фабрика сессий."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


# SQLite требует особого флага для работы в нескольких корутинах.
_connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

# Для async SQLite используем NullPool: пул соединений плохо живёт с несколькими
# event loop-ами (например, в тестах) и даёт «event loop is closed». На
# PostgreSQL оставляем стандартный пул.
_engine_kwargs = {"poolclass": NullPool} if settings.is_sqlite else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=_connect_args,
    **_engine_kwargs,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-зависимость: выдаёт сессию на время запроса."""
    async with SessionLocal() as session:
        yield session
