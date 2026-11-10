import asyncio
import logging
import math
import random
import re
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx
import redis.asyncio as aioredis
from bs4 import BeautifulSoup, Tag
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    CurlAsyncSession = None
    HAS_CURL_CFFI = False

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.eczane import Eczane
from app.schemas.eczane import EczaneCreate

logger = logging.getLogger(__name__)

# Türkiye 81 İl URL Slug Listesi (Öncelikli büyükşehirler başta, ardından plaka sırası)
PRIORITY_CITIES: List[str] = [
    "ankara", "istanbul", "izmir", "antalya", "bursa", "adana", "konya", "gaziantep", "mersin", "kocaeli",
]

ALL_81_CITIES: List[str] = [
    "adana", "adiyaman", "afyonkarahisar", "agri", "amasya", "ankara", "antalya",
    "artvin", "aydin", "balikesir", "bilecik", "bingol", "bitlis", "bolu",
    "burdur", "bursa", "canakkale", "cankiri", "corum", "denizli", "diyarbakir",
    "edirne", "elazig", "erzincan", "erzurum", "eskisehir", "gaziantep", "giresun",
    "gumushane", "hakkari", "hatay", "isparta", "mersin", "istanbul", "izmir",
    "kars", "kastamonu", "kayseri", "kirklareli", "kirsehir", "kocaeli", "konya",
    "kutahya", "malatya", "manisa", "kahramanmaras", "mardin", "mugla", "mus",
    "nevsehir", "nigde", "ordu", "rize", "sakarya", "samsun", "siirt", "sinop",
    "sivas", "tekirdag", "tokat", "trabzon", "tunceli", "sanliurfa", "usak",
    "van", "yozgat", "zonguldak", "aksaray", "bayburt", "karaman", "kirikkale",
    "batman", "sirnak", "bartin", "ardahan", "igdir", "yalova", "karabuk",
    "kilis", "osmaniye", "duzce",
]

TURKIYE_81_IL_SLUGS: List[str] = PRIORITY_CITIES + [
    c for c in ALL_81_CITIES if c not in PRIORITY_CITIES
]

# Geocoding (Nominatim & ArcGIS) sorgularında "cankiri cant found" hatasını önlemek için
# URL slug -> Gerçek Türkçe Şehir Adı eşleştirme tablosu
SEHIR_TURKCE_ISIM_MAP: Dict[str, str] = {
    "adana": "Adana", "adiyaman": "Adıyaman", "afyonkarahisar": "Afyonkarahisar",
    "agri": "Ağrı", "amasya": "Amasya", "ankara": "Ankara", "antalya": "Antalya",
    "artvin": "Artvin", "aydin": "Aydın", "balikesir": "Balıkesir", "bilecik": "Bilecik",
    "bingol": "Bingöl", "bitlis": "Bitlis", "bolu": "Bolu", "burdur": "Burdur",
    "bursa": "Bursa", "canakkale": "Çanakkale", "cankiri": "Çankırı", "corum": "Çorum",
    "denizli": "Denizli", "diyarbakir": "Diyarbakır", "edirne": "Edirne", "elazig": "Elazığ",
    "erzincan": "Erzincan", "erzurum": "Erzurum", "eskisehir": "Eskişehir",
    "gaziantep": "Gaziantep", "giresun": "Giresun", "gumushane": "Gümüşhane",
    "hakkari": "Hakkari", "hatay": "Hatay", "isparta": "Isparta", "mersin": "Mersin",
    "istanbul": "İstanbul", "izmir": "İzmir", "kars": "Kars", "kastamonu": "Kastamonu",
    "kayseri": "Kayseri", "kirklareli": "Kırklareli", "kirsehir": "Kırşehir",
    "kocaeli": "Kocaeli", "konya": "Konya", "kutahya": "Kütahya", "malatya": "Malatya",
    "manisa": "Manisa", "kahramanmaras": "Kahramanmaraş", "mardin": "Mardin",
    "mugla": "Muğla", "mus": "Muş", "nevsehir": "Nevşehir", "nigde": "Niğde",
    "ordu": "Ordu", "rize": "Rize", "sakarya": "Sakarya", "samsun": "Samsun",
    "siirt": "Siirt", "sinop": "Sinop", "sivas": "Sivas", "tekirdag": "Tekirdağ",
    "tokat": "Tokat", "trabzon": "Trabzon", "tunceli": "Tunceli", "sanliurfa": "Şanlıurfa",
    "usak": "Uşak", "van": "Van", "yozgat": "Yozgat", "zonguldak": "Zonguldak",
    "aksaray": "Aksaray", "bayburt": "Bayburt", "karaman": "Karaman",
    "kirikkale": "Kırıkkale", "batman": "Batman", "sirnak": "Şırnak", "bartin": "Bartın",
    "ardahan": "Ardahan", "igdir": "Iğdır", "yalova": "Yalova", "karabuk": "Karabük",
    "kilis": "Kilis", "osmaniye": "Osmaniye", "duzce": "Düzce",
}

