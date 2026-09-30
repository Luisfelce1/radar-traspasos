"""Utilidades comunes para parsers: líneas de texto visibles, etiquetas → valor, metadatos."""
from __future__ import annotations

import re

from selectolax.parser import HTMLParser

from ..normalize import fold

_SKIP_TAGS = ["script", "style", "noscript", "svg", "iframe", "form", "nav", "footer", "header"]


def load(html: str) -> HTMLParser:
    return HTMLParser(html)


def text_lines(tree: HTMLParser, root_selector: str = "body") -> list[str]:
    """Texto visible partido en líneas limpias. Robusto a cambios de clases CSS."""
    node = tree.css_first(root_selector) or tree.body
    if node is None:
        return []
    clone = HTMLParser(node.html)
    for tag in _SKIP_TAGS:
        for n in clone.css(tag):
            n.decompose()
    raw = clone.body.text(separator="\n") if clone.body else ""
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw.split("\n")]
    return [ln for ln in lines if ln]


def value_after(lines: list[str], *labels: str, max_gap: int = 2) -> str | None:
    """Devuelve el texto que sigue a una etiqueta ('Precio', 'SECTOR', 'Precio:').
    Busca la primera aparición y toma la siguiente línea no vacía (o el resto de la misma línea)."""
    wanted = {fold(lb) for lb in labels}
    for i, ln in enumerate(lines):
        f = fold(ln)
        if f in wanted:
            for nxt in lines[i + 1 : i + 1 + max_gap]:
                if fold(nxt) not in wanted:
                    return nxt
        for lb in labels:  # 'Precio: 25.000 €' en la misma línea
            m = re.match(rf"^\s*{re.escape(lb)}\s*:\s*(.+)$", ln, flags=re.I)
            if m:
                return m.group(1).strip()
    return None


def meta(tree: HTMLParser, *names: str) -> str | None:
    for name in names:
        n = tree.css_first(f'meta[property="{name}"]') or tree.css_first(f'meta[name="{name}"]')
        if n and (c := n.attributes.get("content")):
            return re.sub(r"\s+", " ", c).strip()
    return None


def first_text(tree: HTMLParser, selector: str) -> str | None:
    n = tree.css_first(selector)
    return re.sub(r"\s+", " ", n.text()).strip() if n else None


def parse_es_date(s: str | None) -> str | None:
    """'20/06/2025' o '30 de diciembre de 2024' -> '2025-06-20'."""
    if not s:
        return None
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
             "octubre", "noviembre", "diciembre"]
    m = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", fold(s))
    if m and m.group(2) in meses:
        return f"{m.group(3)}-{meses.index(m.group(2)) + 1:02d}-{int(m.group(1)):02d}"
    return None
