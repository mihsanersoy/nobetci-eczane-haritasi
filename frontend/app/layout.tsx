import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ankara Nöbetçi Eczaneler | Canlı Harita",
  description:
    "Ankara genelindeki güncel nöbetçi eczaneleri interaktif harita üzerinde görüntüleyin, ilçe bazlı filtreleyin ve yol tarifi alın.",
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
