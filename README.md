<div align="center">

# 🏥 Türkiye 81 İl Canlı Nöbetçi Eczane Haritası

**81 İlin Nöbetçi Eczane Verilerini Otonom Toplayan, Coğrafi Anomali (Outlier) Tespiti Yapan, Kirli Veriyi Temizleyen ve HTML5 Geolocation ile Akıllı Yönlendirme Sunan Full-Stack Coğrafi Bilgi Sistemi**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## 📌 Proje Özeti

**Türkiye 81 İl Canlı Nöbetçi Eczane Haritası**, Türkiye genelindeki 81 il ve tüm ilçelerde o gün nöbetçi olan eczaneleri otonom zamanlayıcılarla toplayan, kaynak sitelerdeki anti-scraping tuzaklarını (*honeypot*) ve sahte kayıtları temizleyen, eksik harita koordinatlarını много-katmanlı (*multi-tier*) Geocoding hattıyla tamamlayan ve **Haversine formülü** ile hatalı pinleri otomatik denetleyen uçtan uca (*end-to-end*) bir mühendislik projesidir.

Kullanıcı arayüzünde **HTML5 Geolocation** (ve IP tabanlı yedekleme) ile kullanıcının bulunduğu ili otomatik tespit eder, **React-Leaflet** üzerinde interaktif 81 il haritası sunar ve Google Haritalar yönlendirmelerinde cadde-ortası sapmalarını (*coordinate snapping*) önleyen akıllı POI rotalama mimarisi kullanır.

---

## 🛠️ Teknoloji Yığını (Tech Stack)

| Katman | Teknolojiler ve Kütüphaneler | Mimari Rolü |
| :--- | :--- | :--- |
| **Backend & API** | `Python 3.11`, `FastAPI`, `Pydantic v2`, `Uvicorn` | Yüksek performanslı asenkron REST API ve veri doğrulama katmanı |
| **Veritabanı & ORM** | `PostgreSQL 16`, `SQLAlchemy 2.0 (Async)`, `asyncpg`, `Alembic` | İlişkisel veri saklama, bileşik indeksleme (`sehir + ilce + nobet_tarihi`) ve şema göçleri |
| **Önbellek & Kilit** | `Redis 7` (`redis.asyncio`) | `Cache-Aside` önbellekleme (6 saat TTL) ve `Distributed Lock` (`SET NX`) ile tekil kazıma |
| **Veri Kazıma & Ağ** | `BeautifulSoup4`, `lxml`, `HTTPX`, `curl_cffi`, `APScheduler` | Chrome TLS parmak izi taklidi (*Impersonation*), çift kaynaklı failover ve vardiya zamanlayıcısı |
| **Frontend & Harita** | `Next.js (App Router)`, `React 18`, `TypeScript`, `Tailwind CSS`, `React-Leaflet` | SSR uyumlu dinamik harita, BFF Reverse Proxy, Geolocation ve dinamik SEO yönetimi |
| **Altyapı & DevOps** | `Docker`, `Docker Compose` | Konteynerize mikro-servis orkestrasyonu ve sağlık kontrolleri (`healthcheck`) |

---

## 🧠 Öne Çıkan Mühendislik Çözümleri

### 1. 🛡️ Zırhlı Scraper & Anti-Honeypot Sanitizasyonu
Nöbetçi eczane veri kaynakları yoğun trafik ve bot korumaları (Cloudflare 403/429 ve gizli DOM tuzakları) barındırır. Sistemde kesintisiz veri akışı için **Çift Kaynaklı (Dual-Source) Failover Mimarisi** uygulanmıştır:
* **Birincil & İkincil Kaynak Yedekliliği:** İlk olarak birincil kaynak (`eczaneler.gen.tr`) `curl_cffi` Chrome TLS Impersonation ile sorgulanır. IP engeli (403) veya zaman aşımı durumunda sistem sıfır bekleme ile ikincil Türkiye kaynağına (`eczaneler.org`) otomatik geçiş yapar.
* **DOM Seviyesinde Anti-Honeypot Temizliği:** Kaynak sitelerin adres metinlerinin içine CSS ile gizleyerek (`display:none`, `visibility:hidden`, `font-size:0`, `.d-none`, `.sr-only`) yerleştirdiği sahte telif/uyarı tuzakları, ayrıştırma (*parsing*) öncesinde `_strip_hidden_elements()` fonksiyonu ile DOM ağacından tamamen sökülür (`decompose()`).
* **SQL Seviyesinde Veri Sanitizasyonu & Şablon Filtresi:** İkincil kaynaktan sızabilecek boş adresli şablon/footer linkleri çift aşamalı doğrulama (açık `<p>` adresi + geçerli ilçe rozeti veya `tel:` bağlantısı zorunluluğu) ile elenir; geçmiş verilerdeki olası kalıntılar ise PostgreSQL `regexp_replace` sorgusuyla tek hamlede temizlenir.

