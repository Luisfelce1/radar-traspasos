import type { APIRoute } from "astro";
import { active, SECTORES } from "../lib/data";

// Índice compacto para el buscador del navegador.
export const GET: APIRoute = () => {
  const rows = active.map((l) => [
    l.slug, l.title, l.tipo, l.sector, SECTORES[l.sector] ?? "", l.provincia ?? "", l.ubicacion ?? "",
    l.precio ?? 0, l.precio_max ?? 0, l.first_seen,
  ]);
  return new Response(JSON.stringify(rows), { headers: { "Content-Type": "application/json" } });
};