# Türkiye 81 İl Standart Merkez Koordinatları (Haversine Outlier Denetimi İçin)
SEHIR_MERKEZ_KOORDINATLARI: Dict[str, Tuple[float, float]] = {
    "adana": (37.0000, 35.3213), "adiyaman": (37.7648, 38.2786),
    "afyonkarahisar": (38.7507, 30.5567), "agri": (39.7191, 43.0503),
    "amasya": (40.6499, 35.8353), "ankara": (39.9208, 32.8541),
    "antalya": (36.8969, 30.7133), "artvin": (41.1828, 41.8183),
    "aydin": (37.8560, 27.8416), "balikesir": (39.6484, 27.8826),
    "bilecik": (40.1451, 29.9799), "bingol": (38.8854, 40.4980),
    "bitlis": (38.4006, 42.1095), "bolu": (40.7392, 31.6089),
    "burdur": (37.7203, 30.2908), "bursa": (40.1885, 29.0610),
    "canakkale": (40.1553, 26.4142), "cankiri": (40.6013, 33.6134),
    "corum": (40.5506, 34.9556), "denizli": (37.7765, 29.0864),
    "diyarbakir": (37.9144, 40.2306), "edirne": (41.6771, 26.5557),
    "elazig": (38.6810, 39.2264), "erzincan": (39.7500, 39.5000),
    "erzurum": (39.9000, 41.2700), "eskisehir": (39.7767, 30.5206),
    "gaziantep": (37.0662, 37.3833), "giresun": (40.9128, 38.3895),
    "gumushane": (40.4603, 39.4814), "hakkari": (37.5833, 43.7333),
    "hatay": (36.2021, 36.1600), "isparta": (37.7648, 30.5566),
    "mersin": (36.8000, 34.6333), "istanbul": (41.0082, 28.9784),
    "izmir": (38.4237, 27.1428), "kars": (40.6013, 43.0975),
    "kastamonu": (41.3887, 33.7827), "kayseri": (38.7312, 35.4787),
    "kirklareli": (41.7333, 27.2167), "kirsehir": (39.1425, 34.1709),
    "kocaeli": (40.7654, 29.9408), "konya": (37.8667, 32.4833),
    "kutahya": (39.4167, 29.9833), "malatya": (38.3552, 38.3095),
    "manisa": (38.6191, 27.4289), "kahramanmaras": (37.5858, 36.9371),
    "mardin": (37.3212, 40.7245), "mugla": (37.2153, 28.3636),
    "mus": (38.9462, 41.7539), "nevsehir": (38.6244, 34.7144),
    "nigde": (37.9667, 34.6833), "ordu": (40.9839, 37.8764),
    "rize": (41.0201, 40.5234), "sakarya": (40.7569, 30.3783),
    "samsun": (41.2867, 36.3300), "siirt": (37.9333, 41.9500),
    "sinop": (42.0231, 35.1531), "sivas": (39.7477, 37.0179),
    "tekirdag": (40.9833, 27.5167), "tokat": (40.3167, 36.5500),
    "trabzon": (41.0027, 39.7168), "tunceli": (39.1079, 39.5401),
    "sanliurfa": (37.1591, 38.7969), "usak": (38.6823, 29.4082),
    "van": (38.4891, 43.4089), "yozgat": (39.8181, 34.8147),
    "zonguldak": (41.4564, 31.7987), "aksaray": (38.3687, 34.0370),
    "bayburt": (40.2552, 40.2249), "karaman": (37.1759, 33.2287),
    "kirikkale": (39.8468, 33.5153), "batman": (37.8812, 41.1351),
    "sirnak": (37.5164, 42.4611), "bartin": (41.6344, 32.3375),
    "ardahan": (41.1105, 42.7022), "igdir": (39.9167, 44.0333),
    "yalova": (40.6500, 29.2667), "karabuk": (41.2000, 32.6333),
    "kilis": (36.7184, 37.1212), "osmaniye": (37.0742, 36.2478),
    "duzce": (40.8438, 31.1565),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    İki coğrafi koordinat (enlem/boylam) arasındaki kuş uçuşu mesafeyi
    Haversine formülü ile kilometre (km) cinsinden hesaplar.
    """
    r_earth = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    return 2.0 * r_earth * math.asin(math.sqrt(min(1.0, max(0.0, a))))


def _is_coordinate_valid_for_city(lat: float, lon: float, sehir: str, max_km: float = 160.0) -> bool:
    """
    Geocoding servisinden dönen koordinatın Türkiye sınırları içinde ve
    ilgili ilin sınırlarına (en uzak dış ilçeler dahil ~160 km) makul mesafede olduğunu doğrular.
    """
    if not (35.5 <= lat <= 42.5 and 25.5 <= lon <= 45.0):
        return False
    city_center = SEHIR_MERKEZ_KOORDINATLARI.get(sehir.strip().lower())
    if city_center is None:
        return True
    return haversine_km(lat, lon, city_center[0], city_center[1]) <= max_km

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
ARCGIS_GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"

BROWSER_IMPERSONATIONS: List[str] = ["chrome124", "chrome120", "chrome119", "safari17_0"]

NOMINATIM_HEADERS = {
    "User-Agent": "TurkiyeNobetciEczaneHaritasi/2.0 (https://github.com/nobetci-eczane; info@nobetcieczane.local)",
    "Accept": "application/json",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

COORD_REGEX = re.compile(r"(-?\d{1,2}\.\d{3,8})\s*,\s*(-?\d{1,3}\.\d{3,8})")
PHONE_REGEX = re.compile(
    r"(0?\s*\(?\d{3}\)?[\s\-\.]*\d{3}[\s\-\.]*\d{2}[\s\-\.]*\d{2}|\+90\s*\d{3}\s*\d{3}\s*\d{2}\s*\d{2}|\d{4}\s*\(\d{3}\)\s*\d{3}-\d{2}-\d{2})"
)

# Honeypot (Anti-Scraping Tuzak Metni) temizleme Regex'i
HONEYPOT_REGEX = re.compile(
    r"Bu\s+yazıyı\s+okuduğunuz\s+websitesi.*?Tüketici\s+Hakem\s+Heyetine\s+başvurunuz\.?\s*(?:→|»|«|-)*\s*",
    re.I | re.S,
)


def _strip_hidden_elements(scope: Tag) -> None:
    """
    HTML içerisindeki CSS ile gizlenmiş (display:none, visibility:hidden, font-size:0, d-none)
    honeypot/tuzak elementlerini DOM ağacından tamamen kaldırır.
    """
    for hidden in scope.select(
        '[style*="display:none"], [style*="display: none"], '
        '[style*="visibility:hidden"], [style*="visibility: hidden"], '
        '[style*="font-size:0"], [style*="font-size: 0"], '
        '[style*="opacity:0"], [style*="opacity: 0"], '
        '.d-none, .hidden, .sr-only, [hidden]'
    ):
        hidden.decompose()


def _sanitize_address(adres: str) -> str:
    """
    Adresteki honeypot tuzak cümlelerini, fazlalık ok işaretlerini ve şehir tekrarlarını temizler.
    """
    cleaned = HONEYPOT_REGEX.sub("", adres)
    cleaned = re.sub(r"[A-Za-zÇĞİÖŞÜçğıöşü]+\s*»\s*", "", cleaned)
    cleaned = re.sub(r"»[A-Za-zÇĞİÖŞÜçğıöşü0-9\s\.\:\'\(\)]+«", "", cleaned)
    cleaned = re.sub(r"(\/\s*)+[A-Za-zÇĞİÖŞÜçğıöşü]+(\s*→)?", " →", cleaned, flags=re.I)
    cleaned = _clean_text(cleaned).strip(" -–—,/|»«→:")
    return cleaned


def _get_browser_headers() -> Dict[str, str]:
    """Gerçek Chrome oturumuyla uyumlu Türkçe dil ve yönlendirme başlıkları."""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com.tr/",
        "Upgrade-Insecure-Requests": "1",
    }


def _extract_coordinates(container: Tag) -> Tuple[Optional[float], Optional[float]]:
    """Eczane HTML bloğu içindeki harita bağlantılarından (href) enlem ve boylam bilgisini ayrıştırır."""
    for link in container.find_all("a", href=True):
        href = link["href"]
        if any(keyword in href.lower() for keyword in ("maps", "harita", "konum", "q=", "ll=", "destination=")):
            match = COORD_REGEX.search(href)
            if match:
                try:
                    lat, lng = float(match.group(1)), float(match.group(2))
                    if 35.5 <= lat <= 42.5 and 25.5 <= lng <= 45.0:
                        return lat, lng
                except ValueError:
                    continue
    return None, None


def _clean_text(text: str) -> str:
    """Fazla boşlukları, yeni satırları ve sekme karakterlerini temizler."""
    return re.sub(r"\s+", " ", text).strip()


def _extract_core_street_components(adres: str) -> List[str]:
    """Adresten saf 'Mahalle', 'Bulvar', 'Cadde' ve 'Sokak' parçalarını cımbızla çeker."""
    text = re.sub(r"\([^)]*\)", " ", adres)
    text = re.sub(r"\bmah\.?\b", "Mahallesi", text, flags=re.I)
    text = re.sub(r"\bcad\.?\b|\bcd\.?\b", "Caddesi", text, flags=re.I)
    text = re.sub(r"\bsok\.?\b|\bsk\.?\b", "Sokak", text, flags=re.I)
    text = re.sub(r"\bblv\.?\b|\bbul\.?\b", "Bulvarı", text, flags=re.I)

    mahalle_match = re.search(r"([A-Za-zÇĞİÖŞÜçğıöşü0-9\s]{2,35}?Mahallesi)", text, re.I)
    cadde_match = re.search(
        r"([A-Za-zÇĞİÖŞÜçğıöşü0-9\.\s]{2,40}?(?:Caddesi|Bulvarı|Sokak|Sokağı))",
        text,
        re.I,
    )

    candidates: List[str] = []
    mahalle = _clean_text(mahalle_match.group(1)) if mahalle_match else ""
    cadde = _clean_text(cadde_match.group(1)) if cadde_match else ""

    if cadde and mahalle:
        candidates.append(f"{cadde}, {mahalle}")
    if cadde:
        candidates.append(cadde)
    if mahalle:
        candidates.append(mahalle)

    return candidates


async def fetch_coordinates_from_address(
    isim: str,
    sehir: str,
    ilce: str,
    adres: str,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Kaynak sitede harita koordinatı bulunmayan eczaneler için Geocoding çözümlemesi yapar.
    Şehir adını (`cankiri` -> `Çankırı`) gerçek Türkçe karakterli karşılığına çevirerek arar.
    """
    sehir_tr = SEHIR_TURKCE_ISIM_MAP.get(sehir.strip().lower(), sehir.capitalize())
    core_parts = _extract_core_street_components(adres)

    nominatim_queries: List[str] = []
    for part in core_parts:
        nominatim_queries.append(f"{part}, {ilce}, {sehir_tr}, Türkiye")
    nominatim_queries.append(f"{isim}, {ilce}, {sehir_tr}, Türkiye")

    async with httpx.AsyncClient(
        headers=NOMINATIM_HEADERS,
        timeout=httpx.Timeout(12.0, connect=5.0),
    ) as client:
        for query in nominatim_queries[:2]:
            await asyncio.sleep(1.5)
            params = {
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "tr",
                "addressdetails": 0,
            }
            try:
                response = await client.get(NOMINATIM_SEARCH_URL, params=params)
                response.raise_for_status()
                results = response.json()

                if isinstance(results, list) and len(results) > 0:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])
                    if _is_coordinate_valid_for_city(lat, lon, sehir):
                        logger.info(
                            f"[Nominatim Başarılı] '{isim}' ({sehir_tr}/{ilce}) -> ({lat:.5f}, {lon:.5f})"
                        )
                        return lat, lon
                    else:
                        logger.warning(
                            f"[Nominatim Reddedildi - Aykırı Mesafe] '{isim}' ({sehir_tr}/{ilce}) -> ({lat:.5f}, {lon:.5f})"
                        )
            except Exception as exc:
                logger.warning(f"[Nominatim Uyarı] '{isim}' ({query}): {exc}")

        # Bulanık Arama (Fuzzy Geocoding) Yedeği
        full_query = f"{isim}, {adres}, {ilce}, {sehir_tr}, Türkiye"
        try:
            arc_params = {
                "SingleLine": full_query,
                "f": "json",
                "maxLocations": 1,
                "countryCode": "TUR",
            }
            resp = await client.get(ARCGIS_GEOCODE_URL, params=arc_params)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and candidates[0].get("score", 0) >= 75:
                loc = candidates[0]["location"]
                lat, lon = float(loc["y"]), float(loc["x"])
                if _is_coordinate_valid_for_city(lat, lon, sehir):
                    logger.info(
                        f"[Fuzzy Geocoding Başarılı] '{isim}' ({sehir_tr}/{ilce}) -> ({lat:.5f}, {lon:.5f})"
                    )
                    return lat, lon
                else:
                    logger.warning(
                        f"[Fuzzy Geocoding Reddedildi - Aykırı Mesafe] '{isim}' ({sehir_tr}/{ilce}) -> ({lat:.5f}, {lon:.5f})"
                    )
        except Exception as exc:
            logger.warning(f"[Fuzzy Geocoding Uyarı] '{isim}': {exc}")

    return None, None


