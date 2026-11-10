import json
import logging
from datetime import date, datetime
from typing import AsyncGenerator, List
from zoneinfo import ZoneInfo

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Path
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.eczane import Eczane
from app.schemas.eczane import EczaneResponse
from app.services.scraper import (
    TURKIYE_81_IL_SLUGS,
    sanitize_existing_database_records,
    scrape_and_save_all_eczaneler,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ==========================================
# REDIS ASENKRON BAĞLANTI HAVUZU & DEPENDENCY
# ==========================================
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI Dependency Injection için asenkron Redis istemcisi sağlar."""
    client = aioredis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.aclose()


def _get_today_tr() -> date:
    """Türkiye saat dilimine (Europe/Istanbul) göre bugünün tarihini döndürür."""
    return datetime.now(ZoneInfo("Europe/Istanbul")).date()


def _normalize_slug(text: str) -> str:
    """
    Şehir ve ilçe adlarını Redis cache anahtarı ve veritabanı sorgusu için
    standart küçük harf / ASCII-uyumlu formata dönüştürür.
    """
    tr_map = str.maketrans({
        "İ": "i", "I": "i", "ı": "i",
        "Ğ": "g", "ğ": "g",
        "Ü": "u", "ü": "u",
        "Ş": "s", "ş": "s",
        "Ö": "o", "ö": "o",
        "Ç": "c", "ç": "c",
    })
    return text.strip().translate(tr_map).lower()


def _normalize_ilce_key(ilce: str) -> str:
    """İlçe adını Türkçe küçük harf standardına dönüştürür."""
    tr_map = str.maketrans({"İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü", "Ş": "ş", "Ö": "ö", "Ç": "ç"})
    return ilce.strip().translate(tr_map).lower()


# ==========================================
# ENDPOINT 0: VERİTABANI İL BAZLI DOLULUK ÖZETİ (Dış Siteye İstek Atmaz)
# GET /api/v1/eczaneler/system/stats
# ==========================================
@router.get(
    "/system/stats",
    summary="Veritabanındaki 81 il doluluk ve koordinat istatistiklerini getir",
)
async def get_database_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    today = _get_today_tr()
    # Eğer gece 00:00 sonrası henüz yeni gün çekilmediyse en son aktif nöbet tarihini baz al
    latest_date_stmt = select(func.max(Eczane.nobet_tarihi))
    active_date = (await db.execute(latest_date_stmt)).scalar_one_or_none() or today

    stmt = (
        select(
            Eczane.sehir,
            func.count(Eczane.id).label("toplam"),
            func.count(Eczane.enlem).label("koordinatli"),
        )
        .where(Eczane.nobet_tarihi == active_date)
        .group_by(Eczane.sehir)
        .order_by(Eczane.sehir.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    cities_summary = [
        {
            "sehir": r.sehir,
            "toplam_eczane": r.toplam,
            "koordinatli_eczane": r.koordinatli,
            "oran_yuzde": round((r.koordinatli / r.toplam) * 100, 1) if r.toplam else 0.0,
        }
        for r in rows
    ]
    return {
        "sistem_tarihi": str(today),
        "aktif_nobet_tarihi": str(active_date),
        "kayitli_il_sayisi": len(cities_summary),
        "toplam_eczane": sum(c["toplam_eczane"] for c in cities_summary),
        "toplam_koordinatli": sum(c["koordinatli_eczane"] for c in cities_summary),
        "iller": cities_summary,
    }


@router.post(
    "/system/cleanup",
    summary="Veritabanındaki honeypot ve sahte kayıtları SQL ile temizle",
)
async def trigger_database_cleanup() -> dict:
    return await sanitize_existing_database_records()


# ==========================================
# ENDPOINT 1: ŞEHRE GÖRE NÖBETÇİ ECZANELER
# GET /api/v1/eczaneler/{sehir}
# ==========================================
@router.get(
    "/{sehir}",
    response_model=List[EczaneResponse],
    summary="Şehre göre tüm nöbetçi eczaneleri getir",
    description="Belirtilen şehirdeki bugüne ait tüm nöbetçi eczaneleri döndürür. Veritabanında henüz yoksa tek seferlik güvenli olarak çeker ve önbelleğe alır.",
)
async def get_eczaneler_by_sehir(
    sehir: str = Path(..., min_length=2, max_length=50, description="Şehir slug adı (Örn: ankara, istanbul)"),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> List[EczaneResponse]:
    today = _get_today_tr()
    normalized_sehir = _normalize_slug(sehir)
    cache_key = f"eczaneler:{normalized_sehir}:{today.isoformat()}:all"

    # 1. Önce Redis Cache'e bak (Cache-Aside Pattern)
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data is not None:
            logger.info(f"[CACHE HIT] '{normalized_sehir}' ili eczaneleri Redis'ten döndürüldü ({cache_key})")
            raw_list = json.loads(cached_data)
            return [EczaneResponse.model_validate(item) for item in raw_list]
    except Exception as exc:
        logger.warning(f"[Redis Uyarı] Önbellek okuma hatası, DB'ye yönlendiriliyor: {exc}")

    # 2. Cache'de yoksa (CACHE MISS) PostgreSQL'den çek
    logger.info(f"[CACHE MISS] '{normalized_sehir}' ili eczaneleri PostgreSQL'den çekiliyor (Tarih: {today})")
    stmt = (
        select(Eczane)
        .where(
            Eczane.nobet_tarihi == today,
            func.lower(Eczane.sehir) == normalized_sehir,
        )
        .order_by(Eczane.ilce.asc(), Eczane.isim.asc())
    )
    result = await db.execute(stmt)
    eczaneler = result.scalars().all()

    # 3. Eğer o il veritabanında bugün için HİÇ yoksa (ve geçerli 81 ilden biriyse)
    # Redis kilidi (Lock) ile sadece 1 kez çekip DB'ye kaydet (On-Demand Cold Start Hydration)
    if not eczaneler and normalized_sehir in TURKIYE_81_IL_SLUGS:
        lock_key = f"lock:scrape:{normalized_sehir}:{today.isoformat()}"
        has_lock = False
        try:
            has_lock = bool(await redis_client.set(lock_key, "1", ex=300, nx=True))
        except Exception:
            has_lock = True

        if has_lock:
            logger.info(f"[Cold Start] '{normalized_sehir}' DB'de bulunamadı, tek seferlik güvenli çekim yapılıyor...")
            await scrape_and_save_all_eczaneler(target_cities=[normalized_sehir], force=True)
            result = await db.execute(stmt)
            eczaneler = result.scalars().all()

    # 4. Gece 00:00 - Sabah 08:30 Vardiya Geçiş Koruması (veya Geçici Kaynak Engeli Fallback'i):
    # Türkiye'de nöbet vardiyası sabah 08:30'da devredilir. Eğer yeni günün verisi henüz çekilemediyse,
    # haritanın boş kalmaması için o ilin veritabanındaki en son nöbet listesini döndürür.
    if not eczaneler:
        latest_date_stmt = (
            select(func.max(Eczane.nobet_tarihi))
            .where(func.lower(Eczane.sehir) == normalized_sehir)
        )
        latest_date = (await db.execute(latest_date_stmt)).scalar_one_or_none()
        if latest_date is not None:
            logger.info(
                f"[Vardiya Fallback] '{normalized_sehir}' için {today} kaydı henüz yok, "
                f"aktif nöbet vardiyası ({latest_date}) döndürülüyor."
            )
            fallback_stmt = (
                select(Eczane)
                .where(
                    Eczane.nobet_tarihi == latest_date,
                    func.lower(Eczane.sehir) == normalized_sehir,
                )
                .order_by(Eczane.ilce.asc(), Eczane.isim.asc())
            )
            eczaneler = (await db.execute(fallback_stmt)).scalars().all()

    response_data = [EczaneResponse.model_validate(e) for e in eczaneler]

    # 4. Sonucu 6 saatliğine (21600 sn) Redis'e kaydet (Nöbet listeleri günde sadece 3 kez değiştiği için)
    if response_data:
        try:
            serialized = json.dumps(jsonable_encoder(response_data), ensure_ascii=False)
            await redis_client.set(cache_key, serialized, ex=21600)
        except Exception as exc:
            logger.warning(f"[Redis Uyarı] Önbellek yazma hatası: {exc}")

    return response_data


# ==========================================
# ENDPOINT 2: ŞEHİR VE İLÇEYE GÖRE NÖBETÇİ ECZANELER
# GET /api/v1/eczaneler/{sehir}/{ilce}
# ==========================================
@router.get(
    "/{sehir}/{ilce}",
    response_model=List[EczaneResponse],
    summary="Şehir ve ilçeye göre nöbetçi eczaneleri getir",
    description="Belirtilen şehir ve ilçedeki (Örn: ankara/sincan) bugüne ait nöbetçi eczaneleri döndürür.",
)
async def get_eczaneler_by_sehir_and_ilce(
    sehir: str = Path(..., min_length=2, max_length=50, description="Şehir slug adı (Örn: ankara)"),
    ilce: str = Path(..., min_length=2, max_length=100, description="İlçe adı (Örn: sincan, çankaya)"),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> List[EczaneResponse]:
    today = _get_today_tr()
    normalized_sehir = _normalize_slug(sehir)
    normalized_ilce = _normalize_ilce_key(ilce)
    cache_key = f"eczaneler:{normalized_sehir}:{today.isoformat()}:ilce:{normalized_ilce}"

    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data is not None:
            logger.info(
                f"[CACHE HIT] '{normalized_sehir}/{ilce}' eczaneleri Redis'ten döndürüldü ({cache_key})"
            )
            raw_list = json.loads(cached_data)
            return [EczaneResponse.model_validate(item) for item in raw_list]
    except Exception as exc:
        logger.warning(f"[Redis Uyarı] Önbellek okuma hatası, DB'ye yönlendiriliyor: {exc}")

    logger.info(
        f"[CACHE MISS] '{normalized_sehir}/{ilce}' eczaneleri PostgreSQL'den çekiliyor (Tarih: {today})"
    )
    stmt = (
        select(Eczane)
        .where(
            Eczane.nobet_tarihi == today,
            func.lower(Eczane.sehir) == normalized_sehir,
            func.lower(Eczane.ilce).contains(normalized_ilce),
        )
        .order_by(Eczane.isim.asc())
    )
    result = await db.execute(stmt)
    eczaneler = result.scalars().all()

    response_data = [EczaneResponse.model_validate(e) for e in eczaneler]

    if response_data:
        try:
            serialized = json.dumps(jsonable_encoder(response_data), ensure_ascii=False)
            await redis_client.set(cache_key, serialized, ex=21600)
        except Exception as exc:
            logger.warning(f"[Redis Uyarı] Önbellek yazma hatası: {exc}")

    return response_data


# ==========================================
# ENDPOINT 3: MANUEL SCRAPER TETİKLEYİCİ (TEK ŞEHİR VEYA TÜMÜ)
# POST /api/v1/eczaneler/scrape/{sehir}
# ==========================================
@router.post(
    "/scrape/{sehir}",
    summary="Belirli bir şehri (veya 'all' ile 81 ili) hemen tara",
)
async def trigger_city_scrape(sehir: str) -> dict:
    normalized = _normalize_slug(sehir)
    if normalized == "all":
        return await scrape_and_save_all_eczaneler(force=False)
    return await scrape_and_save_all_eczaneler(target_cities=[normalized], force=True)
