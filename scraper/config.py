"""Configuración central. Todo lo ajustable está aquí."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Donde vive cada cosa
LISTINGS_FILE = ROOT / "site" / "src" / "data" / "listings.json"  # lo que publica la web
STATE_FILE = ROOT / "data" / "state.json"                          # URLs descartadas, etc.

# Identifícate siempre. Cambia la URL por tu dominio cuando lo tengas.
SITE_URL = os.getenv("SITE_URL") or "https://example.pages.dev"
USER_AGENT = f"TraspasosBot/1.0 (+{SITE_URL}/bot)"

# Resúmenes con IA (solo si existe la variable ANTHROPIC_API_KEY)
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL") or "claude-haiku-4-5"

# Tipos de anuncio que NO publicamos (compradores buscando, pisos/solares sueltos)
EXCLUDE_TIPOS = {"busqueda", "inmueble"}

# Anuncios retirados: se quitan del JSON pasados estos días
PRUNE_RETIRED_AFTER_DAYS = 180

# Máximo de comprobaciones de caducidad por fuente y ejecución
MAX_EXPIRY_CHECKS = 30

# Fuentes. Para añadir una: crea scraper/sources/<id>.py con parse() y añádela aquí.
SOURCES = [
    {
        "id": "negociosenventa",
        "name": "NegociosEnVenta.es",
        "base": "https://www.negociosenventa.es",
        "sitemaps": ["https://www.negociosenventa.es/sitemap.xml"],
        # Fichas: una sola ruta que acaba en -<número>
        "detail_regex": r"^https://www\.negociosenventa\.es/[a-z0-9-]+-\d+/?$",
        "delay": 3.0,          # segundos entre peticiones (mínimo; robots.txt manda si pide más)
        "max_new_per_run": int(os.getenv("MAX_NEW_NEGOCIOSENVENTA", "60")),
        "max_age_days": None,  # su sitemap refresca lastmod a diario, no sirve para filtrar
    },
    {
        "id": "bizalia",
        "name": "Bizalia",
        "base": "https://www.bizalia.com",
        "sitemaps": ["https://www.bizalia.com/sitemap-actieve-profielen.xml"],
        # Solo vendedores (/en-venta/), no compradores (/compradores/)
        "detail_regex": r"^https://www\.bizalia\.com/en-venta/\d+/[a-z0-9-]+/?$",
        "delay": 10.0,         # su robots.txt pide Crawl-delay: 10
        "max_new_per_run": int(os.getenv("MAX_NEW_BIZALIA", "30")),
        "max_age_days": 365,   # su sitemap arrastra anuncios de 2019
    },
    {
        "id": "transmisionempresas",
        "name": "Transmisión de Empresas (Ministerio)",
        "base": "https://transmisionempresas.circe.es",
        "sitemaps": [],        # no tiene: se descubre con el buscador (Playwright)
        "detail_regex": r"^https://transmisionempresas\.circe\.es/Portal/Anuncio/Index/[A-Za-z0-9%+/=_-]+$",
        "delay": 3.0,
        "max_pages": int(os.getenv("MAX_PAGES_TRANSMISION", "15")),  # páginas del buscador por ejecución
        "max_new_per_run": int(os.getenv("MAX_NEW_TRANSMISION", "40")),
        "max_age_days": None,
    },
]
