export interface Eczane {
  id: string;
  isim: string;
  sehir: string;
  ilce: string;
  adres: string;
  telefon: string | null;
  enlem: number | null;
  boylam: number | null;
  nobet_tarihi: string;
  olusturulma_tarihi: string;
}

export interface CityOption {
  plaka: string;
  slug: string;
  name: string;
  center: [number, number];
}

export const TURKIYE_81_ILLER: CityOption[] = [
  { plaka: "01", slug: "adana", name: "Adana", center: [37.0, 35.3213] },
  { plaka: "02", slug: "adiyaman", name: "Adıyaman", center: [37.7648, 38.2786] },
  { plaka: "03", slug: "afyonkarahisar", name: "Afyonkarahisar", center: [38.7507, 30.5567] },
  { plaka: "04", slug: "agri", name: "Ağrı", center: [39.7191, 43.0503] },
  { plaka: "05", slug: "amasya", name: "Amasya", center: [40.6499, 35.8353] },
  { plaka: "06", slug: "ankara", name: "Ankara", center: [39.9208, 32.8541] },
  { plaka: "07", slug: "antalya", name: "Antalya", center: [36.8969, 30.7133] },
  { plaka: "08", slug: "artvin", name: "Artvin", center: [41.1828, 41.8183] },
  { plaka: "09", slug: "aydin", name: "Aydın", center: [37.856, 27.8416] },
  { plaka: "10", slug: "balikesir", name: "Balıkesir", center: [39.6484, 27.8826] },
  { plaka: "11", slug: "bilecik", name: "Bilecik", center: [40.1451, 29.9799] },
  { plaka: "12", slug: "bingol", name: "Bingöl", center: [38.8854, 40.498] },
  { plaka: "13", slug: "bitlis", name: "Bitlis", center: [38.4006, 42.1095] },
  { plaka: "14", slug: "bolu", name: "Bolu", center: [40.7392, 31.6089] },
  { plaka: "15", slug: "burdur", name: "Burdur", center: [37.7203, 30.2908] },
  { plaka: "16", slug: "bursa", name: "Bursa", center: [40.1885, 29.061] },
  { plaka: "17", slug: "canakkale", name: "Çanakkale", center: [40.1553, 26.4142] },
  { plaka: "18", slug: "cankiri", name: "Çankırı", center: [40.6013, 33.6134] },
  { plaka: "19", slug: "corum", name: "Çorum", center: [40.5506, 34.9556] },
  { plaka: "20", slug: "denizli", name: "Denizli", center: [37.7765, 29.0864] },
  { plaka: "21", slug: "diyarbakir", name: "Diyarbakır", center: [37.9144, 40.2306] },
  { plaka: "22", slug: "edirne", name: "Edirne", center: [41.6771, 26.5557] },
  { plaka: "23", slug: "elazig", name: "Elazığ", center: [38.681, 39.2264] },
  { plaka: "24", slug: "erzincan", name: "Erzincan", center: [39.75, 39.5] },
  { plaka: "25", slug: "erzurum", name: "Erzurum", center: [39.9, 41.27] },
  { plaka: "26", slug: "eskisehir", name: "Eskişehir", center: [39.7767, 30.5206] },
  { plaka: "27", slug: "gaziantep", name: "Gaziantep", center: [37.0662, 37.3833] },
  { plaka: "28", slug: "giresun", name: "Giresun", center: [40.9128, 38.3895] },
  { plaka: "29", slug: "gumushane", name: "Gümüşhane", center: [40.4603, 39.4814] },
  { plaka: "30", slug: "hakkari", name: "Hakkari", center: [37.5833, 43.7333] },
  { plaka: "31", slug: "hatay", name: "Hatay", center: [36.2021, 36.16] },
  { plaka: "32", slug: "isparta", name: "Isparta", center: [37.7648, 30.5566] },
  { plaka: "33", slug: "mersin", name: "Mersin", center: [36.8, 34.6333] },
  { plaka: "34", slug: "istanbul", name: "İstanbul", center: [41.0082, 28.9784] },
  { plaka: "35", slug: "izmir", name: "İzmir", center: [38.4237, 27.1428] },
  { plaka: "36", slug: "kars", name: "Kars", center: [40.6013, 43.0975] },
  { plaka: "37", slug: "kastamonu", name: "Kastamonu", center: [41.3887, 33.7827] },
  { plaka: "38", slug: "kayseri", name: "Kayseri", center: [38.7312, 35.4787] },
  { plaka: "39", slug: "kirklareli", name: "Kırklareli", center: [41.7333, 27.2167] },
  { plaka: "40", slug: "kirsehir", name: "Kırşehir", center: [39.1425, 34.1709] },
  { plaka: "41", slug: "kocaeli", name: "Kocaeli", center: [40.7654, 29.9408] },
  { plaka: "42", slug: "konya", name: "Konya", center: [37.8667, 32.4833] },
  { plaka: "43", slug: "kutahya", name: "Kütahya", center: [39.4167, 29.9833] },
  { plaka: "44", slug: "malatya", name: "Malatya", center: [38.3552, 38.3095] },
  { plaka: "45", slug: "manisa", name: "Manisa", center: [38.6191, 27.4289] },
  { plaka: "46", slug: "kahramanmaras", name: "Kahramanmaraş", center: [37.5858, 36.9371] },
  { plaka: "47", slug: "mardin", name: "Mardin", center: [37.3212, 40.7245] },
  { plaka: "48", slug: "mugla", name: "Muğla", center: [37.2153, 28.3636] },
  { plaka: "49", slug: "mus", name: "Muş", center: [38.9462, 41.7539] },
  { plaka: "50", slug: "nevsehir", name: "Nevşehir", center: [38.6244, 34.7144] },
  { plaka: "51", slug: "nigde", name: "Niğde", center: [37.9667, 34.6833] },
  { plaka: "52", slug: "ordu", name: "Ordu", center: [40.9839, 37.8764] },
  { plaka: "53", slug: "rize", name: "Rize", center: [41.0201, 40.5234] },
  { plaka: "54", slug: "sakarya", name: "Sakarya", center: [40.7569, 30.3783] },
  { plaka: "55", slug: "samsun", name: "Samsun", center: [41.2867, 36.33] },
  { plaka: "56", slug: "siirt", name: "Siirt", center: [37.9333, 41.95] },
  { plaka: "57", slug: "sinop", name: "Sinop", center: [42.0231, 35.1531] },
  { plaka: "58", slug: "sivas", name: "Sivas", center: [39.7477, 37.0179] },
  { plaka: "59", slug: "tekirdag", name: "Tekirdağ", center: [40.9833, 27.5167] },
  { plaka: "60", slug: "tokat", name: "Tokat", center: [40.3167, 36.55] },
  { plaka: "61", slug: "trabzon", name: "Trabzon", center: [41.0027, 39.7168] },
  { plaka: "62", slug: "tunceli", name: "Tunceli", center: [39.1079, 39.5401] },
  { plaka: "63", slug: "sanliurfa", name: "Şanlıurfa", center: [37.1591, 38.7969] },
  { plaka: "64", slug: "usak", name: "Uşak", center: [38.6823, 29.4082] },
  { plaka: "65", slug: "van", name: "Van", center: [38.4891, 43.4089] },
  { plaka: "66", slug: "yozgat", name: "Yozgat", center: [39.8181, 34.8147] },
  { plaka: "67", slug: "zonguldak", name: "Zonguldak", center: [41.4564, 31.7987] },
  { plaka: "68", slug: "aksaray", name: "Aksaray", center: [38.3687, 34.037] },
  { plaka: "69", slug: "bayburt", name: "Bayburt", center: [40.2552, 40.2249] },
  { plaka: "70", slug: "karaman", name: "Karaman", center: [37.1759, 33.2287] },
  { plaka: "71", slug: "kirikkale", name: "Kırıkkale", center: [39.8468, 33.5153] },
  { plaka: "72", slug: "batman", name: "Batman", center: [37.8812, 41.1351] },
  { plaka: "73", slug: "sirnak", name: "Şırnak", center: [37.5164, 42.4611] },
  { plaka: "74", slug: "bartin", name: "Bartın", center: [41.6344, 32.3375] },
  { plaka: "75", slug: "ardahan", name: "Ardahan", center: [41.1105, 42.7022] },
  { plaka: "76", slug: "igdir", name: "Iğdır", center: [39.9167, 44.0333] },
  { plaka: "77", slug: "yalova", name: "Yalova", center: [40.65, 29.2667] },
  { plaka: "78", slug: "karabuk", name: "Karabük", center: [41.2, 32.6333] },
  { plaka: "79", slug: "kilis", name: "Kilis", center: [36.7184, 37.1212] },
  { plaka: "80", slug: "osmaniye", name: "Osmaniye", center: [37.0742, 36.2478] },
  { plaka: "81", slug: "duzce", name: "Düzce", center: [40.8438, 31.1565] },
];
