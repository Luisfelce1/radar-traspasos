"""Parser de fichas de negociosenventa.es

Estructura observada (sept. 2026):
  <h1>Título</h1>
  lista: #id · Provincia · Municipio · Barrio · CP
  "Publicado: dd/mm/aaaa"
  bloque de datos con etiquetas en mayúsculas: PUBLICADO, SECTOR, Nº EMPLEADOS,
  SUPERFÍCIE, VOLUMEN DE VENTA, ALQUILER, (PRECIO)
  La descripción está completa en <meta name="description">.
URL: /<slug>-en-<provincia>-<n>
"""
from __future__ import annotations

import re

from ..normalize import match_provincia
from .base import first_text, load, meta, parse_es_date, text_lines, value_after


def parse(html: str, url: str) -> dict:
    tree = load(html)
    lines = text_lines(tree)

    title = first_text(tree, "h1") or (meta(tree, "og:title") or "").split("|")[-1].strip()

    # Provincia: primero desde la URL (-en-<prov>-<n>), si no desde el texto
    provincia_raw = None
    m = re.search(r"-en-([a-z0-9-]+?)-\d+/?$", url)
    if m:
        provincia_raw = m.group(1)
    if not match_provincia(provincia_raw):
        # la línea que sigue a '#1234' suele ser la provincia
        for i, ln in enumerate(lines):
            if re.fullmatch(r"#\d+", ln) and i + 1 < len(lines):
                provincia_raw = lines[i + 1]
                break

    precio = value_after(lines, "PRECIO", "Precio", "PRECIO DE TRASPASO", "Precio traspaso")
    if not precio:
        # a veces el precio aparece suelto como 'NN.NNN€' tras la descripción
        for ln in lines:
            if re.fullmatch(r"[\d.\s]+ ?€", ln):
                precio = ln
                break

    return {
        "title": title,
        "provincia_raw": provincia_raw,
        "municipio": None,
        "sector_raw": value_after(lines, "SECTOR"),
        "precio_raw": precio,
        "facturacion_raw": value_after(lines, "VOLUMEN DE VENTA", "FACTURACIÓN", "FACTURACION"),
        "alquiler_raw": value_after(lines, "ALQUILER"),
        "superficie_raw": value_after(lines, "SUPERFÍCIE", "SUPERFICIE"),
        "empleados_raw": value_after(lines, "Nº EMPLEADOS", "N EMPLEADOS", "EMPLEADOS"),
        "published": parse_es_date(value_after(lines, "PUBLICADO") or next(
            (ln for ln in lines if ln.lower().startswith("publicado")), None)),
        # Solo para generar el resumen. NUNCA se guarda.
        "description": meta(tree, "description", "og:description"),
    }
