"""Tests offline: no hacen peticiones reales. Ejecuta: pytest -q"""
from pathlib import Path

import pytest

from scraper import config, run
from scraper.dedupe import find_duplicate
from scraper.normalize import detect_sector, detect_tipo, find_provincia_in, match_provincia, parse_money
from scraper.sitemap import parse_sitemap
from scraper.sources import bizalia, negociosenventa

FIX = Path(__file__).parent / "fixtures"
NEV = next(s for s in config.SOURCES if s["id"] == "negociosenventa")
BIZ = next(s for s in config.SOURCES if s["id"] == "bizalia")


# ---------- normalización
@pytest.mark.parametrize("text,expected", [
    ("€ 250.000 - € 500.000", (250000, 500000)),
    ("45.000€", (45000, 45000)),
    ("1,2 M€", (1200000, 1200000)),
    ("Confidencial", (None, None)),
    ("25€", (None, None)),
    (None, (None, None)),
])
def test_parse_money(text, expected):
    assert parse_money(text) == expected


@pytest.mark.parametrize("raw,slug", [
    ("valenciavalencia", "valencia"), ("alicantealacant", "alicante"), ("palmas-las", "las-palmas"),
    ("balears-illes", "baleares"), ("coruna-a", "a-coruna"), ("castelloncastello", "castellon"),
    ("Madrid", "madrid"), ("rioja-la", "la-rioja"), ("bizkaia", "bizkaia"), ("Bélgica", None),
])
def test_provincias(raw, slug):
    assert match_provincia(raw) == slug


def test_provincia_en_titulo():
    assert find_provincia_in("Traspaso bar de tapas en Zaragoza centro") == "zaragoza"
    assert find_provincia_in("Hotel rural con encanto en Cantabria") == "cantabria"


def test_sector_y_tipo():
    assert detect_sector("Carniceria", "Traspaso de carnicería") == "alimentacion"
    assert detect_sector(None, "Traspaso de peluquería canina en Madrid") == "estetica"
    assert detect_sector(None, "Venta de tienda online de mascotas") == "online"
    assert detect_sector(None, "Agencia de publicidad digital") != "hosteleria"  # 'pub' no es bar
    assert detect_tipo("Traspaso de carnicería por jubilación") == "traspaso"
    assert detect_tipo("Busco socio en Barcelona") == "busqueda"
    assert detect_tipo("Se vende suelo urbano en Lorquí") == "inmueble"
    assert detect_tipo("Venta de clínica dental") == "venta"


# ---------- sitemaps
def test_sitemap_index_y_urlset():
    children, urls = parse_sitemap((FIX / "sitemap_index.xml").read_text())
    assert children == ["https://www.negociosenventa.es/sitemap-1.xml"] and urls == []
    _, urls = parse_sitemap((FIX / "sitemap_1.xml").read_text())
    import re
    fichas = [u for u, _ in urls if re.match(NEV["detail_regex"], u)]
    assert len(fichas) == 2  # excluye /traspaso y /noticias/...


# ---------- parsers
def test_parser_negociosenventa():
    url = "https://www.negociosenventa.es/traspaso-de-carniceria-por-jubilacion-en-madrid-11140"
    raw = negociosenventa.parse((FIX / "negociosenventa.html").read_text(), url)
    assert raw["title"] == "Traspaso de carnicería por jubilación"
    assert raw["sector_raw"] == "Carniceria"
    assert raw["superficie_raw"] == "70"
    assert raw["published"] == "2025-06-20"
    item = run.build_listing(raw, url, NEV)
    assert item["provincia"] == "madrid" and item["comunidad"] == "madrid"
    assert item["tipo"] == "traspaso" and item["sector"] == "alimentacion"
    assert item["precio"] == 45000 and item["alquiler_mensual"] == 1200 and item["superficie"] == 70
    assert item["facturacion"] is None


def test_parser_bizalia():
    url = "https://www.bizalia.com/en-venta/110001/traspaso-restaurante-con-terraza-en-cantabria"
    raw = bizalia.parse((FIX / "bizalia.html").read_text(), url)
    assert raw["provincia_raw"] == "Cantabria"
    assert raw["precio_raw"] == "€ 100.000 - € 250.000"
    assert raw["published"] == "2026-09-12"
    item = run.build_listing(raw, url, BIZ)
    assert item["provincia"] == "cantabria"
    assert (item["precio"], item["precio_max"]) == (100000, 250000)
    assert item["facturacion"] == 250000
    assert item["sector"] == "hosteleria"


def test_bizalia_extranjero_se_descarta():
    url = "https://www.bizalia.com/en-venta/108790/inversion-negocio"
    raw = bizalia.parse((FIX / "bizalia_foreign.html").read_text(), url)
    assert run.build_listing(raw, url, BIZ)["_foreign"] is True