### 2. ⚡ Soğuk Başlangıç (Cold Start), Önbellek & Vardiya Geçiş Koruması
* **Redis Cache-Aside Pattern (6 Saatlik TTL):** Nöbet listeleri Türkiye'de sabit vardiyalarla değiştiği için, PostgreSQL sorguları `eczaneler:{sehir}:{tarih}:all` anahtarıyla Redis'te 6 saat boyunca önbelleklenir ve yanıt süresi `< 5 ms` seviyesine indirilir.
* **On-Demand Single-Flight Hydration (Distributed Lock):** Henüz taranmamış bir şehre ilk kez istek geldiğinde, Redis üzerinde `lock:scrape:{sehir}:{tarih}` (`SET NX EX 300`) kilidi alınarak aynı anda 100 kullanıcı tıklasa bile arka planda **yalnızca 1 kez** kazıma tetiklenir (*Cache Stampede* koruması).
* **Gece 00:00 – Sabah 08:30 Nöbet Vardiya Geçiş Koruması:** Türkiye'de eczane nöbet vardiyası gece 00:00'da değil, ertesi sabah **08:30**'da devredilir. Gece yarısından sonra takvim tarihi değiştiğinde yeni günün listesi henüz yayınlanmamışsa, sistem haritayı boş döndürmek yerine bir önceki günün aktif nöbet vardiyasını otomatik olarak sunar.
* **Vardiya Odaklı Zamanlayıcı (`max_age_hours=3`):** `APScheduler`, Türkiye'deki nöbet değişim saatlerine (`08:05`, `09:30` ve `19:05`) göre günde sadece 3 kez çalışır. Tazelik eşiği 3 saat olarak sınırlandırılarak gece taramalarının sabah `08:05` vardiyasıyla çakışması engellenmiştir.

### 3. 🎯 Outlier Detection (Haversine Formülü ile 3 Katmanlı Pin Doğrulama)
Ücretsiz Geocoding servisleri (OpenStreetMap Nominatim ve ArcGIS) aynı isimli mahalle veya caddeleri zaman zaman farklı bir şehirde çözümleyebilmektedir (Örn: *Şırnak/Merkez* kaydının *İstanbul/Çekmeköy* koordinatına düşmesi). Gözle kontrolü imkânsız olan bu sapmaları yakalamak için **Haversine Küresel Mesafe Formülü** tabanlı otonom bir denetleyici geliştirilmiştir:

$$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$

1. **Katman 1 — Geçmiş Koordinat Hafızası (Historical Lookup):** Dış API'ye çıkmadan önce eczanenin geçmiş nöbet kayıtlarındaki doğrulanmış koordinatı veritabanından sorgulanır (`0 ms` maliyet).
2. **Katman 2 — Türkçe Slug Dönüşümü & Proaktif Geocoding Sınırı:** URL slug'ları (`cankiri` $\rightarrow$ `Çankırı`, `igdir` $\rightarrow$ `Iğdır`) gerçek Türkçe karakterli il adlarına çevrilerek Nominatim/ArcGIS'e gönderilir. Dönen koordinat hedef il merkezinden `> 160 km` uzaktaysa veritabanına yazılmadan anında reddedilir.
3. **Katman 3 — Küme Medyanı & İl Merkezi Karşılaştırmalı Outlier Tarayıcısı:** `outlier_scanner.py`, her eczanenin koordinatını hem kayıtlı olduğu ilin standart merkeziyle hem de o ilçedeki diğer eczanelerin **medyan küme merkeziyle** karşılaştırır. Böylece *Mersin/Anamur* (`179 km`) veya *Antalya/Kaş* (`135 km`) gibi coğrafi olarak il merkezine uzak olan gerçek dış ilçeleri korurken; kendi ilçe kümesinden `> 40 km` sapan veya başka bir ilin sınırlarına düşen hatalı pinleri tespit edip sıfırlar.

### 4. 🧭 Akıllı Routing, Google Maps "Coordinate Snapping" Çözümü & UX
* **Google Maps Cadde-Ortası Sapmasını (Snapping) Önleyen Yol Tarifi:** Ücretsiz Geocoding servisleri kapı numarasını bulamadığında caddenin tam orta noktasının koordinatını döndürür. Google Haritalar'a bu ham koordinat gönderildiğinde, caddenin ortasında bulunan alakasız bir bina veya başka bir eczane hedeflenir. Bunu önlemek için **"Yol Tarifi Al"** modülü, ham koordinat yerine doğrudan `"Eczane Adı, Açık Adres, İlçe, İl, Türkiye"` metnini Google Maps POI motoruna ileterek %100 doğru işletme kapısına rota çizer.
* **Akıllı Karşılama & HTML5 Geolocation:** Kullanıcı ana sayfaya (`/`) girdiğinde sabit bir şehir dayatılmaz. Tarayıcının **HTML5 Geolocation API**'si ve Haversine algoritmasıyla kullanıcının koordinatına en yakın il otomatik bulunur (izin verilmezse IP tabanlı yedek devreye girer) veya interaktif **81 İl Türkiye Haritası** üzerinden plaka/il seçimi yapılır.
* **Dinamik SEO Metadata & BFF Reverse Proxy:** Seçilen il ve ilçeye göre sekme başlığı (`Örn: Sungurlu, Çorum Nöbetçi Eczaneleri (14 Açık) | Canlı Harita`), OpenGraph etiketleri ve URL (`?sehir=corum`) anlık güncellenir. Next.js `rewrites()` köprüsü sayesinde istemci yalnızca `/api/v1` bağıl yolunu kullanır; hem yerel ağda hem de `ngrok` tünellerinde CORS veya Mixed-Content hatası yaşanmaz.

