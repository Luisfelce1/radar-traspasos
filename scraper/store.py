"""Lectura/escritura de datos (JSON en el repo; Git hace de base de datos e historial)."""
from __future__ import annotations

import json
from pathlib import Path

from .config import LISTINGS_FILE, STATE_FILE


def _load(path: Path, default):
    if path.exists() and path.stat().st_size:
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_listings() -> list[dict]:
    return _load(LISTINGS_FILE, [])


def save_listings(items: list[dict]) -> None:
    items = sorted(items, key=lambda x: (x.get("first_seen") or "", x["id"]), reverse=True)
    _save(LISTINGS_FILE, items)


def load_state() -> dict:
    return _load(STATE_FILE, {"skipped": {}, "runs": []})


def save_state(state: dict) -> None:
    state["runs"] = state.get("runs", [])[-50:]
    _save(STATE_FILE, state)
