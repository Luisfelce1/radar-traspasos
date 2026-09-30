"""Deduplicación: el mismo negocio suele anunciarse en varios portales."""
from __future__ import annotations

import hashlib

from rapidfuzz import fuzz

from .normalize import fold

# Palabras que no ayudan a distinguir anuncios
_STOP = {"se", "vende", "venta", "traspasa", "traspaso", "de", "en", "el", "la", "los", "las", "por", "con",
         "y", "a", "un", "una", "negocio", "oportunidad", "unica", "pleno", "funcionamiento"}


def core_title(title: str) -> str:
    return " ".join(w for w in fold(title).split() if w not in _STOP)


def exact_key(item: dict) -> str:
    raw = f"{core_title(item['title'])}|{item.get('precio') or ''}|{item.get('provincia') or ''}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _price_close(a: int | None, b: int | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= 0.05 * max(a, b)


def find_duplicate(item: dict, existing: list[dict], threshold: int = 90) -> dict | None:
    key = exact_key(item)
    t = core_title(item["title"])
    for other in existing:
        if other.get("status") != "activo":
            continue
        if other.get("dedupe_key") == key:
            return other
        if other.get("source") == item.get("source"):
            continue  # dentro del mismo portal confiamos en la URL
        if (item.get("provincia") or item.get("comunidad")) != (other.get("provincia") or other.get("comunidad")):
            continue
        if not _price_close(item.get("precio"), other.get("precio")):
            continue
        if len(t) >= 8 and fuzz.token_set_ratio(t, core_title(other["title"])) >= threshold:
            return other
    return None