def parse_eczaneler_org_html(html_content: str, sehir: str, target_date: date) -> List[EczaneCreate]:
    """
    Yedek Türkiye Kaynağı (`eczaneler.org/{sehir}-nobetci-eczaneler/`) HTML ayrıştırıcısı.
    Sahte/şablon linkleri (boş adresli footer linklerini) sıkı doğrulama filtresiyle eler.
    """
    soup = BeautifulSoup(html_content, "lxml")
    _strip_hidden_elements(soup)
    parsed_list: List[EczaneCreate] = []
    sehir_normalized = sehir.strip().lower()

    title_links = soup.select('a[title*="Eczane"]')
    seen_names = set()

    for link_el in title_links:
        isim = _clean_text(link_el.get_text())
        if not isim or "eczane" not in isim.lower() or len(isim) > 100:
            continue
        # Genel şablon başlıklarını ("Nöbetçi Eczaneler", "En Yakın Eczane" vb.) ele
        if any(bad in isim.lower() for bad in ("nöbetçi", "nobetci", "yakın", "tüm", "liste", "harita")):
            continue
        if isim.lower() in seen_names:
            continue

        # Gerçek eczane kartı kapsayıcısını bul
        card = link_el.find_parent("div", class_=lambda c: c and ("rounded" in c or "border" in c))
        if card is None:
            continue

        # Doğrulama Filtresi 1: Kartın içinde gerçek bir <p> açık adres etiketi ZORUNLUDUR
        p_el = card.find("p")
        if p_el is None:
            continue
        adres = _sanitize_address(p_el.get_text(" "))
        if len(adres) < 10 or "belirtilmemiştir" in adres.lower():
            continue

        # Doğrulama Filtresi 2: "İl / İlçe" rozeti veya telefon bağlantısı bulunmalıdır
        ilce = "Merkez"
        has_valid_badge = False
        for span in card.find_all("span"):
            s_text = _clean_text(span.get_text())
            if "/" in s_text and len(s_text) < 50:
                parts = [p.strip() for p in s_text.split("/") if p.strip()]
                if len(parts) >= 2:
                    ilce = parts[-1]
                    has_valid_badge = True
                    break

        tel_link = card.find("a", href=re.compile(r"^tel:", re.I))
        telefon: Optional[str] = None
        if tel_link:
            telefon = _clean_text(tel_link.get_text()) or _clean_text(tel_link["href"].replace("tel:", ""))

        # Hem il/ilçe rozeti yok hem de telefonu yoksa bu bir footer/reklam linkidir -> Atla!
        if not has_valid_badge and not telefon:
            continue

        enlem, boylam = _extract_coordinates(card)

        seen_names.add(isim.lower())
        parsed_list.append(
            EczaneCreate(
                isim=isim[:255],
                sehir=sehir_normalized[:50],
                ilce=ilce[:100],
                adres=adres,
                telefon=telefon[:30] if telefon else None,
                enlem=enlem,
                boylam=boylam,
                nobet_tarihi=target_date,
            )
        )

    return parsed_list


