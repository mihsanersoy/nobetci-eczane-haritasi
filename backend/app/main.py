import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import eczane as eczane_endpoints
from app.core.config import settings
from app.tasks.scheduler import shutdown_scheduler, start_scheduler

# Uygulama genelinde bilgi loglarının konsola basılması için temel yapılandırma
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan (Yaşam Döngüsü) Yöneticisi.
    Uygulama ayağa kalkarken (startup) ve kapanırken (shutdown) çalışacak
    bağlantı havuzlarını (DB, Redis) ve arka plan zamanlayıcısını (Hourly Scraper) yönetir.
    """
    # --- STARTUP (Başlangıç) ---
    logger.info(f"{settings.PROJECT_NAME} başlatılıyor...")
    start_scheduler()

    yield

    # --- SHUTDOWN (Kapanış) ---
    logger.info(f"{settings.PROJECT_NAME} kapatılıyor...")
    shutdown_scheduler()


def create_application() -> FastAPI:
    """
    FastAPI uygulama fabrikası (Application Factory Pattern).
    Test edilebilirliği ve modülerliği artırmak için uygulamayı bir fonksiyon içinde yapılandırır.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Türkiye Nöbetçi Eczaneler Harita Servisi - Önbellekli ve Arka Plan Beslemeli Backend API",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # CORS Middleware: Next.js (Frontend) uygulamasının API'mize güvenli erişimi için
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # API v1 Eczane Router Entegrasyonu (/api/v1/eczaneler)
    app.include_router(
        eczane_endpoints.router,
        prefix=f"{settings.API_V1_STR}/eczaneler",
        tags=["Eczaneler"],
    )

    return app


app = create_application()


@app.get("/health", tags=["Sistem"])
async def health_check():
    """
    Sistem sağlık kontrolü (Health Check) uç noktası.
    Docker, Load Balancer ve izleme araçlarının servisin ayakta olup olmadığını
    kontrol etmesi için kullanılır.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
