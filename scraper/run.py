"""Pipeline completo: descubrir → descargar fichas nuevas → normalizar → deduplicar →
resumir → guardar → marcar caducados.

Uso:
  python -m scraper.run                      # ejecución normal (la que lanza GitHub Actions)
  python -m scraper.run --source bizalia     # solo una fuente
  python -m scraper.run --max-new 5 --dry-run
  python -m scraper.run discover negociosenventa   # lista URLs del sitemap (depuración)
  python -m scraper.run parse <url>                # parsea una ficha e imprime el resultado
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import logging
import re
import sys
from datetime import date, datetime, timedelta, timezone

from . import config
from .dedupe import exact_key, find_duplicate
from .fetch import Fetcher
from .normalize import (detect_sector, detect_tipo, find_provincia_in, is_foreign, match_comunidad,
                        match_provincia, parse_money, PROV_BY_SLUG, slugify)
from .sitemap import discover as sitemap_discover
from .store import load_listings, load_state, save_listings, save_state
from .summarize import summarize, ubicacion_label

log = logging.getLogger("scraper")
TODAY = date.today().isoformat()


def parser_for(source_id: str):
    return importlib.import_module(f"scraper.sources.{source_id}")


def discover(fetcher, source: dict) -> list[tuple[str, str | None]]:
    """Sitemap por defecto; si el módulo de la fuente define discover(), usa ese."""
    mod = parser_for(source["id"])
    return mod.discover(fetcher, source) if hasattr(mod, "discover") else sitemap_discover(fetcher, source)


def _int(text: str | None) -> int | None:
    m = re.search(r"\d[\d.]*", text or "")
    return int(m.group(0).replace(".", "")) if m else None


def build_listing(raw: dict, url: str, source: dict) -> dict:
    """Convierte lo extraído del portal en nuestro formato. Sin texto copiado."""
    title = (raw.get("title") or "").strip()[:160]
    provincia = match_provincia(raw.get("provincia_raw")) or find_provincia_in(title)
    comunidad = (PROV_BY_SLUG[provincia]["comunidad"] if provincia
                 else match_comunidad(raw.get("comunidad_raw")) or match_comunidad(raw.get("provincia_raw")))
    precio, precio_max = parse_money(raw.get("precio_raw"))
    facturacion, _ = parse_money(raw.get("facturacion_raw"))
    alquiler, _ = parse_money(raw.get("alquiler_raw"), minimum=100)
    short = hashlib.sha1(url.encode()).hexdigest()[:8]
    item = {
        "id": f"{source['id']}-{short}",
        "slug": f"{slugify(title, 60)}-{short}",
        "title": title,
        "tipo": detect_tipo(title, url),
        "sector": detect_sector(raw.get("sector_raw"), title),
        "provincia": provincia,
        "comunidad": comunidad,
        "ubicacion": ubicacion_label(provincia, comunidad),
        "municipio": raw.get("municipio"),
        "precio": precio,
        "precio_max": precio_max if precio_max and precio_max != precio else None,
        "facturacion": facturacion,
        "alquiler_mensual": alquiler,
        "superficie": _int(raw.get("superficie_raw")),
        "empleados": raw.get("empleados_raw"),
        "published": raw.get("published"),
        "source": source["id"],
        "source_name": source["name"],
        "url": url,
        "also_on": [],
        "first_seen": TODAY,
        "last_checked": TODAY,
        "status": "activo",
    }
    item["dedupe_key"] = exact_key(item)
    item["_foreign"] = is_foreign(raw.get("provincia_raw"))
    return item


def process_source(fetcher: Fetcher, source: dict, listings: list[dict], state: dict,
                   max_new: int | None = None, dry_run: bool = False) -> dict:
    stats = {"source": source["id"], "nuevos": 0, "duplicados": 0, "descartados": 0, "errores": 0, "retirados": 0}
    parser = parser_for(source["id"])
    discovered = discover(fetcher, source)
    in_sitemap = {u for u, _ in discovered}

    known = {x["url"] for x in listings} | {u for x in listings for u in x.get("also_on", [])}
    known |= set(state["skipped"])
    pending = [u for u, _ in discovered if u not in known]
    limit = max_new if max_new is not None else source["max_new_per_run"]
    log.info("%s: %d nuevas por procesar (límite %d)", source["id"], len(pending), limit)

    for url in pending[:limit]:
        html = fetcher.get_text(url)
        if not html:
            stats["errores"] += 1
            continue
        try:
            raw = parser.parse(html, url)
        except Exception as e:
            log.exception("Parser falló en %s: %s", url, e)
            stats["errores"] += 1
            continue
        item = build_listing(raw, url, source)

        reason = None
        if not item["title"]:
            reason = "sin_titulo"
        elif item.pop("_foreign"):
            reason = "extranjero"
        elif item["tipo"] in config.EXCLUDE_TIPOS:
            reason = item["tipo"]
        if reason:
            state["skipped"][url] = {"reason": reason, "date": TODAY}
            stats["descartados"] += 1
            continue

        dup = find_duplicate(item, listings)
        if dup:
            dup.setdefault("also_on", []).append(url)
            dup.setdefault("also_on_names", []).append(source["name"])
            stats["duplicados"] += 1
            continue

        item["summary"], item["summary_source"] = summarize(item, raw.get("description"))
        listings.append(item)
        stats["nuevos"] += 1
        log.info("  + %s | %s | %s | %s", item["tipo"], item["sector"], item["ubicacion"], item["title"][:60])

    stats["retirados"] = check_expired(fetcher, source, listings, in_sitemap, dry_run, parser)
    return stats


def check_expired(fetcher: Fetcher, source: dict, listings: list[dict], in_sitemap: set[str],
                  dry_run: bool = False, parser=None) -> int:
    """Si un anuncio desaparece del sitemap, se comprueba su URL; 404/410 o redirección fuera => retirado."""
    if not in_sitemap:  # sitemap caído: no tocamos nada
        return 0
    suspects = [x for x in listings if x["source"] == source["id"] and x["status"] == "activo"
                and x["url"] not in in_sitemap]
    suspects.sort(key=lambda x: x.get("last_checked") or "")
    retired = 0
    for x in suspects[: config.MAX_EXPIRY_CHECKS]:
        r = fetcher.get(x["url"])
        if r is None:
            continue
        final = str(r.url).rstrip("/")
        gone = r.status_code in (404, 410) or (r.status_code == 200 and final != x["url"].rstrip("/")
                                               and not re.match(source["detail_regex"], final))
        if not gone and r.status_code == 200 and parser is not None and hasattr(parser, "is_gone"):
            gone = parser.is_gone(r.text)
        x["last_checked"] = TODAY
        if gone and not dry_run:
            x["status"] = "retirado"
            x["retired_on"] = TODAY
            retired += 1
    return retired


def prune(listings: list[dict]) -> list[dict]:
    cutoff = (date.today() - timedelta(days=config.PRUNE_RETIRED_AFTER_DAYS)).isoformat()
    return [x for x in listings if not (x["status"] == "retirado" and (x.get("retired_on") or "") < cutoff)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="run", choices=["run", "discover", "parse"])
    ap.add_argument("arg", nargs="?", help="id de fuente (discover) o URL (parse)")
    ap.add_argument("--source", help="procesar solo esta fuente")
    ap.add_argument("--max-new", type=int, help="máximo de fichas nuevas por fuente")
    ap.add_argument("--dry-run", action="store_true", help="no guarda nada")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    for noisy in ("httpx", "httpcore", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    sources = {s["id"]: s for s in config.SOURCES}

    if args.command == "discover":
        src = sources[args.arg or next(iter(sources))]
        f = Fetcher(min_delay=src["delay"])
        for url, lastmod in discover(f, src)[:50]:
            print(lastmod, url)
        return 0

    if args.command == "parse":
        src = next((s for s in sources.values() if re.match(s["detail_regex"], args.arg or "")), None)
        if not src:
            print("La URL no encaja con ninguna fuente (revisa detail_regex en config.py)")
            return 1
        f = Fetcher(min_delay=1)
        html = f.get_text(args.arg)
        raw = parser_for(src["id"]).parse(html or "", args.arg)
        item = build_listing(raw, args.arg, src)
        raw["description"] = (raw.get("description") or "")[:120] + "…"
        print(json.dumps({"raw": raw, "listing": item}, ensure_ascii=False, indent=2))
        return 0

    listings = load_listings()
    state = load_state()
    run_stats = []
    for sid, src in sources.items():
        if args.source and sid != args.source:
            continue
        fetcher = Fetcher(min_delay=src["delay"])
        try:
            run_stats.append(process_source(fetcher, src, listings, state, args.max_new, args.dry_run))
        except Exception as e:  # una fuente rota no tumba a las demás
            log.exception("Fuente %s falló: %s", sid, e)
            run_stats.append({"source": sid, "error": str(e)})
        finally:
            fetcher.close()

    listings = prune(listings)
    log.info("Resumen: %s", run_stats)
    log.info("Total activos: %d", sum(1 for x in listings if x["status"] == "activo"))
    if args.dry_run:
        return 0
    state["runs"].append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "stats": run_stats})
    save_listings(listings)
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
