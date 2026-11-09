"""Provedor de busca: Google News RSS (pt-BR) com filtro de datas.

O RSS aceita os operadores ``after:AAAA-MM-DD`` e ``before:AAAA-MM-DD``,
permitindo buscas históricas. Os links do RSS apontam para redirecionadores do
Google; a URL original é obtida pelo mesmo endpoint usado pela interface web
(``batchexecute``). Se a decodificação falhar, o candidato é descartado com
erro registrado — nunca se inventa uma URL.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus, urlencode

from lxml import etree

from app.climate_news.news.http import HttpClient
from app.climate_news.news.text import parse_datetime, strip_site_suffix

RSS_URL = "https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
ARTICLE_URL = "https://news.google.com/rss/articles/{id}"
BATCH_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"


@dataclass
class SearchHit:
    headline: str
    source: str | None
    source_url: str | None
    link: str
    published_at: datetime | None
    query: str
    provider: str = "google_news_rss"


class SearchError(RuntimeError):
    pass


class GoogleNewsProvider:
    name = "google_news_rss"

    def __init__(self, client: HttpClient, max_results: int = 10):
        self.client = client
        self.max_results = max_results
        self._decoded: dict[str, str | None] = {}

    def search(self, terms: str, start: date, end: date) -> tuple[list[SearchHit], str]:
        """Busca notícias publicadas entre ``start`` e ``end`` (inclusive)."""
        query = f"{terms} after:{start.isoformat()} before:{(end + timedelta(days=1)).isoformat()}"
        url = RSS_URL.format(query=quote_plus(query))
        result = self.client.get(url)
        if not result.ok:
            raise SearchError(f"falha na busca ({result.status or result.error}): {query}")
        try:
            root = etree.fromstring(result.text.encode("utf-8"))
        except etree.XMLSyntaxError as error:
            raise SearchError(f"RSS inválido: {error}") from error
        hits = []
        for item in list(root.iterfind("./channel/item"))[: self.max_results]:
            source = item.find("source")
            source_name = source.text.strip() if source is not None and source.text else None
            title = item.findtext("title") or ""
            hits.append(
                SearchHit(
                    headline=strip_site_suffix(title, source_name),
                    source=source_name,
                    source_url=source.get("url") if source is not None else None,
                    link=item.findtext("link") or "",
                    published_at=parse_datetime(item.findtext("pubDate")),
                    query=query,
                )
            )
        return hits, query

    def resolve(self, link: str) -> str | None:
        """Converte o link do Google News na URL original da matéria."""
        if "news.google.com" not in link:
            return link
        if link in self._decoded:
            return self._decoded[link]
        match = re.search(r"/(?:rss/)?articles/([^?/]+)", link)
        resolved = None
        if match:
            article_id = match.group(1)
            page = self.client.get(ARTICLE_URL.format(id=article_id))
            signature = re.search(r'data-n-a-sg="([^"]+)"', page.text or "")
            timestamp = re.search(r'data-n-a-ts="([^"]+)"', page.text or "")
            if page.ok and signature and timestamp:
                inner = [
                    "garturlreq",
                    [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
                     "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
                    article_id,
                    int(timestamp.group(1)),
                    signature.group(1),
                ]
                payload = urlencode({"f.req": json.dumps([[["Fbv4je", json.dumps(inner), None, "generic"]]])})
                response = self.client.post(
                    BATCH_URL,
                    content=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
                )
                found = re.search(r'garturlres\\",\\"(.*?)\\"', response.text or "")
                if response.ok and found:
                    resolved = found.group(1).encode().decode("unicode_escape")
        self._decoded[link] = resolved
        return resolved
