"""Agente 7 — News Researcher.

Pesquisa notícias para UMA data de anomalia por tarefa. Não valida nada: tudo o
que encontra sai com status ``discovered`` e segue para o Fact-Checker.

Datas importantes:
- ``anomaly_date``: data detectada pelo modelo (entrada da tarefa);
- janela de busca: publicação entre ``anomaly_date − before`` e
  ``anomaly_date + after`` (padrão −3/+7 dias);
- a data de publicação vinda do buscador é apenas uma *alegação* e será
  confirmada na página original pelo Fact-Checker.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Protocol

from app.climate_news.agents.base import MunicipalityContext
from app.climate_news.news.google_news import SearchError, SearchHit
from app.climate_news.news.text import normalize_url

EVENT_TERMS = "(chuva OR chuvas OR temporal OR enchente OR alagamento OR inundação OR deslizamento OR granizo OR vendaval OR tempestade OR transbordamento)"
SHORT_TERMS = "(chuva OR temporal OR enchente OR alagamento OR inundação OR deslizamento)"


class SearchProvider(Protocol):
    name: str

    def search(self, terms: str, start: date, end: date) -> tuple[list[SearchHit], str]: ...

    def resolve(self, link: str) -> str | None: ...


@dataclass
class InvestigationTask:
    anomaly_id: str
    anomaly_date: date
    municipality: MunicipalityContext
    window_before: int = 3
    window_after: int = 7
    include_neighbors: bool = True

    @property
    def window_start(self) -> date:
        return self.anomaly_date - timedelta(days=self.window_before)

    @property
    def window_end(self) -> date:
        return self.anomaly_date + timedelta(days=self.window_after)


@dataclass
class NewsCandidate:
    url: str
    headline: str
    source: str | None
    claimed_published_at: datetime | None
    query: str
    provider: str
    search_link: str


@dataclass
class ResearchOutcome:
    candidates: list[NewsCandidate] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    sources_consulted: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    raw_hits: int = 0
    unresolved_links: int = 0


class NewsResearcherAgent:
    name = "news_researcher"

    def __init__(
        self, provider: SearchProvider, max_candidates: int = 15, max_neighbors: int = 3, main_only: bool = False,
    ):
        self.provider = provider
        self.max_candidates = max_candidates
        self.max_neighbors = max_neighbors
        # modo "principais": só a consulta principal (município + termos de evento),
        # cujos primeiros resultados são os mais relevantes segundo o buscador
        self.main_only = main_only
        self._lock = threading.Lock()

    def build_queries(self, task: InvestigationTask) -> list[str]:
        ctx = task.municipality
        place = f'"{ctx.name}"'
        if ctx.homonym and ctx.state:
            place += f' ("{ctx.state}" OR {ctx.uf})'
        queries = [f"{place} {EVENT_TERMS}"]
        if self.main_only:
            return queries
        queries.append(f'{place} "Defesa Civil"')
        if task.include_neighbors and ctx.neighbors:
            names = " OR ".join(f'"{n}"' for n in ctx.neighbors[: self.max_neighbors])
            queries.append(f"({names}) {SHORT_TERMS}")
        return queries

    def research(self, task: InvestigationTask) -> ResearchOutcome:
        outcome = ResearchOutcome(sources_consulted=[self.provider.name])
        seen: set[str] = set()
        for terms in self.build_queries(task):
            try:
                hits, query = self.provider.search(terms, task.window_start, task.window_end)
            except SearchError as error:
                outcome.errors.append(str(error))
                outcome.queries.append(terms)
                continue
            outcome.queries.append(query)
            outcome.raw_hits += len(hits)
            for hit in hits:
                if len(outcome.candidates) >= self.max_candidates:
                    break
                try:
                    url = self.provider.resolve(hit.link)
                except Exception as error:  # noqa: BLE001 — erro registrado, nunca inventado
                    outcome.errors.append(f"falha ao resolver link: {error}")
                    url = None
                if not url:
                    outcome.unresolved_links += 1
                    continue
                key = normalize_url(url)
                if key in seen:
                    continue
                seen.add(key)
                outcome.candidates.append(
                    NewsCandidate(
                        url=url,
                        headline=hit.headline,
                        source=hit.source,
                        claimed_published_at=hit.published_at,
                        query=query,
                        provider=hit.provider,
                        search_link=hit.link,
                    )
                )
        return outcome
