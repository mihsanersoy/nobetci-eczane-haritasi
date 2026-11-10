import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Türkiye 81 İl Nöbetçi Eczaneler | Canlı Harita",
    template: "%s | Canlı Nöbetçi Eczane Haritası",
  },
  description:
    "Türkiye genelinde 81 il ve tüm ilçelerdeki güncel nöbetçi eczaneleri interaktif harita üzerinde görüntüleyin, konumunuza en yakın eczaneyi bulun ve yol tarifi alın.",
  keywords: [
    "nöbetçi eczane",
    "nöbetçi eczaneler",
    "canlı nöbetçi eczane haritası",
    "en yakın nöbetçi eczane",
    "81 il nöbetçi eczane",
  ],
  openGraph: {
    title: "Türkiye 81 İl Nöbetçi Eczaneler | Canlı Harita",
    description:
      "Bulunduğunuz şehri seçin veya konumunuzu kullanarak size en yakın açık nöbetçi eczaneleri haritada anında görüntüleyin.",
    locale: "tr_TR",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className="antialiased bg-slate-50 text-slate-900 selection:bg-red-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}
