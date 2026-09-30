"""Parser de fichas de bizalia.com

Estructura observada (sept. 2026):
  <h1>Título</h1>
  "en-venta #108790 - Ofrecido desde el 30 de diciembre de 2024"
  bloques etiqueta/valor: Región, Sector, Tipo empresa, Tipo de transacción,
  Número de empleados, Facturación en el último ejercicio, Precio de venta,
  y un resumen lateral: Región, Sector, Facturación, Precio.
  Precio en rangos: '€ 250.000 - € 500.000'. Región puede ser comunidad o país.
  og:description contiene el primer bloque de la descripción.
URL: /en-venta/<id>/<slug>
"""
from __future__ import annotations

from .base import first_text, load, meta, parse_es_date, text_lines, value_after


def parse(html: str, url: str) -> dict:
    tree = load(html)
    lines = text_lines(tree)
    title = first_text(tree, "h1") or (meta(tree, "og:title") or "").split("|")[0].strip()
    ofrecido = next((ln for ln in lines if "Ofrecido desde" in ln), None)

    return {
        "title": title,
        "provincia_raw": value_after(lines, "Región", "Provincia", "Ubicación"),
        "municipio": None,
        "sector_raw": value_after(lines, "Sector"),
        "precio_raw": value_after(lines, "Precio de venta", "Precio"),
        "facturacion_raw": value_after(lines, "Facturación en el último ejercicio", "Facturación"),
        "alquiler_raw": None,
        "superficie_raw": None,
        "empleados_raw": value_after(lines, "Número de empleados"),
        "published": parse_es_date(ofrecido),
        "description": meta(tree, "og:description", "description"),
    }
