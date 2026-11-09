"use client";

import React, { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Eczane, TURKIYE_81_ILLER } from "@/types/eczane";

// Varsayılan Merkez Koordinatları (Ankara)
const DEFAULT_CENTER: [number, number] = [39.9208, 32.8541];

// Ankara ilçeleri için detaylı koordinat yedeği
const ANKARA_ILCE_COORDS: Record<string, [number, number]> = {
  akyurt: [40.1353, 33.0849],
  altındağ: [39.9565, 32.8742],
  ayaş: [40.0176, 32.3338],
  bala: [39.5546, 33.1235],
  beypazarı: [40.1678, 31.9211],
  çamlıdere: [40.491, 32.4754],
  çankaya: [39.9008, 32.8603],
  çubuk: [40.2386, 33.0322],
  elmadağ: [39.9213, 33.2307],
  etimesgut: [39.9482, 32.6691],
  evren: [39.0247, 33.8058],
  gölbaşı: [39.7918, 32.8065],
  güdül: [40.2117, 32.2454],
  haymana: [39.4317, 32.4959],
  kahramankazan: [40.1997, 32.6819],
  kazan: [40.1997, 32.6819],
  kalecik: [40.0972, 33.4084],
  keçiören: [39.9922, 32.8631],
  kızılcahamam: [40.4712, 32.6502],
  mamak: [39.9272, 32.9234],
  nallıhan: [40.1869, 31.3522],
  polatlı: [39.5842, 32.1472],
  pursaklar: [40.0389, 32.9022],
  sincan: [39.9744, 32.5808],
  şereflikoçhisar: [38.9383, 33.5386],
  yenimahalle: [39.9699, 32.7997],
  merkez: [39.9208, 32.8541],
};

const CITY_CENTER_MAP: Record<string, [number, number]> = Object.fromEntries(
  TURKIYE_81_ILLER.map((c) => [c.slug, c.center])
);

/**
 * Eczanenin gerçek koordinatı varsa onu döndürür; yoksa seçilen ilin/ilçenin
 * merkez koordinatı etrafına deterministik küçük bir dağılım ekleyerek döndürür.
 */
export function resolveEczaneCoords(
  eczane: Eczane,
  selectedCity: string
): [number, number] {
  if (
    typeof eczane.enlem === "number" &&
    typeof eczane.boylam === "number" &&
    !Number.isNaN(eczane.enlem) &&
    !Number.isNaN(eczane.boylam)
  ) {
    return [eczane.enlem, eczane.boylam];
  }

  const citySlug = (eczane.sehir || selectedCity || "ankara").toLowerCase();
  const normalizedIlce = eczane.ilce
    .trim()
    .toLocaleLowerCase("tr-TR")
    .split(/[\s\-\/]+/)[0];

  const base =
    (citySlug === "ankara" && ANKARA_ILCE_COORDS[normalizedIlce]) ||
    CITY_CENTER_MAP[citySlug] ||
    DEFAULT_CENTER;

  let hash = 0;
  for (let i = 0; i < eczane.id.length; i++) {
    hash = (hash << 5) - hash + eczane.id.charCodeAt(i);
    hash |= 0;
  }
  const latOffset = ((hash % 100) / 100) * 0.018 - 0.009;
  const lngOffset = (((hash >> 8) % 100) / 100) * 0.024 - 0.012;

  return [base[0] + latOffset, base[1] + lngOffset];
}

/**
 * Özel Eczane "E" Logolu Pin İkonu
 */
const createPharmacyIcon = (isSelected: boolean) =>
  L.divIcon({
    className: "custom-pharmacy-marker",
    html: `
      <div class="relative flex items-center justify-center transition-transform duration-300 ${
        isSelected ? "scale-125 z-50" : "hover:scale-110"
      }">
        <div class="w-9 h-9 rounded-full ${
          isSelected
            ? "bg-red-700 ring-4 ring-red-300"
            : "bg-red-600 ring-2 ring-white"
        } shadow-lg flex items-center justify-center text-white font-extrabold text-base border border-red-800">
          E
        </div>
        <div class="absolute -bottom-1.5 w-3 h-3 bg-red-600 rotate-45 border-r border-b border-red-800"></div>
      </div>
    `,
    iconSize: [36, 42],
    iconAnchor: [18, 42],
    popupAnchor: [0, -40],
  });

