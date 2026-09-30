"""Lectura de sitemaps (incluye sitemap index) para descubrir anuncios."""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def parse_sitemap(xml_text: str) -> tuple[list[str], list[tuple[str, str | None]]]:
    """Devuelve (sitemaps_hijos, [(url, lastmod)])."""
    root = ET.fromstring(xml_text.strip().encode("utf-8"))
    children, urls = [], []
    if root.tag == f"{NS}sitemapindex":
        for sm in root.findall(f"{NS}sitemap"):
            loc = sm.findtext(f"{NS}loc")
            if loc:
                children.append(loc.strip())
    else:
        for u in root.findall(f"{NS}url"):
            loc = u.findtext(f"{NS}loc")
            if loc:
                urls.append((loc.strip(), (u.findtext(f"{NS}lastmod") or "").strip() or None))
    return children, urls


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def discover(fetcher, source: dict) -> list[tuple[str, str | None]]:
    """URLs de fichas de una fuente, las más recientes primero."""
    pattern = re.compile(source["detail_regex"])
    max_age = source.get("max_age_days")
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age) if max_age else None

    queue, seen_maps, found = list(source["sitemaps"]), set(), {}
    while queue:
        sm_url = queue.pop(0)
        if sm_url in seen_maps or len(seen_maps) > 50:
            continue
        seen_maps.add(sm_url)
        text = fetcher.get_text(sm_url)
        if not text:
            log.warning("Sitemap vacío o inaccesible: %s", sm_url)
            continue
        try:
            children, urls = parse_sitemap(text)
        except ET.ParseError as e:
            log.warning("Sitemap mal formado %s: %s", sm_url, e)
            continue
        queue.extend(children)
        for url, lastmod in urls:
            if not pattern.match(url):
                continue
            if cutoff and (d := _parse_date(lastmod)) and d < cutoff:
                continue
            found[url.rstrip("/")] = lastmod

    items = sorted(found.items(), key=lambda kv: kv[1] or "", reverse=True)
    log.info("%s: %d fichas en sitemap", source["id"], len(items))
    return items
