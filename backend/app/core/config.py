from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Uygulama konfigürasyon sınıfı.
    Pydantic BaseSettings kullanarak ortam değişkenlerini (.env) tip güvenli (type-safe)
    bir şekilde okur ve doğrular.
    """
    PROJECT_NAME: str = "Nöbetçi Eczane API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL
    POSTGRES_USER: str = "eczane_user"
    POSTGRES_PASSWORD: str = "eczane_secret_pass"
    POSTGRES_DB: str = "nobetci_eczane_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://eczane_user:eczane_secret_pass@localhost:5432/nobetci_eczane_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600  # 1 saat (3600 saniye)

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
