"""
Pin Doğruluğu İçin Aykırı Değer (Outlier) Tarayıcısı (Haversine Formülü)
Kullanım:
  docker compose exec backend python scripts/outlier_scanner.py
  docker compose exec backend python scripts/outlier_scanner.py --threshold 45 --fix
"""

import argparse
import asyncio
import os
import sys

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.scraper import scan_coordinate_outliers


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Haversine formülü ile eczane pin koordinatlarının il/ilçe merkezine mesafesini denetler."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=50.0,
        help="İl merkezine maksimum kabul edilebilir kuş uçuşu mesafe eşiği (km, varsayılan: 50.0)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Kendi ilçe/il kümesinden sapmış (başka şehre düşmüş) hatalı pinlerin koordinatlarını sıfırla",
    )
    args = parser.parse_args()

    print(f"\n[Outlier Tarayıcı] Haversine analizi başlatılıyor (Eşik: {args.threshold} km, Fix: {args.fix})...")
    report = await scan_coordinate_outliers(
        threshold_km=args.threshold,
        fix_outliers=args.fix,
    )

    print("=" * 80)
    print(f"Aktif Nöbet Tarihi           : {report['aktif_nobet_tarihi']}")
    print(f"İncelenen Koordinatlı Eczane : {report['incelenen_koordinatli_eczane']}")
    print(f"Kesin Hatalı / Sapmış Pin    : {report['kesin_hatali_pin_sayisi']}")
    print(f"Uzak Dış İlçe Eczanesi (>50km): {report['uzak_dis_ilce_eczane_sayisi']}")
    if args.fix:
        print(f"Sıfırlanan Hatalı Koordinat  : {report['duzeltilen_kayit_sayisi']}")
    print("=" * 80)

    if report["kesin_hatali_pinler"]:
        print("\n[!] KESİN HATALI VEYA BAŞKA ŞEHRE DÜŞMÜŞ PİNLER:")
        for idx, item in enumerate(report["kesin_hatali_pinler"], start=1):
            print(
                f"  {idx:02d}. [{item['sehir'].upper()} / {item['ilce']}] {item['isim']}\n"
                f"      Koordinat : ({item['enlem']}, {item['boylam']})\n"
                f"      İl Merkezine Mesafe   : {item['il_merkezine_mesafe_km']} km\n"
                f"      İlçe Merkezine Mesafe : {item['ilce_merkezine_mesafe_km']} km\n"
                f"      Fiziksel En Yakın İl  : {item['fiziksel_en_yakin_il'].upper()} ({item['en_yakin_ile_mesafe_km']} km)\n"
                f"      Adres                 : {item['adres']}"
            )
    else:
        print("\n[✓] Harika! Başka şehre veya denize düşmüş hiçbir hatalı (outlier) pin bulunamadı.")


if __name__ == "__main__":
    asyncio.run(main())