def parse_eczaneler_html(html_content: str, sehir: str, target_date: date) -> List[EczaneCreate]:
    """
    Hem birincil (`eczaneler.gen.tr`) hem de ikincil (`eczaneler.org`) kaynağın HTML içeriğini
    otomatik tanıyıp EczaneCreate listesine dönüştürür.
    Gizli honeypot etiketlerini (`display:none` vb.) ayrıştırma öncesinde temizler.
    """
    soup = BeautifulSoup(html_content, "lxml")
    _strip_hidden_elements(soup)
    parsed_list: List[EczaneCreate] = []
    sehir_normalized = sehir.strip().lower()

    active_scope = (
        soup.find("div", id="nav-bugun")
        or soup.find("div", class_=lambda c: c and "tab-pane" in c and "active" in c)
        or soup
    )

    name_elements = active_scope.select("span.isim, div.isim, a.isim, strong.isim")

    if not name_elements:
        return parse_eczaneler_org_html(html_content, sehir=sehir, target_date=target_date)

    for name_el in name_elements:
        isim = _clean_text(name_el.get_text())
        if not isim:
            continue

        row_container = name_el.find_parent(["tr", "div.col-lg-12", "div.border-bottom"])
        if row_container is None:
            row_container = name_el.find_parent("div")
        if row_container is None:
            continue

        ilce = "Merkez"
        ilce_badge = row_container.select_one(
            "span.bg-info, span.badge-info, span.ilce, div.bg-info, span.bg-secondary"
        )
        if ilce_badge:
            ilce_raw = _clean_text(ilce_badge.get_text())
            if ilce_raw:
                ilce = ilce_raw
        else:
            alt_ilce = row_container.find("span", class_=lambda x: x and "bg-" in x)
            if alt_ilce:
                ilce = _clean_text(alt_ilce.get_text())

        telefon: Optional[str] = None
        tel_link = row_container.find("a", href=re.compile(r"^tel:", re.I))
        if tel_link:
            telefon = _clean_text(tel_link.get_text()) or _clean_text(tel_link["href"].replace("tel:", ""))
        else:
            row_text = row_container.get_text(" ", strip=True)
            phone_match = PHONE_REGEX.search(row_text)
            if phone_match:
                telefon = _clean_text(phone_match.group(0))

        enlem, boylam = _extract_coordinates(row_container)

        adres_el = row_container.select_one("div.col-lg-6, td:nth-of-type(2), div.adres")
        if adres_el:
            raw_text = _clean_text(adres_el.get_text(" "))
        else:
            raw_text = _clean_text(row_container.get_text(" "))

        adres = raw_text
        for token in filter(None, [isim, ilce, telefon]):
            adres = adres.replace(token, "").strip(" -–—,/|:")
        adres = _sanitize_address(adres)

        # Doğrulama Filtresi: Geçerli bir açık adres kalmadıysa sahte/bozuk kaydı atla
        if len(adres) < 5 or "belirtilmemiştir" in adres.lower():
            continue

        parsed_list.append(
            EczaneCreate(
                isim=isim[:255],
                sehir=sehir_normalized[:50],
                ilce=ilce[:100],
                adres=adres,
                telefon=telefon[:30] if telefon else None,
                enlem=enlem,
                boylam=boylam,
                nobet_tarihi=target_date,
            )
        )

    return parsed_list