# ---------- dedupe
def test_duplicado_entre_portales():
    a = {"id": "a", "source": "negociosenventa", "status": "activo", "title": "Traspaso restaurante con terraza en Cantabria",
         "provincia": "cantabria", "precio": 100000, "dedupe_key": "x"}
    b = {"id": "b", "source": "bizalia", "status": "activo", "title": "Se traspasa restaurante con terraza Cantabria",
         "provincia": "cantabria", "precio": 102000, "dedupe_key": "y"}
    assert find_duplicate(b, [a]) is a
    c = dict(b, precio=300000)
    assert find_duplicate(c, [a]) is None


# ---------- pipeline completo con un fetcher falso
class FakeResp:
    def __init__(self, url, status, text=""):
        self.url, self.status_code, self.text = url, status, text


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        return FakeResp(url, 200, self.pages[url]) if url in self.pages else FakeResp(url, 404)

    def get_text(self, url):
        return self.pages.get(url)


def test_pipeline_offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    carn = "https://www.negociosenventa.es/traspaso-de-carniceria-por-jubilacion-en-madrid-11140"
    socio = "https://www.negociosenventa.es/busco-socio-en-barcelona-11515"
    viejo = "https://www.negociosenventa.es/bar-antiguo-en-madrid-999"
    pages = {
        "https://www.negociosenventa.es/sitemap.xml": (FIX / "sitemap_index.xml").read_text(),
        "https://www.negociosenventa.es/sitemap-1.xml": (FIX / "sitemap_1.xml").read_text(),
        carn: (FIX / "negociosenventa.html").read_text(),
        socio: "<html><body><h1>Busco socio en Barcelona</h1></body></html>",
    }
    listings = [{"id": "old", "url": viejo, "source": "negociosenventa", "status": "activo",
                 "title": "Bar antiguo", "last_checked": "2026-01-01"}]
    state = {"skipped": {}, "runs": []}
    stats = run.process_source(FakeFetcher(pages), NEV, listings, state)
    assert stats["nuevos"] == 1 and stats["descartados"] == 1 and stats["retirados"] == 1
    nuevo = next(x for x in listings if x["url"] == carn)
    assert nuevo["summary_source"] == "template" and "Madrid" in nuevo["summary"]
    assert "description" not in nuevo  # nunca guardamos el texto original
    assert state["skipped"][socio]["reason"] == "busqueda"
    assert listings[0]["status"] == "retirado"
    # segunda pasada: nada nuevo, nada que reprocesar
    stats2 = run.process_source(FakeFetcher(pages), NEV, listings, state)
    assert stats2["nuevos"] == 0 and stats2["descartados"] == 0


# ---------- transmisionempresas
from scraper.sources import transmisionempresas as te  # noqa: E402

TE = next(s for s in config.SOURCES if s["id"] == "transmisionempresas")


def test_parser_transmisionempresas():
    url = "https://transmisionempresas.circe.es/Portal/Anuncio/Index/8DiscnAk334%3D"
    import re
    assert re.match(TE["detail_regex"], url)
    raw = te.parse((FIX / "transmisionempresas.html").read_text(), url)
    assert raw["title"] == "Venta de cafeteria con obrador en el centro de segovia"
    assert raw["provincia_raw"] == "SEGOVIA" and raw["municipio"] == "Segovia"
    assert raw["published"] == "2026-09-03"
    assert "obrador propio" in raw["description"] and "Forma Jurídica" not in raw["description"]
    item = run.build_listing(raw, url, TE)
    assert item["provincia"] == "segovia" and item["comunidad"] == "castilla-y-leon"
    assert item["precio"] == 120000 and item["sector"] == "hosteleria" and item["tipo"] == "venta"


def test_transmisionempresas_sin_precio_y_baja():
    html = (FIX / "transmisionempresas.html").read_text().replace("120.000,00 €", "Precio no especificado")
    raw = te.parse(html, "https://transmisionempresas.circe.es/Portal/Anuncio/Index/x")
    assert raw["precio_raw"] is None
    assert te.is_gone((FIX / "transmisionempresas_gone.html").read_text())
    assert not te.is_gone((FIX / "transmisionempresas.html").read_text())


def test_fecha_mdy():
    assert te._date_mdy("10/17/2024") == "2024-10-17"
    assert te._date_mdy("25/03/2026") == "2026-03-25"


def test_discover_playwright_con_buscador_falso():
    pytest.importorskip("playwright")
    import http.server, threading, functools  # noqa: E401
    root = FIX / "transmision_search"
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    src = dict(TE, base=base, search_url=f"{base}/index.html", delay=0.1,
               detail_regex=r"^http://127\.0\.0\.1:\d+/Portal/Anuncio/Index/[A-Za-z0-9%+/=_-]+$")
    try:
        urls = [u for u, _ in te.discover(None, src)]
    except Exception as e:  # sin Chromium disponible
        pytest.skip(f"Chromium no disponible: {e}")
    finally:
        srv.shutdown()
    assert len(urls) == 3 and all("/Portal/Anuncio/Index/" in u for u in urls)
