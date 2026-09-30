// Tipos y utilidades compartidas por los componentes Angular (volt-ui).

/** Fila compacta del índice /listings-index.json (claves cortas para pesar poco). */
export interface Row {
  s: string; // slug
  t: string; // título
  k: string; // tipo: traspaso | venta | alquiler
  c: string; // sector (slug)
  p: string; // provincia (slug) o ''
  u: string; // ubicación legible o ''
  e: number; // precio (0 = a consultar)
  m: number; // precio máximo (0 = sin rango)
  y: string; // resumen corto
  o: string; // portal de origen
  f: string; // visto por primera vez (YYYY-MM-DD)
}

export interface Filters {
  q: string;
  sector: string;
  provincia: string;
  tipo: string;
  max: number;
}

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

export const SECTOR_ICON: Record<string, string> = {
  online: "💻", hosteleria: "☕", alojamiento: "🛏️", estetica: "💇", salud: "🩺", alimentacion: "🥖",
  educacion: "🎓", "deporte-ocio": "🏋️", comercio: "🛍️", transporte: "🚚", servicios: "🧰",
  industria: "🏭", otros: "📦",
};

export const TIPOS: Record<string, string> = { traspaso: "Traspaso", venta: "Venta", alquiler: "Alquiler" };

const fmt = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
export const eur = (n: number | null | undefined) => (n ? fmt.format(n) : "");

export function priceLabel(r: Pick<Row, "e" | "m">): string {
  if (!r.e) return "Precio a consultar";
  return r.m ? `${eur(r.e)} – ${eur(r.m)}` : eur(r.e);
}

export const fold = (s: string) =>
  (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Fisher–Yates: orden aleatorio distinto en cada visita. */
export function shuffle<T>(arr: T[]): T[] {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function matches(r: Row, f: Filters): boolean {
  if (f.sector && r.c !== f.sector) return false;
  if (f.provincia && r.p !== f.provincia) return false;
  if (f.tipo && r.k !== f.tipo) return false;
  if (f.max && (!r.e || r.e > f.max)) return false;
  if (f.q) {
    const hay = fold(`${r.t} ${SECTORES[r.c] ?? ""} ${r.u} ${r.y}`);
    return fold(f.q).split(/\s+/).filter(Boolean).every((w) => hay.includes(w));
  }
  return true;
}
