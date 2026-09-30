import type { APIRoute } from "astro";
import { active, toRow } from "../lib/data";

// Índice compacto que usa el explorador en el navegador (se baraja en cada visita).
export const GET: APIRoute = () =>
  new Response(JSON.stringify(active.map(toRow)), { headers: { "Content-Type": "application/json" } });
