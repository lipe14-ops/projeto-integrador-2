"""Extração de metadados de páginas de notícia (Open Graph, JSON-LD, HTML)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime

from lxml import html as lxml_html

from app.climate_news.news.text import domain_of, parse_datetime

DATE_META = [
    ("property", "article:published_time"),
    ("name", "article:published_time"),
    ("itemprop", "datePublished"),
    ("name", "datePublished"),
    ("name", "publishdate"),
    ("name", "pubdate"),
    ("name", "date"),
    ("name", "parsely-pub-date"),
    ("name", "sailthru.date"),
    ("name", "dc.date"),
    ("name", "DC.date.issued"),
    ("property", "og:published_time"),
]


@dataclass
class PageMetadata:
    url: str
    title: str | None = None
    h1: str | None = None
    site_name: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
    published_source: str | None = None
    canonical_url: str | None = None
    page_type: str | None = None  # og:type / @type
    text: str = ""
    lead: str = ""
    found: dict = field(default_factory=dict)

    @property
    def domain(self) -> str:
        return domain_of(self.url)


def _meta(doc, attribute: str, value: str) -> str | None:
    nodes = doc.xpath(f'//meta[translate(@{attribute}, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")="{value.lower()}"]/@content')
    for node in nodes:
        if node and node.strip():
            return node.strip()
    return None


def _json_ld_items(doc) -> list[dict]:
    items: list[dict] = []
    for script in doc.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            data = json.loads(script)
        except (ValueError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                items.append(item)
                if "@graph" in item:
                    stack.extend(item["@graph"] if isinstance(item["@graph"], list) else [item["@graph"]])
    return items


ARTICLE_TYPES = {"NewsArticle", "Article", "ReportageNewsArticle", "BlogPosting", "AnalysisNewsArticle", "LiveBlogPosting"}


def extract_metadata(content: str, url: str) -> PageMetadata:
    doc = lxml_html.fromstring(content)
    meta = PageMetadata(url=url)

    for tag in doc.xpath("//script|//style|//noscript"):
        tag.drop_tree()

    articles = []
    for item in _json_ld_items(doc):
        types = item.get("@type")
        types = set(types) if isinstance(types, list) else {types}
        if types & ARTICLE_TYPES:
            articles.append(item)

    meta.title = _meta(doc, "property", "og:title") or _meta(doc, "name", "twitter:title")
    if not meta.title and articles:
        meta.title = articles[0].get("headline")
    if not meta.title:
        titles = doc.xpath("//title/text()")
        meta.title = titles[0].strip() if titles else None
    h1 = doc.xpath("//h1")
    meta.h1 = h1[0].text_content().strip() if h1 else None

    meta.site_name = _meta(doc, "property", "og:site_name")
    meta.page_type = _meta(doc, "property", "og:type")
    for article in articles:
        publisher = article.get("publisher")
        if isinstance(publisher, dict) and publisher.get("name"):
            meta.publisher = publisher["name"]
            break
        if isinstance(publisher, str):
            meta.publisher = publisher
            break
    if articles and not meta.page_type:
        meta.page_type = "article"

    for attribute, value in DATE_META:
        parsed = parse_datetime(_meta(doc, attribute, value))
        if parsed:
            meta.published_at, meta.published_source = parsed, f"meta[{attribute}={value}]"
            break
    if meta.published_at is None:
        for article in articles:
            parsed = parse_datetime(article.get("datePublished"))
            if parsed:
                meta.published_at, meta.published_source = parsed, "json-ld:datePublished"
                break
    if meta.published_at is None:
        for value in doc.xpath("//time/@datetime"):
            parsed = parse_datetime(value)
            if parsed:
                meta.published_at, meta.published_source = parsed, "html:time[datetime]"
                break
    if meta.published_at is None:
        # último recurso: data visível em elemento cuja classe indica data de
        # publicação (ex.: Drupal "field--name-field-noticia-data"); menor confiança
        lower = "translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"
        nodes = doc.xpath(
            f"//*[contains({lower}, 'date') or contains({lower}, 'data') or contains({lower}, 'publica')]"
        )
        for node in nodes[:50]:
            text = node.text_content().strip()
            match = re.search(r"\b(\d{2}/\d{2}/\d{4})(?:\s*[-–às]*\s*(\d{2})[:h](\d{2}))?", text)
            if match and len(text) < 120:
                parsed = parse_datetime(
                    f"{match.group(1)} {match.group(2)}:{match.group(3)}" if match.group(2) else match.group(1)
                )
                if parsed:
                    meta.published_at, meta.published_source = parsed, "html:visible-date-element"
                    break

    canonical = doc.xpath('//link[@rel="canonical"]/@href')
    meta.canonical_url = canonical[0].strip() if canonical else _meta(doc, "property", "og:url")

    scope = doc.xpath("//article") or [doc]
    paragraphs = [p.text_content().strip() for p in scope[0].xpath(".//p")]
    paragraphs = [p for p in paragraphs if len(p) > 40]
    meta.text = "\n".join(paragraphs)[:30000]
    meta.lead = " ".join(paragraphs[:3])
    description = _meta(doc, "property", "og:description") or _meta(doc, "name", "description")
    if description:
        meta.lead = f"{description} {meta.lead}".strip()
    meta.found = {
        "title": bool(meta.title),
        "site_name": bool(meta.site_name),
        "publisher": bool(meta.publisher),
        "published_at": meta.published_source,
        "json_ld_article": bool(articles),
        "paragraphs": len(paragraphs),
    }
    return meta
