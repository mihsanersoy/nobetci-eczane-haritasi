/** @type {import('next').NextConfig} */
const nextConfig = {
  // 1. Leaflet MapContainer çift başlatma hatasını önlemek için false korunur
  reactStrictMode: false,

  // 2. Geliştirme tünellerine (Ngrok vb.) kişisel adresi ifşa etmeden joker (wildcard) ile izin verilir
  allowedDevOrigins: [
    "*.ngrok-free.dev",
    "*.ngrok-free.app",
    "localhost",
    "127.0.0.1",
  ],

  // 3. Reverse Proxy (BFF) Standartı: İstemci /api/v1 çağırır, Next.js arka uca iletir
  async rewrites() {
    const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