async def _http_get_text(url: str, headers: Dict[str, str], impersonate_profile: str) -> Tuple[int, str]:
    """
    Konteynerde curl_cffi yüklüyse Chrome TLS Impersonation ile, henüz kurulmamışsa
    httpx.AsyncClient ile HTTP GET isteği yapar.
    """
    if HAS_CURL_CFFI and CurlAsyncSession is not None:
        async with CurlAsyncSession(timeout=18) as c_client:
            resp = await c_client.get(
                url,
                headers=headers,
                impersonate=impersonate_profile,
                allow_redirects=True,
            )
            return resp.status_code, resp.text
    else:
        httpx_headers = {
            **headers,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            ),
        }
        async with httpx.AsyncClient(timeout=18.0, follow_redirects=True) as h_client:
            resp = await h_client.get(url, headers=httpx_headers)
            return resp.status_code, resp.text


async def fetch_sehir_eczaneler_html(sehir: str) -> str:
    """
    Çift Kaynaklı (Dual-Source) Veri Çekici:
    1. Önce birincil kaynağı (`eczaneler.gen.tr/nobetci-{sehir}`) dener.
    2. Eğer birincil kaynak 403/429 (IP Ban) dönerse, hiçbir dakikada 5 istek sınırı olmayan
       ve doğrudan Türkiye'den 200 OK dönen ikincil resmi kaynağa (`eczaneler.org/{sehir}-nobetci-eczaneler/`) geçer!
    """
    primary_url = f"https://www.eczaneler.gen.tr/nobetci-{sehir}"
    secondary_url = f"https://www.eczaneler.org/{sehir}-nobetci-eczaneler/"
    headers = _get_browser_headers()
    impersonate_profile = random.choice(BROWSER_IMPERSONATIONS)

    # KAYNAK 1: eczaneler.gen.tr
    try:
        status_code, text = await _http_get_text(primary_url, headers, impersonate_profile)
        if status_code == 200 and "isim" in text:
            return text
    except Exception as primary_err:
        logger.debug(f"[Scraper] '{sehir}' birincil kaynak uyarısı: {primary_err}")

    # KAYNAK 2: eczaneler.org (Limitsiz, hızlı ve Cloudflare 403 engeli yok)
    try:
        status_code, text = await _http_get_text(secondary_url, headers, impersonate_profile)
        if status_code == 200 and "Eczane" in text:
            logger.info(f"[Scraper] '{sehir}' verisi ikincil kaynak (eczaneler.org) üzerinden başarıyla çekildi.")
            return text
    except Exception as sec_err:
        logger.warning(f"[Scraper] '{sehir}' ikincil kaynak hatası: {sec_err}")

    raise RuntimeError(f"'{sehir}' için her iki veri kaynağından da yanıt alınamadı.")


