"""HTTP educado: respeta robots.txt, Crawl-delay y deja pausas entre peticiones."""
from __future__ import annotations

import logging
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from .config import USER_AGENT

log = logging.getLogger(__name__)


class Fetcher:
    def __init__(self, min_delay: float = 3.0, timeout: float = 20.0):
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "es-ES,es;q=0.9"},
            follow_redirects=True,
            timeout=timeout,
        )
        self.min_delay = min_delay
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last_hit: dict[str, float] = {}
        self._delay: dict[str, float] = {}

    # ---------- robots.txt ----------
    def _robots_for(self, url: str) -> RobotFileParser | None:
        host = urlparse(url).netloc
        if host in self._robots:
            return self._robots[host]
        rp: RobotFileParser | None = RobotFileParser()
        try:
            r = self.client.get(f"https://{host}/robots.txt")
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            else:
                rp.parse([])  # sin robots.txt => todo permitido
        except httpx.HTTPError as e:
            log.warning("No se pudo leer robots.txt de %s: %s", host, e)
            rp = None
        self._robots[host] = rp
        crawl = None
        if rp is not None:
            crawl = rp.crawl_delay(USER_AGENT) or rp.crawl_delay("*")
        self._delay[host] = max(self.min_delay, float(crawl or 0))
        log.info("%s: pausa entre peticiones = %.1fs", host, self._delay[host])
        return rp

    def allowed(self, url: str) -> bool:
        rp = self._robots_for(url)
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def _wait(self, host: str) -> None:
        delay = self._delay.get(host, self.min_delay)
        elapsed = time.monotonic() - self._last_hit.get(host, 0)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_hit[host] = time.monotonic()

    # ---------- peticiones ----------
    def get(self, url: str, retries: int = 2) -> httpx.Response | None:
        """GET respetando robots y pausas. Devuelve la respuesta (también 404) o None si falla."""
        if not self.allowed(url):
            log.info("robots.txt no permite %s", url)
            return None
        host = urlparse(url).netloc
        for attempt in range(retries + 1):
            self._wait(host)
            try:
                r = self.client.get(url)
            except httpx.HTTPError as e:
                log.warning("Error %s (%s/%s): %s", url, attempt + 1, retries + 1, e)
                continue
            if r.status_code in (429, 503):
                wait = int(r.headers.get("Retry-After", "30") or 30)
                log.warning("%s devolvió %s, espero %ss", host, r.status_code, wait)
                time.sleep(min(wait, 120))
                continue
            return r
        return None

    def get_text(self, url: str) -> str | None:
        r = self.get(url)
        if r is None or r.status_code != 200:
            return None
        return r.text

    def close(self) -> None:
        self.client.close()
