from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# 1. Asenkron Veritabanı Motoru (AsyncEngine)
# pool_pre_ping=True: Bağlantıyı havuzdan almadan önce hala canlı olup olmadığını kontrol eder.
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# 2. Asenkron Oturum Fabrikası (async_sessionmaker)
# expire_on_commit=False: Asenkron kullanımda commit sonrası nesne özelliklerine
# tekrar erişildiğinde oluşan "implicit I/O" (örtük sorgu) hatasını önler.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# 3. SQLAlchemy 2.0 Declarative Base Sınıfı
class Base(DeclarativeBase):
    """Tüm SQLAlchemy ORM modellerinin miras alacağı temel sınıf."""
    pass


# 4. FastAPI Dependency Injection (Bağımlılık Enjeksiyonu) Jeneratörü
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Her API isteği için bağımsız bir asenkron veritabanı oturumu (session) açar
    ve işlem bittiğinde (veya hata aldığında) güvenli bir şekilde kapatır.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