async def get_historical_coordinates(
    session: AsyncSession,
    isim: str,
    sehir: str,
    ilce: str,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Geçmiş Koordinat Hafızası (Historical Lookup / Data Hydration).
    """
    stmt = (
        select(Eczane.enlem, Eczane.boylam)
        .where(
            func.lower(Eczane.sehir) == sehir.strip().lower(),
            func.lower(Eczane.ilce) == ilce.strip().lower(),
            func.lower(Eczane.isim) == isim.strip().lower(),
            Eczane.enlem.is_not(None),
            Eczane.boylam.is_not(None),
        )
        .order_by(Eczane.nobet_tarihi.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is not None and row.enlem is not None and row.boylam is not None:
        logger.info(
            f"[Historical Cache Hit] '{isim}' ({sehir}/{ilce}) koordinatları geçmiş kayıtlardan alındı -> "
            f"({row.enlem:.5f}, {row.boylam:.5f})"
        )
        return float(row.enlem), float(row.boylam)

    return None, None


async def is_city_recently_scraped(session: AsyncSession, sehir: str, target_date: date, max_age_hours: int = 3) -> bool:
    """
    Belirtilen şehrin bugüne ait verisi veritabanında zaten varsa ve son `max_age_hours` (3 saat)
    içinde çekilmişse True döndürür. (Sabah 08:05 vardiyasının gece taramasıyla çakışmaması için 3 saate düşürüldü).
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    stmt = (
        select(func.count(Eczane.id))
        .where(
            Eczane.nobet_tarihi == target_date,
            Eczane.sehir == sehir.strip().lower(),
            Eczane.olusturulma_tarihi >= cutoff_time,
        )
    )
    result = await session.execute(stmt)
    count = result.scalar_one_or_none() or 0
    return count > 0


async def upsert_eczaneler(
    session: AsyncSession,
    eczaneler: List[EczaneCreate],
    sehir: str,
    target_date: date,
) -> Tuple[int, int]:
    """
    Belirli bir şehre ait çekilen nöbetçi eczaneleri veritabanına UPSERT mantığıyla kaydeder.
    """
    if not eczaneler:
        return 0, 0

    sehir_normalized = sehir.strip().lower()

    stmt = select(Eczane).where(
        Eczane.nobet_tarihi == target_date,
        Eczane.sehir == sehir_normalized,
    )
    result = await session.execute(stmt)
    existing_records = result.scalars().all()

    existing_map: Dict[Tuple[str, str, str], Eczane] = {
        (rec.isim.strip().lower(), rec.sehir.strip().lower(), rec.ilce.strip().lower()): rec
        for rec in existing_records
    }

    inserted_count = 0
    updated_count = 0
    processed_keys = set()

    for item in eczaneler:
        key = (item.isim.strip().lower(), item.sehir.strip().lower(), item.ilce.strip().lower())
        if key in processed_keys:
            continue
        processed_keys.add(key)

        if key in existing_map:
            db_obj = existing_map[key]
            db_obj.adres = item.adres
            db_obj.telefon = item.telefon

            if item.enlem is not None and item.boylam is not None:
                db_obj.enlem = item.enlem
                db_obj.boylam = item.boylam
            elif db_obj.enlem is None or db_obj.boylam is None:
                hist_lat, hist_lon = await get_historical_coordinates(
                    session=session,
                    isim=item.isim,
                    sehir=item.sehir,
                    ilce=item.ilce,
                )
                if hist_lat is not None and hist_lon is not None:
                    db_obj.enlem = hist_lat
                    db_obj.boylam = hist_lon
                else:
                    geo_lat, geo_lon = await fetch_coordinates_from_address(
                        isim=item.isim,
                        sehir=item.sehir,
                        ilce=item.ilce,
                        adres=item.adres,
                    )
                    if geo_lat is not None and geo_lon is not None:
                        db_obj.enlem = geo_lat
                        db_obj.boylam = geo_lon

            updated_count += 1
        else:
            enlem = item.enlem
            boylam = item.boylam

            if enlem is None or boylam is None:
                enlem, boylam = await get_historical_coordinates(
                    session=session,
                    isim=item.isim,
                    sehir=item.sehir,
                    ilce=item.ilce,
                )

                if enlem is None or boylam is None:
                    enlem, boylam = await fetch_coordinates_from_address(
                        isim=item.isim,
                        sehir=item.sehir,
                        ilce=item.ilce,
                        adres=item.adres,
                    )

            new_obj = Eczane(
                isim=item.isim,
                sehir=item.sehir,
                ilce=item.ilce,
                adres=item.adres,
                telefon=item.telefon,
                enlem=enlem,
                boylam=boylam,
                nobet_tarihi=item.nobet_tarihi,
            )
            session.add(new_obj)
            inserted_count += 1

    await session.commit()
    return inserted_count, updated_count


async def invalidate_sehir_cache(sehir: str, target_date: date) -> None:
    """Belirtilen şehrin o günkü Redis önbellek anahtarlarını temizler."""
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pattern = f"eczaneler:{sehir}:{target_date.isoformat()}:*"
        keys = [key async for key in client.scan_iter(match=pattern)]
        if keys:
            await client.delete(*keys)
        await client.aclose()
    except Exception as exc:
        logger.warning(f"[Scraper] Redis önbellek temizleme uyarısı ({sehir}): {exc}")


async def scrape_and_save_all_eczaneler(
    target_cities: Optional[List[str]] = None,
    force: bool = False,
) -> dict:
    """
    Çift Kaynaklı (eczaneler.gen.tr + eczaneler.org) Türkiye 81 İl Nöbetçi Eczane Kazıyıcısı.
    - Zaten çekilmiş illeri 0 saniyede (beklemeden) atlar.
    - Eksik illeri birincil kaynak 403 verse bile ikincil kaynak üzerinden kesintisiz tamamlar.
    """
    today_tr = datetime.now(ZoneInfo("Europe/Istanbul")).date()
    cities_to_scrape = target_cities or TURKIYE_81_IL_SLUGS

    logger.info(
        f"[Scraper] 81 İl Taraması başlatıldı "
        f"(Hedef İl Sayısı: {len(cities_to_scrape)}, Tarih: {today_tr}, Force: {force})"
    )

    total_scraped = 0
    total_inserted = 0
    total_updated = 0
    skipped_cities = 0
    failed_cities: List[str] = []

    for index, sehir in enumerate(cities_to_scrape):
        sehir_slug = sehir.strip().lower()

        # 1. Akıllı Atlama (Smart Skip): Veritabanında güncel kayıt varsa hiç beklemeden (0 sn) geç!
        if not force:
            async with AsyncSessionLocal() as check_session:
                if await is_city_recently_scraped(check_session, sehir_slug, today_tr):
                    skipped_cities += 1
                    logger.info(
                        f"[Scraper] ({index + 1}/{len(cities_to_scrape)}) '{sehir_slug}' zaten güncel, beklemeden atlanıyor."
                    )
                    continue

        try:
            html_content = await fetch_sehir_eczaneler_html(sehir_slug)
            scraped_items = parse_eczaneler_html(html_content, sehir=sehir_slug, target_date=today_tr)

            if scraped_items:
                async with AsyncSessionLocal() as session:
                    inserted, updated = await upsert_eczaneler(
                        session,
                        scraped_items,
                        sehir=sehir_slug,
                        target_date=today_tr,
                    )
                await invalidate_sehir_cache(sehir_slug, today_tr)
                total_scraped += len(scraped_items)
                total_inserted += inserted
                total_updated += updated
                logger.info(
                    f"[Scraper] ({index + 1}/{len(cities_to_scrape)}) '{sehir_slug}' tamamlandı -> "
                    f"Toplam: {len(scraped_items)} | Yeni: {inserted} | Güncel: {updated}"
                )
            else:
                logger.warning(f"[Scraper] '{sehir_slug}' için eczane kaydı bulunamadı.")

        except Exception as exc:
            failed_cities.append(sehir_slug)
            logger.error(f"[Scraper] '{sehir_slug}' ili taranırken hata oluştu: {exc}")

        # İller arası nazik bekleme (3.0 - 6.0 sn)
        if index < len(cities_to_scrape) - 1:
            jitter_delay = round(random.uniform(3.0, 6.0), 2)
            await asyncio.sleep(jitter_delay)

    logger.info(
        f"[Scraper] Tarama Bitti! Kazınan: {total_scraped} | Yeni: {total_inserted} | "
        f"Güncel: {total_updated} | Atlanan (Zaten Güncel): {skipped_cities} | Hatalı: {len(failed_cities)}"
    )
    return {
        "status": "success",
        "cities_processed": len(cities_to_scrape),
        "skipped_cities": skipped_cities,
        "total_scraped": total_scraped,
        "inserted": total_inserted,
        "updated": total_updated,
        "failed_cities": failed_cities,
        "date": str(today_tr),
    }


async def sanitize_existing_database_records() -> dict:
    """
    Mevcut veritabanındaki kirli verileri (Honeypot metinlerini ve sahte boş adresli kayıtları)
    doğrudan SQL sorgularıyla temizler ve Redis önbelleğini sıfırlar:
    1. İkincil kaynaktan sızan 126 adet sahte ('Adres bilgisi detayda belirtilmemiştir.') kaydı DELETE eder.
    2. Honeypot tuzak metnini ('Bu yazıyı okuduğunuz websitesi...') SQL regexp_replace ile tek sorguda temizler.
    3. Honeypot silindikten sonra geriye anlamlı adres kalmayan (<5 karakter) kayıtları DELETE eder.
    4. Redis önbelleğindeki tüm şehir/ilçe anahtarlarını temizler.
    """
    async with AsyncSessionLocal() as session:
        # 1. Sahte (boş adresli) kayıtları sil
        del_fake_stmt = delete(Eczane).where(
            Eczane.adres.ilike("%Adres bilgisi detayda belirtilmemiştir%")
        )
        res_fake = await session.execute(del_fake_stmt)
        deleted_fake_count = res_fake.rowcount or 0

        # 2. Honeypot tuzak metnini tek bir PostgreSQL regexp_replace sorgusuyla temizle
        sql_cleanup = text("""
            UPDATE eczaneler
            SET adres = btrim(
                regexp_replace(
                    adres,
                    'Bu\\s+yazıyı\\s+okuduğunuz\\s+websitesi.*?Tüketici\\s+Hakem\\s+Heyetine\\s+başvurunuz\\.?\\s*(?:→|»|«|-)*\\s*',
                    '',
                    'gi'
                ),
                ' -–—,/|»«→:'
            )
            WHERE adres ILIKE '%eczaneler.gen.tr%' OR adres ILIKE '%veri hırsızlığı%';
        """)
        res_update = await session.execute(sql_cleanup)
        cleaned_honeypot_count = res_update.rowcount or 0

        # 3. Honeypot temizliği sonrası adresi tamamen boşalan (< 5 karakter) satırlar varsa sil
        del_empty_stmt = delete(Eczane).where(func.length(func.btrim(Eczane.adres)) < 5)
        res_empty = await session.execute(del_empty_stmt)
        deleted_empty_count = res_empty.rowcount or 0

        await session.commit()

    # 4. Tüm Redis önbelleğini temizle ki temizlenen adresler anında API'den dönsün
    flushed_keys = 0
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        keys = [k async for k in client.scan_iter(match="eczaneler:*")]
        if keys:
            await client.delete(*keys)
            flushed_keys = len(keys)
        await client.aclose()
    except Exception as exc:
        logger.warning(f"[Cleanup] Redis temizleme uyarısı: {exc}")

    logger.info(
        f"[SQL Cleanup Tamamlandı] Honeypot Temizlenen: {cleaned_honeypot_count} | "
        f"Silinen Sahte Kayıt: {deleted_fake_count} | Silinen Boş Adres: {deleted_empty_count} | "
        f"Temizlenen Redis Anahtarı: {flushed_keys}"
    )
    return {
        "status": "success",
        "cleaned_honeypot_records": cleaned_honeypot_count,
        "deleted_fake_records": deleted_fake_count,
        "deleted_empty_after_cleanup": deleted_empty_count,
        "flushed_redis_keys": flushed_keys,
    }


async def scan_coordinate_outliers(
    threshold_km: float = 50.0,
    fix_outliers: bool = False,
) -> dict:
    """
    Haversine Formülü ile Pin Doğruluğu ve Aykırı Değer (Outlier) Tarayıcısı.
    - Veritabanındaki her eczanenin (enlem, boylam) koordinatını:
      1. Kayıtlı olduğu ilin standart merkez koordinatıyla (SEHIR_MERKEZ_KOORDINATLARI)
      2. Aynı ilçedeki diğer eczanelerin medyan (ilçe merkezi) koordinatıyla
      3. Türkiye'deki 81 il merkezi arasından fiziksel olarak en yakın olduğu il ile
      karşılaştırır.
    - `fix_outliers=True` verilirse, kendi ilçe/il merkezinden sapmış (başka şehre düşmüş)
      hatalı pinlerin koordinatlarını sıfırlar veya yeniden geocode eder.
    """
    async with AsyncSessionLocal() as session:
        latest_date_stmt = select(func.max(Eczane.nobet_tarihi))
        active_date = (await session.execute(latest_date_stmt)).scalar_one_or_none()

        stmt = select(Eczane).where(
            Eczane.nobet_tarihi == active_date,
            Eczane.enlem.is_not(None),
            Eczane.boylam.is_not(None),
        )
        rows = (await session.execute(stmt)).scalars().all()

        # 1. İlçe bazlı medyan (küme merkezi) koordinatlarını tüm geçmiş+güncel veriden hesapla
        all_coords_stmt = select(Eczane.sehir, Eczane.ilce, Eczane.enlem, Eczane.boylam).where(
            Eczane.enlem.is_not(None),
            Eczane.boylam.is_not(None),
        )
        all_coord_rows = (await session.execute(all_coords_stmt)).all()

        district_groups: Dict[Tuple[str, str], List[Tuple[float, float]]] = {}
        for cr in all_coord_rows:
            key = (cr.sehir.strip().lower(), cr.ilce.strip().lower())
            district_groups.setdefault(key, []).append((float(cr.enlem), float(cr.boylam)))

        district_Reference: Dict[Tuple[str, str], Tuple[float, float]] = {}
        district_counts: Dict[Tuple[str, str], int] = {}
        for key, coords in district_groups.items():
            district_counts[key] = len(coords)
            if len(coords) >= 2:
                lats = sorted(c[0] for c in coords)
                lons = sorted(c[1] for c in coords)
                mid = len(coords) // 2
                district_Reference[key] = (lats[mid], lons[mid])
            else:
                sehir_center = SEHIR_MERKEZ_KOORDINATLARI.get(key[0], (39.9208, 32.8541))
                district_Reference[key] = sehir_center

        critical_outliers: List[dict] = []
        outer_district_pins: List[dict] = []
        fixed_count = 0

        for r in rows:
            sehir_slug = r.sehir.strip().lower()
            ilce_norm = r.ilce.strip().lower()
            ilce_key = (sehir_slug, ilce_norm)
            lat, lon = float(r.enlem), float(r.boylam)

            city_center = SEHIR_MERKEZ_KOORDINATLARI.get(sehir_slug, (39.9208, 32.8541))
            dist_to_city_km = round(haversine_km(lat, lon, city_center[0], city_center[1]), 2)

            if ilce_norm == "merkez":
                ilce_center = city_center
                has_district_cluster = True
                dist_to_ilce_km = dist_to_city_km
            else:
                ilce_center = district_Reference.get(ilce_key, city_center)
                has_district_cluster = district_counts.get(ilce_key, 0) >= 2
                dist_to_ilce_km = (
                    round(haversine_km(lat, lon, ilce_center[0], ilce_center[1]), 2)
                    if has_district_cluster
                    else dist_to_city_km
                )

            # En yakın il merkezini bul
            closest_city_slug = sehir_slug
            closest_city_km = dist_to_city_km
            for cand_slug, (c_lat, c_lon) in SEHIR_MERKEZ_KOORDINATLARI.items():
                d = haversine_km(lat, lon, c_lat, c_lon)
                if d < closest_city_km:
                    closest_city_km = round(d, 2)
                    closest_city_slug = cand_slug

            if dist_to_city_km > threshold_km or (has_district_cluster and dist_to_ilce_km > 40.0):
                item_info = {
                    "id": str(r.id),
                    "sehir": sehir_slug,
                    "ilce": r.ilce,
                    "isim": r.isim,
                    "adres": r.adres,
                    "enlem": lat,
                    "boylam": lon,
                    "il_merkezine_mesafe_km": dist_to_city_km,
                    "ilce_merkezine_mesafe_km": dist_to_ilce_km,
                    "fiziksel_en_yakin_il": closest_city_slug,
                    "en_yakin_ile_mesafe_km": round(closest_city_km, 2),
                }

                # Kesin Hatalı Pin (Outlier) Kriterleri:
                # 1) Türkiye'de hiçbir ilçe kendi il merkezine 185 km'den uzak değildir (Örn: Şırnak -> İstanbul 1206 km)
                # 2) 'Merkez' ilçede kayıtlı olup il merkezinden > 45 km uzakta olanlar
                # 3) Aynı ilçedeki diğer eczanelerin küme merkezinden > 40 km sapanlar
                # 4) İlçe kümesi olmayan tekil kayıtlarda başka bir ilin tam merkezine (< 25 km) düşüp kendi ilinden > 85 km uzakta olanlar
                is_wrong_pin = (
                    dist_to_city_km > 185.0
                    or (ilce_norm == "merkez" and dist_to_city_km > 45.0)
                    or (has_district_cluster and dist_to_ilce_km > 40.0)
                    or (
                        not has_district_cluster
                        and closest_city_slug != sehir_slug
                        and closest_city_km < 25.0
                        and dist_to_city_km > 85.0
                    )
                )

                if is_wrong_pin:
                    item_info["anomali_tipi"] = "HATALI_PIN_BASKA_SEHIR_VEYA_SAPMA"
                    critical_outliers.append(item_info)
                    if fix_outliers:
                        r.enlem = None
                        r.boylam = None
                        fixed_count += 1
                else:
                    item_info["anomali_tipi"] = "UZAK_DIS_ILCE_NORMAL"
                    outer_district_pins.append(item_info)

        if fix_outliers and fixed_count > 0:
            await session.commit()
            try:
                client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                keys = [k async for k in client.scan_iter(match="eczaneler:*")]
                if keys:
                    await client.delete(*keys)
                await client.aclose()
            except Exception:
                pass

    critical_outliers.sort(key=lambda x: x["il_merkezine_mesafe_km"], reverse=True)
    outer_district_pins.sort(key=lambda x: x["il_merkezine_mesafe_km"], reverse=True)

    return {
        "aktif_nobet_tarihi": str(active_date),
        "incelenen_koordinatli_eczane": len(rows),
        "esik_mesafe_km": threshold_km,
        "kesin_hatali_pin_sayisi": len(critical_outliers),
        "uzak_dis_ilce_eczane_sayisi": len(outer_district_pins),
        "duzeltilen_kayit_sayisi": fixed_count,
        "kesin_hatali_pinler": critical_outliers,
        "uzak_dis_ilce_eczaneleri": outer_district_pins[:30],
    }


scrape_and_save_ankara_eczaneler = scrape_and_save_all_eczaneler
