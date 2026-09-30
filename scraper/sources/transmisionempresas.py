"""Bolsa pública del Plan de Apoyo a la Transmisión de Empresas (Ministerio de Industria).

- Sin robots.txt ni sitemap.
- El buscador (/Portal/Busqueda/Index) carga los resultados con JavaScript, así que el
  descubrimiento usa un navegador sin interfaz (Playwright): abre el buscador, pulsa Buscar
  y recoge los enlaces /Portal/Anuncio/Index/<id> página a página.
- Las fichas son HTML normal y se leen con httpx como el resto.

Estructura de la ficha observada (sept. 2026), pares etiqueta/valor:
  Forma Jurídica, Precio de Venta ('Precio no especificado' o importe), Motivación venta,
  Año de Constitución, Número Socios, Número Trabajadores, Local, Sector Principal,
  Actividad Principal, Ubicación ('COMUNIDAD DE MADRID, MADRID, FUENLABRADA'),
  Visualizaciones, Fecha de Publicación (formato MM/DD/AAAA), ...
Sin meta description: la descripción es el bloque de texto bajo el título.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from .base import first_text, load, text_lines, value_after

log = logging.getLogger(__name__)

BASE = "https://transmisionempresas.circe.es"
SEARCH_URL = f"{BASE}/Portal/Busqueda/Index"

LABELS = ["Forma Jurídica", "Precio de Venta", "Motivación venta", "Año de Constitución", "Número Socios",
          "Número Trabajadores", "Local", "Sector Principal", "Actividad Principal", "Ubicación",
          "Visualizaciones", "Fecha de Publicación", "Número de veces señalado como favorito",
          "Número veces Solicitado"]
def _clean(v: str | None) -> str | None:
    if v is None or v.strip() in LABELS or v.strip() in ("", "-"):
        return None
    if re.search(r"no especificad|sin especificar", v, re.I):
        return None
    return v.strip()


def _date_mdy(s: str | None) -> str | None:
    """La web publica 10/17/2024 (MM/DD/AAAA). Si el primer número >12, es DD/MM."""
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
    if not m:
        return None
    a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
    month, day = (b, a) if a > 12 else (a, b)
    return f"{y}-{month:02d}-{day:02d}"


def _description(lines: list[str], title: str) -> str | None:
    """Texto entre el título (su última aparición) y la primera etiqueta de datos."""
    try:
        start = max(i for i, ln in enumerate(lines) if ln == title) + 1
    except ValueError:
        start = 0
    end = next((i for i in range(start, len(lines)) if lines[i] in LABELS), len(lines))
    text = " ".join(lines[start:end]).strip()
    if len(text) < 60:  # estructura distinta: usa el párrafo más largo
        text = max(lines, key=len, default="")
    return text[:3000] or None


def parse(html: str, url: str) -> dict:
    tree = load(html)
    lines = text_lines(tree)
    title = (first_text(tree, "h1") or first_text(tree, "h2") or "").strip()
    # Títulos en MAYÚSCULAS: los pasamos a formato frase
    if title and title.isupper():
        title = title.capitalize()

    ubic = _clean(value_after(lines, "Ubicación")) or ""
    parts = [p.strip() for p in ubic.split(",") if p.strip()]
    # 'CCAA, PROVINCIA, MUNICIPIO'
    provincia_raw = parts[1] if len(parts) >= 2 else (parts[0] if parts else None)
    municipio = parts[2].title() if len(parts) >= 3 else None

    sector = _clean(value_after(lines, "Sector Principal"))
    actividad = _clean(value_after(lines, "Actividad Principal"))
    raw_title = first_text(tree, "h1") or ""
    return {
        "title": title,
        "provincia_raw": provincia_raw,
        "comunidad_raw": parts[0] if parts else None,
        "municipio": municipio,
        # la actividad es más específica que el sector; se prueba primero
        "sector_raw": " / ".join(x for x in (actividad, sector) if x) or None,
        "precio_raw": _clean(value_after(lines, "Precio de Venta")),
        "facturacion_raw": _clean(value_after(lines, "Facturación", "Volumen de Negocio")),
        "alquiler_raw": None,
        "superficie_raw": None,
        "empleados_raw": _clean(value_after(lines, "Número Trabajadores")),
        "published": _date_mdy(value_after(lines, "Fecha de Publicación")),
        "description": _description(lines, raw_title.strip()),
    }


def is_gone(html: str) -> bool:
    """Anuncio dado de baja: la página responde 200 pero sin ficha."""
    tree = load(html)
    if not (first_text(tree, "h1") or "").strip():
        return True
    lines = text_lines(tree)
    return "Precio de Venta" not in lines and "Ubicación" not in lines


# ------------------------------------------------------------------ descubrimiento

_NEXT_SELECTORS = [
    "a[aria-label*='Siguiente' i]", "a[title*='Siguiente' i]", "a:has-text('Siguiente')",
    "li.next:not(.disabled) a", ".pagination li:not(.disabled) a:has-text('»')",
    ".pagination li:not(.disabled) a:has-text('>')", "a.paginate_button.next:not(.disabled)",
]
_SEARCH_BUTTONS = ["button:has-text('Buscar')", "input[type=submit][value*='Buscar' i]",
                   "a:has-text('Buscar')", "button[type=submit]"]


def discover(fetcher, source: dict) -> list[tuple[str, str | None]]:
    """Abre el buscador con Chromium sin interfaz y recoge las fichas.
    Devuelve [(url, None)]. Si Playwright no está instalado, devuelve [] y avisa."""
    try:
        from playwright.sync_api import TimeoutError as PWTimeout
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("transmisionempresas: Playwright no instalado; se omite esta fuente "
                    "(pip install playwright && python -m playwright install chromium)")
        return []

    from ..config import USER_AGENT

    max_pages = source.get("max_pages", 15)
    delay_ms = int(source.get("delay", 3) * 1000)
    found: dict[str, None] = {}

    def collect(page) -> int:
        before = len(found)
        for href in page.eval_on_selector_all("a[href*='/Portal/Anuncio/']", "els => els.map(e => e.href)"):
            url = urljoin(source.get("base", BASE) + "/", href).split("#")[0]
            if re.match(source["detail_regex"], url):
                found[url] = None
        return len(found) - before

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=USER_AGENT, locale="es-ES")
        try:
            page.goto(source.get("search_url", SEARCH_URL), wait_until="networkidle", timeout=60_000)
            if not collect(page):  # sin resultados iniciales: lanza la búsqueda vacía
                for sel in _SEARCH_BUTTONS:
                    btn = page.locator(sel).first
                    if btn.count() and btn.is_visible():
                        btn.click()
                        break
                try:
                    page.wait_for_selector("a[href*='/Portal/Anuncio/']", timeout=30_000)
                except PWTimeout:
                    log.warning("transmisionempresas: el buscador no devolvió enlaces a fichas. "
                                "Revisa _SEARCH_BUTTONS en este archivo.")
                collect(page)

            for n in range(2, max_pages + 1):
                nxt = next((page.locator(s).first for s in _NEXT_SELECTORS
                            if page.locator(s).first.count() and page.locator(s).first.is_visible()), None)
                if nxt is None:
                    break
                page.wait_for_timeout(delay_ms)  # pausa educada entre páginas
                first = page.eval_on_selector("a[href*='/Portal/Anuncio/']", "e => e.href")
                nxt.click()
                try:  # espera a que la lista cambie (recarga completa o AJAX)
                    page.wait_for_function(
                        "f => { const a = document.querySelector(\"a[href*='/Portal/Anuncio/']\");"
                        " return a && a.href !== f; }", arg=first, timeout=30_000)
                except PWTimeout:
                    break
                if collect(page) == 0:
                    break
                log.info("transmisionempresas: página %d, %d fichas", n, len(found))
        except Exception as e:
            log.warning("transmisionempresas: fallo en el buscador (%s); uso lo recogido", e)
        finally:
            browser.close()

    log.info("transmisionempresas: %d fichas en el buscador", len(found))
    return list(found.items())
