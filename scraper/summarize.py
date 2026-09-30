"""Resumen propio de cada anuncio.

- Con ANTHROPIC_API_KEY: Claude escribe 2 frases originales a partir de la descripción.
- Sin clave: plantilla con los datos estructurados.
La descripción original se usa solo como entrada y no se guarda en ningún sitio.
"""
from __future__ import annotations

import logging
import os

from .config import ANTHROPIC_MODEL
from .normalize import SECTOR_NAMES, TIPO_NAMES, PROV_BY_SLUG, COMUNIDADES

log = logging.getLogger(__name__)

PROMPT = """Eres redactor de un buscador de negocios en traspaso en España.
Escribe un resumen ORIGINAL de 2 frases (máximo 260 caracteres) del anuncio de abajo, en español neutro.
Reglas:
- Con tus propias palabras. No copies frases del anuncio.
- Solo datos que aparezcan en el anuncio. No inventes cifras.
- Sin teléfonos, emails, nombres de personas ni llamadas a la acción.
- Sin comillas ni emojis. Devuelve solo el resumen.

Título: {title}
Ubicación: {ubicacion}
Anuncio:
{description}"""

_client = None


def _get_client():
    global _client
    if _client is None and os.getenv("ANTHROPIC_API_KEY"):
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def _fmt_eur(n: int | None) -> str | None:
    return f"{n:,.0f} €".replace(",", ".") if n else None


def template_summary(item: dict) -> str:
    tipo = TIPO_NAMES.get(item.get("tipo"), "Venta")
    sector = SECTOR_NAMES.get(item.get("sector"), "negocio").lower()
    lugar = item.get("ubicacion") or "España"
    parts = [f"{tipo} de negocio de {sector} en {lugar}."]
    if p := _fmt_eur(item.get("precio")):
        parts.append(f"Precio desde {p}.")
    if f := _fmt_eur(item.get("facturacion")):
        parts.append(f"Facturación declarada: {f}.")
    if s := item.get("superficie"):
        parts.append(f"Superficie aproximada de {s} m².")
    return " ".join(parts)


def summarize(item: dict, description: str | None) -> tuple[str, str]:
    """Devuelve (resumen, origen) con origen 'ai' o 'template'."""
    client = _get_client()
    if client and description and len(description) > 60:
        try:
            msg = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=200,
                messages=[{"role": "user", "content": PROMPT.format(
                    title=item["title"], ubicacion=item.get("ubicacion") or "España",
                    description=description[:3000])}],
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
            if 40 < len(text) <= 400:
                return text, "ai"
        except Exception as e:  # la IA es opcional: nunca rompe el pipeline
            log.warning("Resumen IA falló (%s), uso plantilla", e)
    return template_summary(item), "template"


def ubicacion_label(provincia: str | None, comunidad: str | None) -> str | None:
    if provincia and provincia in PROV_BY_SLUG:
        return PROV_BY_SLUG[provincia]["nombre"]
    if comunidad:
        return COMUNIDADES.get(comunidad)
    return None
