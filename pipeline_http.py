"""Respectful HTTP helper for station discovery.

Used only for DISCOVERY/metadata scraping of official portals. Actual data
acquisition stays on the official ``fluxnet-shuttle`` path. This helper never
evades rate limits or authentication.

Features:
    * Descriptive User-Agent.
    * robots.txt gate per host (``urllib.robotparser``).
    * Minimum inter-request delay per host.
    * Retries with exponential backoff honoring ``Retry-After`` on 429/5xx.
    * On-disk response cache under ``research/.http_cache/``.
    * ``offline`` mode that serves only from cache / fixtures.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests

from pipeline_paths import RESEARCH_DIR

USER_AGENT = (
    "austral-breathing/1.0 (ecosystem research; "
    "+https://github.com/djwillichile/austral-breathing; "
    "contact: guillermo.f1990@gmail.com)"
)

CACHE_DIR = RESEARCH_DIR / ".http_cache"


@dataclass
class FetchResult:
    url: str
    status: int
    text: str
    from_cache: bool
    robots_blocked: bool = False


@dataclass
class RespectfulHttpClient:
    """A polite HTTP client with caching, rate limiting and robots.txt checks."""

    min_delay_seconds: float = 3.0
    max_retries: int = 4
    cache_ttl_seconds: int = 7 * 24 * 3600
    offline: bool = False
    respect_robots: bool = True
    timeout: float = 30.0

    _session: requests.Session = field(default_factory=requests.Session, init=False, repr=False)
    _last_request_at: dict[str, float] = field(default_factory=dict, init=False, repr=False)
    _robots: dict[str, urllib.robotparser.RobotFileParser] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self._session.headers.update({"User-Agent": USER_AGENT})
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # -- cache -----------------------------------------------------------
    def _cache_file(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        return CACHE_DIR / f"{digest}.json"

    def _read_cache(self, url: str) -> FetchResult | None:
        path = self._cache_file(url)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        age = time.time() - payload.get("fetched_at", 0)
        if not self.offline and age > self.cache_ttl_seconds:
            return None
        return FetchResult(
            url=url,
            status=int(payload.get("status", 0)),
            text=payload.get("text", ""),
            from_cache=True,
        )

    def _write_cache(self, url: str, status: int, text: str) -> None:
        payload = {"url": url, "status": status, "text": text, "fetched_at": time.time()}
        self._cache_file(url).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    # -- robots ----------------------------------------------------------
    def _robots_allows(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._robots.get(host)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(f"{host}/robots.txt")
            try:
                parser.read()
            except Exception:
                # If robots.txt cannot be read, be conservative but not blocking:
                # default-allow only the well-known public endpoints.
                parser = None
            self._robots[host] = parser or urllib.robotparser.RobotFileParser()
        if parser is None:
            return True
        try:
            return self._robots[host].can_fetch(USER_AGENT, url)
        except Exception:
            return True

    # -- rate limiting ---------------------------------------------------
    def _respect_delay(self, host: str) -> None:
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = time.time() - last
            wait = self.min_delay_seconds - elapsed
            if wait > 0:
                time.sleep(wait)
        self._last_request_at[host] = time.time()

    # -- public ----------------------------------------------------------
    def fetch(self, url: str) -> FetchResult:
        cached = self._read_cache(url)
        if cached is not None:
            return cached
        if self.offline:
            return FetchResult(url=url, status=0, text="", from_cache=False)

        if not self._robots_allows(url):
            return FetchResult(url=url, status=0, text="", from_cache=False, robots_blocked=True)

        host = urlparse(url).netloc
        backoff = self.min_delay_seconds
        for attempt in range(1, self.max_retries + 1):
            self._respect_delay(host)
            try:
                resp = self._session.get(url, timeout=self.timeout)
            except requests.RequestException:
                if attempt == self.max_retries:
                    return FetchResult(url=url, status=0, text="", from_cache=False)
                time.sleep(backoff)
                backoff = min(backoff * 2, 3600)
                continue

            if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                retry_after = resp.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else backoff
                except ValueError:
                    delay = backoff
                time.sleep(min(delay, 3600))
                backoff = min(backoff * 2, 3600)
                continue

            self._write_cache(url, resp.status_code, resp.text)
            return FetchResult(url=url, status=resp.status_code, text=resp.text, from_cache=False)

        return FetchResult(url=url, status=0, text="", from_cache=False)

    def fetch_json(self, url: str):
        result = self.fetch(url)
        if result.status and result.text:
            try:
                return json.loads(result.text), result
            except json.JSONDecodeError:
                return None, result
        return None, result
