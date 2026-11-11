"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { CityOption, Eczane, TURKIYE_81_ILLER } from "@/types/eczane";

// Next.js SSR uyumsuzluğunu önlemek için MapComponent'i ssr: false ile dinamik yüklüyoruz.
const MapComponent = dynamic(() => import("@/components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex flex-col items-center justify-center bg-slate-100 text-slate-500 gap-3">
      <div className="w-10 h-10 border-4 border-red-600 border-t-transparent rounded-full animate-spin" />
      <p className="text-sm font-medium">Türkiye haritası yükleniyor...</p>
    </div>
  ),
});

// Next.js rewrites() köprüsü üzerinden hem localhost hem Ngrok ile sorunsuz çalışır
const API_BASE_URL = "/api/v1";

const POPULAR_CITIES = [
  "istanbul",
  "ankara",
  "izmir",
  "antalya",
  "bursa",
  "adana",
  "konya",
  "gaziantep",
];

/**
 * İki koordinat arasındaki kuş uçuşu mesafeyi Haversine formülü ile (km) hesaplar.
 * Kullanıcının HTML5 Geolocation konumuna en yakın ili bulmak için kullanılır.
 */
function haversineDistanceKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function findNearestCityByCoords(lat: number, lon: number): CityOption {
  let nearest = TURKIYE_81_ILLER[5]; // Varsayılan: Ankara
  let minDistance = Infinity;
  for (const city of TURKIYE_81_ILLER) {
    const dist = haversineDistanceKm(lat, lon, city.center[0], city.center[1]);
    if (dist < minDistance) {
      minDistance = dist;
      nearest = city;
    }
  }
  return nearest;
}

