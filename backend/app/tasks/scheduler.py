import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.scraper import scrape_and_save_all_eczaneler

logger = logging.getLogger(__name__)

# Türkiye saat dilimine (Europe/Istanbul) duyarlı Singleton Zamanlayıcı
scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")

CRON_SCRAPER_JOB_ID = "shift_based_turkiye_eczane_scraper"
STARTUP_WARMUP_JOB_ID = "startup_all_81_cities_sync"


async def startup_all_cities_sync_job() -> None:
    """
    Uygulama başladığında (veya yeniden yüklendiğinde) 81 ilin tamamını kontrol eder.
    - Veritabanında bugüne ait güncel verisi olan illeri otomatik atlar (Skip).
    - Henüz çekilmemiş / eksik kalan illerin tamamını sırayla ve güvenli aralıklarla (Jitter) çeker.
    """
    logger.info("[Scheduler] Başlangıç senkronizasyonu: 81 ilin tamamı kontrol ediliyor ve eksikler tamamlanıyor...")
    await scrape_and_save_all_eczaneler(target_cities=None, force=False)


def start_scheduler() -> None:
    """
    Türkiye'deki resmi eczane nöbet vardiyası saatlerine göre yapılandırılmış zamanlayıcı:
    - Başlangıçta (Startup): 81 ilde eksik kalan tüm şehirleri otomatik tamamlar.
    - 00:05, 08:05, 18:05 -> Günde 3 kez tüm Türkiye (81 il) nöbetçi eczanelerini günceller.
    """
    if scheduler.running:
        logger.info("[Scheduler] Zamanlayıcı zaten çalışıyor.")
        return

    # 1. Vardiya Bazlı Cron Görevi (Günde 3 kez tüm 81 il: 00:05, 08:05, 18:05)
    scheduler.add_job(
        scrape_and_save_all_eczaneler,
        trigger=CronTrigger(hour="0,8,18", minute="5", timezone="Europe/Istanbul"),
        kwargs={"target_cities": None, "force": False},
        id=CRON_SCRAPER_JOB_ID,
        name="Vardiya Bazlı 81 İl Nöbetçi Eczane Güncelleyici",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    # 2. Başlangıçta (Startup) sadece 10 ili değil, 81 ilin tamamındaki eksikleri otomatik çek
    run_at = datetime.now(ZoneInfo("Europe/Istanbul")) + timedelta(seconds=3)
    scheduler.add_job(
        startup_all_cities_sync_job,
        trigger="date",
        run_date=run_at,
        id=STARTUP_WARMUP_JOB_ID,
        name="Başlangıç 81 İl Eksik Tamamlama Görevi",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info(
        "[Scheduler] 81 İl Otomatik Zamanlayıcısı başlatıldı "
        "(Başlangıç senkronizasyonu + 00:05, 08:05, 18:05 vardiyaları aktif)."
    )


def shutdown_scheduler() -> None:
    """Uygulama kapanırken zamanlayıcıyı güvenli bir şekilde durdurur."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Zamanlayıcı güvenli bir şekilde durduruldu.")
