"""Cliente HTTP com limite de requisições por host e novas tentativas.

Respeita limites dos buscadores e das fontes: um intervalo mínimo entre
requisições ao mesmo host (configurável por host) e backoff exponencial em
429/5xx. Falhas nunca são mascaradas: o resultado traz status e erro.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 ClimaNoticiasBot/1.0 (projeto academico)"
)
RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass
class FetchResult:
    url: str
    final_url: str | None
    status: int | None
    text: str | None
    error: str | None
    elapsed: float
    attempts: int

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300 and self.text is not None


class HttpClient:
    def __init__(
        self,
        min_interval: float = 1.0,
        host_intervals: dict[str, float] | None = None,
        timeout: float = 20.0,
        retries: int = 2,
        max_bytes: int = 3_000_000,
    ):
        self.min_interval = min_interval
        self.host_intervals = host_intervals or {}
        self.retries = retries
        self.max_bytes = max_bytes
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5"},
        )
        self._locks: dict[str, threading.Lock] = {}
        self._last: dict[str, float] = {}
        self._guard = threading.Lock()

    def _wait_turn(self, host: str) -> None:
        with self._guard:
            lock = self._locks.setdefault(host, threading.Lock())
        with lock:
            interval = self.host_intervals.get(host, self.min_interval)
            wait = self._last.get(host, 0.0) + interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last[host] = time.monotonic()

    def request(self, method: str, url: str, **kwargs) -> FetchResult:
        host = (urlsplit(url).hostname or "").lower()
        started = time.perf_counter()
        error = None
        response = None
        attempt = 0
        for attempt in range(1, self.retries + 2):
            self._wait_turn(host)
            try:
                response = self._client.request(method, url, **kwargs)
                error = None
                if response.status_code not in RETRY_STATUS:
                    break
                error = f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                response = None
                error = f"{type(exc).__name__}: {exc}"
            if attempt <= self.retries:
                time.sleep(min(2 ** attempt, 10))
        text = None
        if response is not None:
            text = response.text if len(response.content) <= self.max_bytes else response.text[: self.max_bytes]
        return FetchResult(
            url=url,
            final_url=str(response.url) if response is not None else None,
            status=response.status_code if response is not None else None,
            text=text,
            error=error,
            elapsed=round(time.perf_counter() - started, 3),
            attempts=attempt,
        )

    def get(self, url: str, **kwargs) -> FetchResult:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> FetchResult:
        return self.request("POST", url, **kwargs)

    def close(self) -> None:
        self._client.close()