export default function HomePage() {
  // İlk açılışta sabit "ankara" yerine null (Türkiye Geneli Karşılama Ekranı)
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [cityFilterQuery, setCityFilterQuery] = useState<string>("");
  const [isLocating, setIsLocating] = useState<boolean>(false);
  const [geoMessage, setGeoMessage] = useState<string | null>(null);

  const [eczaneler, setEczaneler] = useState<Eczane[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedIlce, setSelectedIlce] = useState<string>("Tümü");
  const [selectedEczane, setSelectedEczane] = useState<Eczane | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Seçili şehrin nesnesini bul (null ise karşılama ekranındayız)
  const selectedCityObj = useMemo(
    () =>
      selectedCity
        ? TURKIYE_81_ILLER.find((c) => c.slug === selectedCity) || null
        : null,
    [selectedCity]
  );

  // Şehir seçme ve URL (?sehir=...) güncelleme yardımcı fonksiyonu
  const handleSelectCity = useCallback((slug: string | null) => {
    setSelectedCity(slug);
    setSearchQuery("");
    setSelectedIlce("Tümü");
    setSelectedEczane(null);

    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      if (slug) {
        url.searchParams.set("sehir", slug);
      } else {
        url.searchParams.delete("sehir");
      }
      window.history.replaceState({}, "", url.toString());
    }
  }, []);

  // Sayfa ilk yüklendiğinde URL'de ?sehir=corum gibi bir parametre varsa doğrudan o ili aç
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const cityParam = params.get("sehir")?.trim().toLowerCase();
    if (cityParam && TURKIYE_81_ILLER.some((c) => c.slug === cityParam)) {
      setSelectedCity(cityParam);
    }
  }, []);

  // GÖREV 2.1: Dinamik Metadata (Sekme Başlığı ve SEO Açıklama Etiketleri)
  useEffect(() => {
    if (typeof document === "undefined") return;

    const updateMetaTag = (selector: string, content: string) => {
      const el = document.querySelector(selector);
      if (el) el.setAttribute("content", content);
    };

    if (!selectedCityObj) {
      const defaultTitle = "Türkiye 81 İl Nöbetçi Eczaneler | Canlı Harita";
      const defaultDesc =
        "Türkiye genelinde 81 il ve tüm ilçelerdeki güncel nöbetçi eczaneleri interaktif harita üzerinde görüntüleyin ve yol tarifi alın.";
      document.title = defaultTitle;
      updateMetaTag('meta[name="description"]', defaultDesc);
      updateMetaTag('meta[property="og:title"]', defaultTitle);
      return;
    }

    const ilcePrefix =
      selectedIlce !== "Tümü" ? `${selectedIlce}, ` : "";
    const countSuffix =
      !isLoading && eczaneler.length > 0 ? ` (${eczaneler.length} Açık)` : "";

    const dynamicTitle = `${ilcePrefix}${selectedCityObj.name} Nöbetçi Eczaneleri${countSuffix} | Canlı Harita`;
    const dynamicDesc = `${selectedCityObj.name} ${
      selectedIlce !== "Tümü" ? selectedIlce + " ilçesi " : ""
    }nöbetçi eczaneler listesi, açık adresleri, telefon numaraları ve canlı harita konumu.`;

    document.title = dynamicTitle;
    updateMetaTag('meta[name="description"]', dynamicDesc);
    updateMetaTag('meta[property="og:title"]', dynamicTitle);
  }, [selectedCityObj, selectedIlce, eczaneler.length, isLoading]);

  // GÖREV 2.2: HTML5 Geolocation + IP Fallback ile Akıllı Şehir Tespiti
  const detectUserCity = useCallback(async () => {
    setIsLocating(true);
    setGeoMessage("Konumunuz tespit ediliyor...");

    // Yöntem 1: Tarayıcı HTML5 Geolocation API + Haversine Mesafe Ölçümü
    if (typeof navigator !== "undefined" && "geolocation" in navigator) {
      try {
        const pos = await new Promise<GeolocationPosition>(
          (resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
              enableHighAccuracy: false,
              timeout: 6000,
              maximumAge: 300000,
            });
          }
        );
        const nearest = findNearestCityByCoords(
          pos.coords.latitude,
          pos.coords.longitude
        );
        setGeoMessage(`Konumunuz ${nearest.name} olarak tespit edildi.`);
        handleSelectCity(nearest.slug);
        setIsLocating(false);
        return;
      } catch {
        // Kullanıcı izin vermediyse veya GPS zaman aşımına uğradıysa IP tabanlı yedek yönteme geç
      }
    }

    // Yöntem 2: IP Tabanlı Konum Tespiti (Fallback)
    try {
      const res = await fetch("https://ipapi.co/json/", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        if (typeof data.latitude === "number" && typeof data.longitude === "number") {
          const nearest = findNearestCityByCoords(data.latitude, data.longitude);
          setGeoMessage(`IP konumunuza göre ${nearest.name} seçildi.`);
          handleSelectCity(nearest.slug);
          setIsLocating(false);
          return;
        }
      }
    } catch {
      // IP servisi engelliyse sessizce geç
    }

    setGeoMessage(
      "Otomatik konum alınamadı. Lütfen aşağıdaki listeden veya haritadan ilinizi seçin."
    );
    setIsLocating(false);
  }, [handleSelectCity]);

  // Seçilen şehre göre FastAPI Backend'den (/api/v1/eczaneler/{sehir}) nöbetçi eczaneleri çek
  useEffect(() => {
    if (!selectedCity || !selectedCityObj) {
      setEczaneler([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    let isCancelled = false;

    const fetchEczanelerByCity = async () => {
      try {
        setIsLoading(true);
        setError(null);
        setSelectedIlce("Tümü");
        setSelectedEczane(null);

        const response = await fetch(
          `${API_BASE_URL}/eczaneler/${selectedCity}`,
          {
            cache: "no-store",
          }
        );

        if (!response.ok) {
          throw new Error(`API Hatası: ${response.status}`);
        }

        const data: Eczane[] = await response.json();
        if (!isCancelled) {
          setEczaneler(data);
        }
      } catch (err) {
        console.error(
          `'${selectedCity}' eczane verileri çekilirken hata oluştu:`,
          err
        );
        if (!isCancelled) {
          setError(
            `${selectedCityObj.name} nöbetçi eczane verilerine şu anda ulaşılamıyor. Lütfen Backend servisinin çalıştığından emin olun.`
          );
          setEczaneler([]);
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchEczanelerByCity();

    return () => {
      isCancelled = true;
    };
  }, [selectedCity, selectedCityObj]);

  // Karşılama ekranındaki 81 il arama filtresi
  const filteredCitiesForWelcome = useMemo(() => {
    if (!cityFilterQuery.trim()) return TURKIYE_81_ILLER;
    const q = cityFilterQuery.toLocaleLowerCase("tr-TR").trim();
    return TURKIYE_81_ILLER.filter(
      (c) =>
        c.name.toLocaleLowerCase("tr-TR").includes(q) ||
        c.slug.includes(q) ||
        c.plaka.includes(q)
    );
  }, [cityFilterQuery]);

  // Mevcut şehrin verilerinden benzersiz ilçe listesini çıkar
  const ilceler = useMemo(() => {
    const unique = Array.from(new Set(eczaneler.map((e) => e.ilce))).sort(
      (a, b) => a.localeCompare(b, "tr-TR")
    );
    return ["Tümü", ...unique];
  }, [eczaneler]);

  // İlçe seçimi ve arama çubuğuna göre eczaneleri filtrele
  const filteredEczaneler = useMemo(() => {
    return eczaneler.filter((eczane) => {
      const matchesIlce =
        selectedIlce === "Tümü" ||
        eczane.ilce.toLocaleLowerCase("tr-TR") ===
          selectedIlce.toLocaleLowerCase("tr-TR");

      if (!searchQuery.trim()) return matchesIlce;

      const q = searchQuery.toLocaleLowerCase("tr-TR");
      const matchesQuery =
        eczane.ilce.toLocaleLowerCase("tr-TR").includes(q) ||
        eczane.isim.toLocaleLowerCase("tr-TR").includes(q) ||
        eczane.adres.toLocaleLowerCase("tr-TR").includes(q);

      return matchesIlce && matchesQuery;
    });
  }, [eczaneler, selectedIlce, searchQuery]);

  // Google Maps Yol Tarifi Linki:
  // Nominatim cadde-ortası koordinatının Google Maps'te yan bina/farklı eczane göstermesini
  // önlemek için Google Maps'in kendi POI veritabanına doğrudan eczane adı + açık adres gönderilir.
  const getDirectionsUrl = (eczane: Eczane) => {
    const cityName = selectedCityObj ? selectedCityObj.name : eczane.sehir;
    const cleanAdres = eczane.adres.split("→")[0].trim();
    const query = encodeURIComponent(
      `${eczane.isim}, ${cleanAdres}, ${eczane.ilce}, ${cityName}, Türkiye`
    );
    return `https://www.google.com/maps/dir/?api=1&destination=${query}`;
  };

  return (
    <main className="flex flex-col md:flex-row h-screen w-screen overflow-hidden bg-slate-50">
      {/* SOL KENAR ÇUBUĞU (SIDEBAR) */}
      <aside className="w-full md:w-[430px] lg:w-[470px] h-[52vh] md:h-full flex flex-col bg-white border-b md:border-b-0 md:border-r border-slate-200 shadow-lg z-20 shrink-0">
        {/* Üst Başlık (Header) */}
        <div className="p-4 bg-gradient-to-r from-red-600 to-red-700 text-white shadow-sm space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <button
                onClick={() => handleSelectCity(null)}
                title="Türkiye 81 İl Karşılama Ekranına Dön"
                className="w-9 h-9 rounded-lg bg-white text-red-600 font-black text-xl flex items-center justify-center shadow hover:scale-105 transition-transform shrink-0"
              >
                E
              </button>
              <div className="min-w-0">
                <h1 className="font-bold text-lg leading-tight truncate">
                  {selectedCityObj
                    ? `${selectedCityObj.name} Nöbetçi Eczaneleri`
                    : "Türkiye Nöbetçi Eczaneler"}
                </h1>
                <p className="text-xs text-red-100 truncate">
                  {selectedCityObj
                    ? `${selectedCityObj.plaka} Plaka • Canlı Nöbetçi Eczane Haritası`
                    : "81 İl Canlı Nöbetçi Eczane Haritası"}
                </p>
              </div>
            </div>

            {selectedCityObj ? (
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => handleSelectCity(null)}
                  className="bg-white/15 hover:bg-white/25 border border-white/30 text-white text-xs font-semibold px-2.5 py-1 rounded-full transition-colors"
                  title="81 İl Haritasına Dön"
                >
                  🗺️ 81 İl
                </button>
                <span className="bg-red-800/60 border border-red-400/30 text-xs font-semibold px-2.5 py-1 rounded-full">
                  {filteredEczaneler.length} Eczane
                </span>
              </div>
            ) : (
              <span className="bg-red-800/60 border border-red-400/30 text-xs font-semibold px-2.5 py-1 rounded-full shrink-0">
                81 İl Aktif
              </span>
            )}
          </div>

          {/* Şehir Seçiliyse: 81 İl Dropdown + Konum Butonu + Eczane Arama Çubuğu */}
          {selectedCityObj && (
            <div className="grid grid-cols-1 sm:grid-cols-12 gap-2">
              <div className="sm:col-span-5 flex gap-1.5">
                <div className="relative flex-1">
                  <select
                    aria-label="Şehir Seçin"
                    value={selectedCity || ""}
                    onChange={(e) => handleSelectCity(e.target.value)}
                    className="w-full pl-2.5 pr-6 py-2 rounded-lg bg-white text-slate-800 font-semibold text-xs focus:outline-none focus:ring-2 focus:ring-red-200 shadow-inner cursor-pointer appearance-none"
                  >
                    {TURKIYE_81_ILLER.map((city) => (
                      <option key={city.slug} value={city.slug}>
                        {city.plaka} - {city.name}
                      </option>
                    ))}
                  </select>
                  <span className="pointer-events-none absolute right-2 top-2.5 text-slate-500 text-[10px]">
                    ▼
                  </span>
                </div>

                <button
                  onClick={detectUserCity}
                  disabled={isLocating}
                  title="Bulunduğum şehri otomatik bul"
                  className="px-2.5 py-2 rounded-lg bg-red-800/70 hover:bg-red-800 text-white text-xs font-bold border border-red-400/30 transition-colors shrink-0"
                >
                  {isLocating ? "⏳" : "📍"}
                </button>
              </div>

              <div className="sm:col-span-7 relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={`${selectedCityObj.name} içinde ilçe veya eczane ara...`}
                  className="w-full pl-8 pr-7 py-2 rounded-lg bg-white/95 text-slate-800 placeholder-slate-400 text-xs focus:outline-none focus:ring-2 focus:ring-white shadow-inner"
                />
                <span className="absolute left-2.5 top-2 text-slate-400 text-xs">
                  🔍
                </span>
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2.5 top-1.5 text-slate-400 hover:text-slate-600 text-xs font-bold"
                    title="Aramayı temizle"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* DURUM A: AKILLI KARŞILAMA EKRANI (ŞEHİR HENÜZ SEÇİLMEDİYSE)       */}
        {/* ================================================================= */}
        {!selectedCityObj ? (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Otomatik Konum (HTML5 Geolocation) Kartı */}
            <div className="p-4 rounded-2xl bg-gradient-to-br from-red-50 via-white to-red-50/40 border border-red-200/80 shadow-sm space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="text-sm font-bold text-slate-900">
                    👋 Hoş Geldiniz! Şehrinizi Seçin
                  </h2>
                  <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                    Size en yakın açık nöbetçi eczaneleri görmek için konumunuzu
                    kullanabilir veya 81 ilden birini seçebilirsiniz.
                  </p>
                </div>
              </div>

              <button
                onClick={detectUserCity}
                disabled={isLocating}
                className="w-full py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white font-bold text-xs shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>{isLocating ? "⏳" : "📍"}</span>
                <span>
                  {isLocating
                    ? "Konumunuz Tespit Ediliyor..."
                    : "Konumumu Bul ve En Yakın İli Aç"}
                </span>
              </button>

              {geoMessage && (
                <p className="text-[11px] text-slate-600 font-medium text-center bg-white/80 py-1 px-2 rounded-lg border border-slate-200/60">
                  {geoMessage}
                </p>
              )}
            </div>

            {/* Büyükşehirler Hızlı Erişim Rozetleri */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-1">
                Popüler Büyükşehirler
              </span>
              <div className="flex flex-wrap gap-1.5">
                {POPULAR_CITIES.map((slug) => {
                  const city = TURKIYE_81_ILLER.find((c) => c.slug === slug);
                  if (!city) return null;
                  return (
                    <button
                      key={city.slug}
                      onClick={() => handleSelectCity(city.slug)}
                      className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-red-600 text-slate-700 hover:text-white text-xs font-semibold transition-colors cursor-pointer"
                    >
                      {city.name}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 81 İl Arama ve Seçim Izgarası */}
            <div className="space-y-2">
              <div className="relative">
                <input
                  type="text"
                  value={cityFilterQuery}
                  onChange={(e) => setCityFilterQuery(e.target.value)}
                  placeholder="İl adı veya plaka kodu yazın (Örn: 19 veya Çorum)..."
                  className="w-full pl-8 pr-8 py-2 rounded-xl bg-slate-50 border border-slate-200 text-slate-800 placeholder-slate-400 text-xs focus:outline-none focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
                <span className="absolute left-2.5 top-2 text-slate-400 text-xs">
                  🔍
                </span>
                {cityFilterQuery && (
                  <button
                    onClick={() => setCityFilterQuery("")}
                    className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600 text-xs font-bold"
                  >
                    ✕
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 pt-1">
                {filteredCitiesForWelcome.map((city) => (
                  <button
                    key={city.slug}
                    onClick={() => handleSelectCity(city.slug)}
                    className="flex items-center gap-2 p-2 rounded-xl border border-slate-200/80 hover:border-red-400 hover:bg-red-50/50 text-left transition-all group cursor-pointer"
                  >
                    <span className="w-6 h-6 rounded-lg bg-slate-100 group-hover:bg-red-600 text-slate-700 group-hover:text-white text-[11px] font-extrabold flex items-center justify-center shrink-0 transition-colors">
                      {city.plaka}
                    </span>
                    <span className="text-xs font-semibold text-slate-800 group-hover:text-red-700 truncate">
                      {city.name}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* ================================================================= */
          /* DURUM B: SEÇİLEN İLİN İLÇE FİLTRELERİ VE NÖBETÇİ ECZANE LİSTESİ   */
          /* ================================================================= */
          <>
            {ilceler.length > 1 && (
              <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-1.5 overflow-x-auto no-scrollbar shrink-0">
                {ilceler.map((ilce) => {
                  const active = selectedIlce === ilce;
                  return (
                    <button
                      key={ilce}
                      onClick={() => setSelectedIlce(ilce)}
                      className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
                        active
                          ? "bg-red-600 text-white shadow-sm"
                          : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
                      }`}
                    >
                      {ilce}
                    </button>
                  );
                })}
              </div>
            )}

            <div className="flex-1 overflow-y-auto divide-y divide-slate-100 p-2 space-y-2">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-48 text-slate-400 gap-2">
                  <div className="w-7 h-7 border-3 border-red-600 border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs font-medium">
                    {selectedCityObj.name} nöbetçi eczaneleri yükleniyor...
                  </span>
                </div>
              ) : error ? (
                <div className="m-3 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs leading-relaxed">
                  <p className="font-bold mb-1">⚠️ Bağlantı Hatası</p>
                  <p>{error}</p>
                </div>
              ) : filteredEczaneler.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-slate-400 text-center px-4">
                  <p className="text-sm font-semibold text-slate-600">
                    Kayıtlı Nöbetçi Eczane Bulunamadı
                  </p>
                  <p className="text-xs mt-1">
                    {selectedCityObj.name} ili için arama kriterlerinize uygun
                    sonuç bulunamadı.
                  </p>
                </div>
              ) : (
                filteredEczaneler.map((eczane) => {
                  const isSelected = selectedEczane?.id === eczane.id;
                  return (
                    <div
                      key={eczane.id}
                      onClick={() => setSelectedEczane(eczane)}
                      className={`p-3.5 rounded-xl cursor-pointer transition-all border ${
                        isSelected
                          ? "bg-red-50/70 border-red-400 shadow-sm ring-1 ring-red-400"
                          : "bg-white border-slate-200/80 hover:border-red-200 hover:bg-slate-50/60"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h2 className="font-bold text-sm text-slate-900">
                          {eczane.isim}
                        </h2>
                        <span className="shrink-0 bg-red-100 text-red-700 text-[11px] font-semibold px-2 py-0.5 rounded-md">
                          {eczane.ilce}
                        </span>
                      </div>

                      <p className="mt-1.5 text-xs text-slate-600 line-clamp-2 leading-relaxed">
                        📍 {eczane.adres}
                      </p>

                      <div className="mt-3 flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
                        {eczane.telefon ? (
                          <a
                            href={`tel:${eczane.telefon.replace(/\s+/g, "")}`}
                            onClick={(e) => e.stopPropagation()}
                            className="text-xs font-semibold text-slate-700 hover:text-red-600 flex items-center gap-1"
                          >
                            📞 {eczane.telefon}
                          </a>
                        ) : (
                          <span className="text-xs text-slate-400">
                            Telefon belirtilmemiş
                          </span>
                        )}

                        <a
                          href={getDirectionsUrl(eczane)}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs font-semibold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-2.5 py-1 rounded-md transition-colors"
                        >
                          Yol Tarifi ↗
                        </a>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </>
        )}
      </aside>

      {/* SAĞ PANEL (HARİTA: KARŞILAMA MODUNDA 81 İL HARİTASI, ŞEHİR SEÇİLİNCE ECZANE HARİTASI) */}
      <section className="flex-1 h-[48vh] md:h-full relative">
        <MapComponent
          selectedCity={selectedCity}
          selectedCityName={selectedCityObj ? selectedCityObj.name : "Türkiye"}
          eczaneler={filteredEczaneler}
          selectedEczane={selectedEczane}
          onSelectEczane={(eczane) => setSelectedEczane(eczane)}
          onSelectCity={(citySlug) => handleSelectCity(citySlug)}
        />
      </section>
    </main>
  );
}
