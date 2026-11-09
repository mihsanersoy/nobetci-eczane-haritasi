"use client";

import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Eczane, TURKIYE_81_ILLER } from "@/types/eczane";

// Next.js SSR uyumsuzluğunu önlemek için MapComponent'i ssr: false ile dinamik yüklüyoruz.
const MapComponent = dynamic(() => import("@/components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex flex-col items-center justify-center bg-slate-100 text-slate-500 gap-3">
      <div className="w-10 h-10 border-4 border-red-600 border-t-transparent rounded-full animate-spin" />
      <p className="text-sm font-medium">Harita yükleniyor...</p>
    </div>
  ),
});

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function HomePage() {
  const [selectedCity, setSelectedCity] = useState<string>("ankara");
  const [eczaneler, setEczaneler] = useState<Eczane[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedIlce, setSelectedIlce] = useState<string>("Tümü");
  const [selectedEczane, setSelectedEczane] = useState<Eczane | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Seçili şehrin okunabilir (Türkçe) adını bul (Örn: "ankara" -> "Ankara")
  const selectedCityObj = useMemo(
    () =>
      TURKIYE_81_ILLER.find((c) => c.slug === selectedCity) ||
      TURKIYE_81_ILLER[5], // 06 Ankara
    [selectedCity]
  );

  // Seçilen şehre göre FastAPI Backend'den (/api/v1/eczaneler/{sehir}) nöbetçi eczaneleri çek
  useEffect(() => {
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
  }, [selectedCity, selectedCityObj.name]);

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

  // Google Maps Yol Tarifi Linki
  const getDirectionsUrl = (eczane: Eczane) => {
    if (eczane.enlem && eczane.boylam) {
      return `https://www.google.com/maps/dir/?api=1&destination=${eczane.enlem},${eczane.boylam}`;
    }
    const query = encodeURIComponent(
      `${eczane.isim} Eczanesi ${eczane.adres} ${eczane.ilce} ${selectedCityObj.name}`
    );
    return `https://www.google.com/maps/dir/?api=1&destination=${query}`;
  };

  return (
    <main className="flex flex-col md:flex-row h-screen w-screen overflow-hidden bg-slate-50">
      {/* SOL KENAR ÇUBUĞU (SIDEBAR) */}
      <aside className="w-full md:w-[420px] lg:w-[460px] h-[50vh] md:h-full flex flex-col bg-white border-b md:border-b-0 md:border-r border-slate-200 shadow-lg z-20 shrink-0">
        {/* Üst Başlık (Header) + 81 İl Seçim Dropdown'u */}
        <div className="p-4 bg-gradient-to-r from-red-600 to-red-700 text-white shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-white text-red-600 font-black text-xl flex items-center justify-center shadow">
                E
              </div>
              <div>
                <h1 className="font-bold text-lg leading-tight">
                  {selectedCityObj.name} Nöbetçi Eczaneler
                </h1>
                <p className="text-xs text-red-100">
                  Türkiye 81 İl Canlı Nöbetçi Eczane Haritası
                </p>
              </div>
            </div>
            <span className="bg-red-800/60 border border-red-400/30 text-xs font-semibold px-2.5 py-1 rounded-full shrink-0">
              {filteredEczaneler.length} Eczane
            </span>
          </div>

          {/* 81 İl Seçici (Dropdown) ve Arama Çubuğu */}
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
            {/* Şehir Seçimi Dropdown */}
            <div className="sm:col-span-2 relative">
              <select
                aria-label="Şehir Seçin"
                value={selectedCity}
                onChange={(e) => setSelectedCity(e.target.value)}
                className="w-full pl-3 pr-7 py-2 rounded-lg bg-white text-slate-800 font-semibold text-sm focus:outline-none focus:ring-2 focus:ring-red-200 shadow-inner cursor-pointer appearance-none"
              >
                {TURKIYE_81_ILLER.map((city) => (
                  <option key={city.slug} value={city.slug}>
                    {city.plaka} - {city.name}
                  </option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-2.5 top-2.5 text-slate-500 text-xs">
                ▼
              </span>
            </div>

            {/* İlçe / Eczane Arama Çubuğu */}
            <div className="sm:col-span-3 relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={`${selectedCityObj.name} içinde ilçe veya eczane ara...`}
                className="w-full pl-8 pr-7 py-2 rounded-lg bg-white/95 text-slate-800 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-white shadow-inner"
              />
              <span className="absolute left-2.5 top-2.5 text-slate-400 text-xs">
                🔍
              </span>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600 text-sm font-bold"
                  title="Aramayı temizle"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Hızlı İlçe Filtre Sekmeleri */}
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

        {/* Kaydırılabilir Eczane Listesi */}
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
                {selectedCityObj.name} ili için henüz veri çekilmemiş veya
                arama kriterlerinize uygun sonuç yok.
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
      </aside>

      {/* SAĞ PANEL (HARİTA) */}
      <section className="flex-1 h-[50vh] md:h-full relative">
        <MapComponent
          selectedCity={selectedCity}
          selectedCityName={selectedCityObj.name}
          eczaneler={filteredEczaneler}
          selectedEczane={selectedEczane}
          onSelectEczane={(eczane) => setSelectedEczane(eczane)}
        />
      </section>
    </main>
  );
}
