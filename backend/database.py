import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Preluăm URL-ul din variabilele de mediu sau fallback local
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://ark_admin:ark_secret_pass@localhost:5432/arkopticon_db"
)

# Engine asincron pentru PostgreSQL
engine = create_async_engine(DATABASE_URL, echo=True)

# Session factory pentru injectarea în endpoint-urile FastAPI
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    """Dependency pentru furnizarea unei sesiuni DB per request."""
    async with AsyncSessionLocal() as session:
        yield session