---

## 🚀 Kurulum ve Çalıştırma

### Ön Gereksinimler
* **Docker** & **Docker Compose**
* **Node.js 18+** & **npm**

### 1. Ortam Değişkenlerini Hazırlayın
Proje kök dizinindeki `.env.example` dosyasını `.env` olarak kopyalayın:
```bash
cp .env.example .env
```

### 2. Backend, PostgreSQL ve Redis Servislerini Başlatın (Docker)
```bash
docker compose up -d --build
```
* **FastAPI Swagger UI (Dokümantasyon):** `http://localhost:8000/docs`
* **Sağlık Kontrolü (Healthcheck):** `http://localhost:8000/health`

### 3. Frontend (Next.js) Uygulamasını Başlatın
```bash
cd frontend
npm install
npm run dev
```
* **Canlı Harita Arayüzü:** `http://localhost:3000`

---

## 🔍 Operasyonel CLI ve QA Denetim Komutları

### Haversine Outlier (Aykırı Pin) Tarayıcısını Çalıştırma
Veritabanındaki tüm koordinatlı eczaneleri Haversine formülüyle taramak, başka şehre/denize düşen pinleri raporlamak ve otomatik düzeltmek (`--fix`) için:

```bash
# Sadece raporlama modu (varsayılan eşik: 50 km)
docker compose exec backend python scripts/outlier_scanner.py

# Hatalı/sapmış pinlerin koordinatlarını otomatik sıfırlama ve Redis önbelleğini tazeleme modu
docker compose exec backend python scripts/outlier_scanner.py --threshold 45 --fix
```

### Temel API Uç Noktaları (Endpoints)

| Metot | Uç Nokta (Endpoint) | Açıklama |
| :--- | :--- | :--- |
| `GET` | `/api/v1/eczaneler/{sehir}` | Belirtilen ildeki (Örn: `ankara`, `corum`) güncel nöbetçi eczaneleri getirir |
| `GET` | `/api/v1/eczaneler/{sehir}/{ilce}` | İl ve ilçeye göre (Örn: `konya/selcuklu`) nöbetçi eczaneleri filtreler |
| `GET` | `/api/v1/eczaneler/system/stats` | 81 ilin veritabanı doluluk ve koordinat başarı oranlarını özetler |
| `GET` | `/api/v1/eczaneler/system/outliers` | Haversine formülü ile aykırı koordinatlı pinleri listeler (`?fix=true` ile onarır) |
| `POST` | `/api/v1/eczaneler/system/cleanup` | Honeypot tuzak metinlerini ve sahte kayıtları SQL seviyesinde temizler |
| `POST` | `/api/v1/eczaneler/scrape/{sehir}` | Belirtilen ili (veya `all` ile 81 ili) anında tarayıp veritabanını günceller |

---

## 🗺️ Gelecek Yol Haritası (Roadmap — V2.0)

Gece yarısı acil ilaç arayan bir kullanıcının %1'lik bir koordinat sapmasıyla bile karşılaşmaması adına **V2.0** sürümünde şu mimari dönüşümler hedeflenmektedir:

- [ ] **Modüler Resmi Eczacı Odaları Adaptör Mimarisi (1. El Veri Kaynağı):** Üçüncü parti aracı siteleri tamamen devreden çıkararak, doğrudan **TEB (Türk Eczacıları Birliği) 81 İl Bölge Eczacı Odalarının** resmi web servislerinden (Örn: *Ankara Eczacı Odası `aeo.org.tr`*, *İstanbul Eczacı Odası `ieo.org.tr`*, *Konya Eczacı Odası `keo.org.tr`*) eczacı odası onaylı **%100 saf GPS koordinatlarının** çekileceği `BaseChamberAdapter` mimarisine geçiş.
- [ ] **Nöbet Bitiş Saati & Gece/Yarım Gün Nöbet Rozetleri:** Bazı ilçelerde saat `23:59`'a kadar nöbet tutan (*Yarım Nöbet*) eczaneler ile sabah `08:30`'a kadar açık olan (*Tam Nöbet*) eczanelerin arayüzde canlı geri sayım sayacıyla ayrıştırılması.
- [ ] **PWA & Mobil Uygulama Desteği:** Çevrimdışı (*Offline-First*) önbellekleme ve tek dokunuşla "Bana En Yakın Nöbetçi Eczaneye Götür" acil durum modülü.

---

<div align="center">
  <sub>Geliştirici: <b>Mehmet İhsan Ersoy</b> • Full-Stack Coğrafi Bilgi ve Otonom Veri Mühendisliği Projesi</sub>
</div>
