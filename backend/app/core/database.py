"""
Database configuration and session management.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


from sqlalchemy import text

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Auto-migration for prompt_template
        try:
            # PostgreSQL specific check/add
            await conn.execute(text("ALTER TABLE category_definitions ADD COLUMN IF NOT EXISTS prompt_template TEXT;"))
            logger.info("Schema check: prompt_template column ensured.")
        except Exception as e:
            logger.warning(f"Schema migration skipped/failed: {e}")
            
    logger.info("Database initialized")


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_session() -> AsyncSession:
    """Get a new database session (non-generator version for background tasks)."""
    return async_session_maker()
