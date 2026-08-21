from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from src.core.config import settings

# Async engine and session maker
engine = create_async_engine(settings.DB_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync session maker using the engine's sync engine when synchronous sessions are required
SessionLocal = sessionmaker(bind=engine.sync_engine, autoflush=False, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session