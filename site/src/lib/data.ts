// Acceso a datos y agregados. Todo se calcula en build (sitio 100% estático).
import raw from "../data/listings.json";

export type Listing = {
  id: string;
  slug: string;
  title: string;
  tipo: "traspaso" | "venta" | "alquiler";
  sector: string;
  provincia: string | null;
  comunidad: string | null;
  ubicacion: string | null;
  municipio?: string | null;
  precio: number | null;
  precio_max: number | null;
  facturacion: number | null;
  alquiler_mensual: number | null;
  superficie: number | null;
  empleados: string | null;
  published: string | null;
  source: string;
  source_name: string;
  url: string;
  also_on?: string[];
  also_on_names?: string[];
  first_seen: string;
  status: "activo" | "retirado";
  retired_on?: string;
  summary: string;
};

export const SECTORES: Record<string, string> = {
  online: "Negocio online",
  hosteleria: "Hostelería",
  alojamiento: "Hoteles y alojamiento",
  estetica: "Estética y peluquería",
  salud: "Salud y bienestar",
  alimentacion: "Alimentación",
  educacion: "Educación y formación",
  "deporte-ocio": "Deporte y ocio",
  comercio: "Comercio",
  transporte: "Transporte y logística",
  servicios: "Servicios",
  industria: "Industria y construcción",
  otros: "Otros negocios",
};

export const all = raw as Listing[];
export const active = all.filter((l) => l.status === "activo");

export const provincias = (() => {
  const m = new Map<string, string>();
  for (const l of active) if (l.provincia && l.ubicacion) m.set(l.provincia, l.ubicacion);
  return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1], "es"));
})();

export const byKey = <K extends keyof Listing>(key: K) => {
  const m = new Map<string, Listing[]>();
  for (const l of active) {
    const k = l[key] as string | null;
    if (!k) continue;
    if (!m.has(k)) m.set(k, []);
    m.get(k)!.push(l);
  }
  return m;
};

export const eur = (n: number | null | undefined) =>
  n == null ? null : new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);

export const priceLabel = (l: Listing) => {
  if (!l.precio) return "Precio a consultar";
  return l.precio_max ? `${eur(l.precio)} – ${eur(l.precio_max)}` : eur(l.precio)!;
};

export const tipoLabel = (t: string) => ({ traspaso: "Traspaso", venta: "Venta", alquiler: "Alquiler" })[t] ?? "Venta";

export function median(nums: number[]) {
  const s = nums.filter((n) => n > 0).sort((a, b) => a - b);
  if (!s.length) return null;
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : Math.round((s[mid - 1] + s[mid]) / 2);
}

/** Estadísticas propias: contenido original a partir de nuestros datos (bueno para SEO y AdSense). */
export function statsBy(key: "sector" | "provincia") {
  const groups = byKey(key);
  return [...groups.entries()]
    .map(([k, items]) => ({
      key: k,
      label: key === "sector" ? SECTORES[k] ?? k : items[0].ubicacion ?? k,
      count: items.length,
      medianPrice: median(items.map((i) => i.precio ?? 0)),
      traspasos: items.filter((i) => i.tipo === "traspaso").length,
    }))
    .sort((a, b) => b.count - a.count);
}
