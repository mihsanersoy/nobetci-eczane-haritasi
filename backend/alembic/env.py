import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Uygulama konfigürasyonu ve Base sınıfı
from app.core.config import settings
from app.core.database import Base

# Autogenerate'in tabloları algılaması için modelleri import ediyoruz
import app.models.eczane  # noqa: F401

# Alembic Config nesnesi (alembic.ini dosyasına erişim sağlar)
config = context.config

# Veritabanı bağlantısını ortam değişkenlerinden (settings.DATABASE_URL) dinamik olarak ata
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Python loglama ayarlarını alembic.ini'den yükle
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate desteği için hedef metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    'Offline' modda migration çalıştırır.
    Gerçek bir veritabanı bağlantısı kurmadan sadece SQL çıktılarını üretmek için kullanılır.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Asenkron bağlantı içinden senkron Alembic migration bağlamını çalıştıran yardımcı fonksiyon.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Sütun tipi değişikliklerini de algıla
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Asenkron motor (AsyncEngine) oluşturur ve bağlantıyı senkron migration
    fonksiyonuna (`connection.run_sync`) devreder.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    'Online' modda asenkron event loop üzerinden migration çalıştırır.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