/**
 * Şehir değiştiğinde veya listeden bir eczane seçildiğinde haritayı ilgili konuma uçuran kontrolcü
 */
function MapViewportController({
  selectedCity,
  selectedEczane,
}: {
  selectedCity: string;
  selectedEczane: Eczane | null;
}) {
  const map = useMap();

  // 1. Kullanıcı Dropdown'dan yeni bir şehir seçtiğinde haritayı o şehrin merkezine uçur
  useEffect(() => {
    const cityCenter = CITY_CENTER_MAP[selectedCity] || DEFAULT_CENTER;
    map.flyTo(cityCenter, 11, {
      animate: true,
      duration: 1.2,
    });
  }, [selectedCity, map]);

  // 2. Kullanıcı listeden spesifik bir eczaneye tıkladığında o eczanenin pinine yakınlaş
  useEffect(() => {
    if (selectedEczane) {
      const coords = resolveEczaneCoords(selectedEczane, selectedCity);
      map.flyTo(coords, 15, {
        animate: true,
        duration: 1.2,
      });
    }
  }, [selectedEczane, selectedCity, map]);

  return null;
}

interface MapComponentProps {
  selectedCity: string;
  selectedCityName: string;
  eczaneler: Eczane[];
  selectedEczane: Eczane | null;
  onSelectEczane: (eczane: Eczane) => void;
}

export default function MapComponent({
  selectedCity,
  selectedCityName,
  eczaneler,
  selectedEczane,
  onSelectEczane,
}: MapComponentProps) {
  const defaultIcon = useMemo(() => createPharmacyIcon(false), []);
  const selectedIcon = useMemo(() => createPharmacyIcon(true), []);

  const initialCenter = CITY_CENTER_MAP[selectedCity] || DEFAULT_CENTER;

  // Google Haritalar Yol Tarifi URL üreticisi
  const getDirectionsUrl = (eczane: Eczane) => {
    if (eczane.enlem && eczane.boylam) {
      return `https://www.google.com/maps/dir/?api=1&destination=${eczane.enlem},${eczane.boylam}`;
    }
    const query = encodeURIComponent(
      `${eczane.isim} Eczanesi ${eczane.adres} ${eczane.ilce} ${selectedCityName}`
    );
    return `https://www.google.com/maps/dir/?api=1&destination=${query}`;
  };

  return (
    <div className="w-full h-full relative">
      <MapContainer
        center={initialCenter}
        zoom={11}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıda bulunanlar'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Şehir ve Eczane Seçimi Kamera Kontrolcüsü */}
        <MapViewportController
          selectedCity={selectedCity}
          selectedEczane={selectedEczane}
        />

        {/* Eczane Pinleri (Markers) */}
        {eczaneler.map((eczane) => {
          const position = resolveEczaneCoords(eczane, selectedCity);
          const isSelected = selectedEczane?.id === eczane.id;

          return (
            <Marker
              key={eczane.id}
              position={position}
              icon={isSelected ? selectedIcon : defaultIcon}
              eventHandlers={{
                click: () => onSelectEczane(eczane),
              }}
            >
              <Popup minWidth={250} maxWidth={300}>
                <div className="flex flex-col gap-2 text-slate-800">
                  <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2">
                    <h3 className="font-bold text-base text-slate-900 leading-snug">
                      {eczane.isim}
                    </h3>
                    <span className="shrink-0 bg-red-50 text-red-700 border border-red-200 text-xs font-semibold px-2 py-0.5 rounded-full">
                      {eczane.ilce}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed m-0">
                    📍 {eczane.adres}
                  </p>

                  {eczane.telefon && (
                    <a
                      href={`tel:${eczane.telefon.replace(/\s+/g, "")}`}
                      className="text-xs font-semibold text-slate-700 hover:text-red-600 flex items-center gap-1.5 no-underline"
                    >
                      📞 <span>{eczane.telefon}</span>
                    </a>
                  )}

                  <a
                    href={getDirectionsUrl(eczane)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 w-full bg-red-600 hover:bg-red-700 !text-white font-semibold text-xs py-2 px-3 rounded-lg text-center transition-colors shadow-sm flex items-center justify-center gap-1.5 no-underline"
                  >
                    <span>🗺️</span>
                    <span>Yol Tarifi Al (Google Maps)</span>
                  </a>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
