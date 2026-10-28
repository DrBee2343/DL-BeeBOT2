from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

if settings.database_url.startswith("sqlite"):
    Path("/data").mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
else:
    engine = create_async_engine(
        settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=10
    )

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_models() -> None:
    from app import models

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


async def dispose() -> None:
    await engine.dispose()
