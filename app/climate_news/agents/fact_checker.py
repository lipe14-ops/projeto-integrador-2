"""Agente 8 — Fact-Checker.

Verificação independente: usa seu próprio cliente HTTP, acessa a URL
original e reextrai título, fonte e data da própria página. As alegações do
News Researcher (manchete, fonte, data do buscador) são apenas comparadas,
nunca aceitas sem confirmação.

Resultado por notícia × anomalia:
- ``verified``: todos os critérios obrigatórios confirmados;
- ``rejected``: algum critério falhou de forma conclusiva;
- ``pending_verification``: não foi possível confirmar (página indisponível,
  data ausente etc.) — nunca é tratado como aprovado.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from app.climate_news.agents.base import MunicipalityContext, utcnow
from app.climate_news.agents.news_researcher import NewsCandidate
from app.climate_news.news.extract import PageMetadata, extract_metadata
from app.climate_news.news.http import FetchResult, HttpClient
from app.climate_news.news.text import (
    RETROSPECTIVE_CUES,
    mentions_place,
    mentions_state,
    domain_of,
    estimate_event_date,
    non_article_reason,
    normalize_text,
    normalize_url,
    strip_site_suffix,
    theme_terms,
    title_similarity,
    years_mentioned,
)

BRT = timezone(timedelta(hours=-3))

OFFICIAL_SUFFIXES = (".gov.br", ".leg.br", ".jus.br", ".mp.br", ".def.br")
OFFICIAL_HINTS = ("inmet", "cemaden", "defesacivil", "prefeitura", "marinha.mil")
AGENCIES = (
    "agenciabrasil.ebc.com.br", "reuters.com", "apnews.com", "afp.com", "efe.com", "agenciagov.ebc.com.br",
)
NATIONAL_MEDIA = (
    "g1.globo.com", "oglobo.globo.com", "globo.com", "folha.uol.com.br", "estadao.com.br", "uol.com.br",
    "cnnbrasil.com.br", "bbc.com", "terra.com.br", "r7.com", "metropoles.com", "correiobraziliense.com.br",
    "band.uol.com.br", "sbtnews.sbt.com.br", "veja.abril.com.br", "exame.com", "poder360.com.br",
    "cartacapital.com.br", "infomoney.com.br", "jovempan.com.br", "otempo.com.br", "gauchazh.clicrbs.com.br",
    "correiodopovo.com.br", "acritica.com", "opopular.com.br", "correio24horas.com.br", "jornaldocomercio.com",
)


def source_tier(domain: str) -> str:
    if domain.endswith(OFFICIAL_SUFFIXES) or any(h in domain for h in OFFICIAL_HINTS):
        return "official"
    if any(domain == a or domain.endswith("." + a) for a in AGENCIES):
        return "news_agency"
    if any(domain == m or domain.endswith("." + m) for m in NATIONAL_MEDIA):
        return "recognized_media"
    return "regional_or_other"


@dataclass
class VerificationContext:
    anomaly_date: date
    window_start: date
    window_end: date
    municipality: MunicipalityContext
    # período do evento detectado (acumulados cobrem vários dias); padrão: a própria data
    event_start: date | None = None
    event_end: date | None = None
    # tolerância para a data de ocorrência estimada no texto, em dias
    event_tolerance_before: int = 2
    event_tolerance_after: int = 3

    @property
    def event_range(self) -> tuple[date, date]:
        start = (self.event_start or self.anomaly_date) - timedelta(days=self.event_tolerance_before)
        end = (self.event_end or self.anomaly_date) + timedelta(days=self.event_tolerance_after)
        return start, end


@dataclass
class FactCheckDecision:
    url: str  # normalizada
    original_url: str
    status: str  # verified | rejected | pending_verification
    relevance_status: str  # relevant | regional | not_relevant | undetermined
    municipality_match: str | None
    reliability: str | None
    source_tier: str | None
    headline: str | None
    source: str | None
    source_domain: str
    published_at: datetime | None
    event_date: date | None
    event_date_evidence: str | None
    canonical_url: str | None
    http_status: int | None
    duplicate_of: str | None
    duplicate_kind: str | None = None
    checks: dict = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=utcnow)
    agent: str = "fact_checker"

    def evidence(self) -> dict:
        return {
            "agent": self.agent,
            "checked_at": self.checked_at.isoformat(),
            "http_status": self.http_status,
            "canonical_url": self.canonical_url,
            "source_tier": self.source_tier,
            "reliability": self.reliability,
            "municipality_match": self.municipality_match,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "event_date_evidence": self.event_date_evidence,
            "duplicate_of": self.duplicate_of,
            "duplicate_kind": self.duplicate_kind,
            "checks": self.checks,
            "reasons": self.reasons,
        }


class FactCheckerAgent:
    name = "fact_checker"

    def __init__(self, client: HttpClient, headline_threshold: float = 0.6, claimed_date_tolerance_days: int = 2):
        self.client = client
        self.headline_threshold = headline_threshold
        self.claimed_date_tolerance_days = claimed_date_tolerance_days
        self._pages: dict[str, tuple[FetchResult, PageMetadata | None, str | None]] = {}
        self._fingerprints: dict[str, str] = {}
        self._canonicals: dict[str, str] = {}
        self._lock = threading.Lock()
        self._url_locks: dict[str, threading.Lock] = {}

    # ---- acesso à página (uma vez por URL) ------------------------------
    def _page(self, url: str) -> tuple[FetchResult, PageMetadata | None, str | None]:
        key = normalize_url(url)
        with self._lock:
            lock = self._url_locks.setdefault(key, threading.Lock())
        with lock:
            if key in self._pages:
                return self._pages[key]
            fetched = self.client.get(url)
            meta, error = None, None
            if fetched.ok:
                try:
                    meta = extract_metadata(fetched.text, fetched.final_url or url)
                except Exception as exc:  # noqa: BLE001
                    error = f"falha ao interpretar HTML: {exc}"
            self._pages[key] = (fetched, meta, error)
            return self._pages[key]

    def _register(self, key: str, canonical: str | None, fingerprint: str) -> tuple[str | None, str | None]:
        """Detecta duplicatas. Retorna (URL já vista, tipo):

        - ``same_article``: mesma matéria por outra URL (mesmo canonical);
        - ``republication``: mesma manchete e data em outra URL/veículo.
        """
        with self._lock:
            duplicate, kind = None, None
            seen_canonical = self._canonicals.get(canonical) if canonical else None
            if seen_canonical and seen_canonical != key:
                duplicate, kind = seen_canonical, "same_article"
            elif fingerprint in self._fingerprints and self._fingerprints[fingerprint] != key:
                duplicate, kind = self._fingerprints[fingerprint], "republication"
            if canonical:
                self._canonicals.setdefault(canonical, key)
            self._fingerprints.setdefault(fingerprint, key)
            return duplicate, kind

    # ---- verificação ----------------------------------------------------
    def verify(self, candidate: NewsCandidate, ctx: VerificationContext) -> FactCheckDecision:
        key = normalize_url(candidate.url)
        domain = domain_of(candidate.url)
        decision = FactCheckDecision(
            url=key, original_url=candidate.url, status="pending_verification", relevance_status="undetermined",
            municipality_match=None, reliability=None, source_tier=None, headline=None, source=None,
            source_domain=domain, published_at=None, event_date=None, event_date_evidence=None,
            canonical_url=None, http_status=None, duplicate_of=None,
        )
        checks = decision.checks

        def fail(check: str, detail: str, status: str = "rejected") -> FactCheckDecision:
            checks[check] = {"passed": False, "detail": detail}
            decision.status = status
            decision.relevance_status = "not_relevant" if status == "rejected" else "undetermined"
            decision.reasons.append(f"{check}: {detail}")
            return decision

        def ok(check: str, detail) -> None:
            checks[check] = {"passed": True, "detail": detail}

        # 1. URL de matéria específica (não página inicial/busca)
        reason = non_article_reason(candidate.url)
        if reason:
            return fail("url_is_article", reason)
        ok("url_is_article", "caminho de matéria específica")

        # 2. página existe
        fetched, meta, parse_error = self._page(candidate.url)
        decision.http_status = fetched.status
        if fetched.status in (404, 410):
            return fail("page_exists", f"HTTP {fetched.status}: página inexistente")
        if not fetched.ok:
            return fail("page_exists", f"não acessível ({fetched.status or fetched.error}); tentar novamente", "pending_verification")
        if fetched.final_url and normalize_url(fetched.final_url) != key:
            redirected = non_article_reason(fetched.final_url)
            if redirected:
                return fail("page_exists", f"redireciona para página que não é matéria ({redirected}): {fetched.final_url}")
        if meta is None or not meta.title:
            return fail("page_exists", parse_error or "página sem título identificável", "pending_verification")
        ok("page_exists", f"HTTP {fetched.status} em {fetched.elapsed}s")

        # 3. manchete corresponde ao conteúdo
        page_title = strip_site_suffix(meta.title, meta.site_name)
        similarity = max(
            title_similarity(candidate.headline, page_title),
            title_similarity(candidate.headline, meta.h1 or ""),
        )
        decision.headline = page_title
        if similarity < self.headline_threshold:
            return fail("headline_matches", f"manchete alegada {candidate.headline!r} ≠ título da página {page_title!r} (similaridade {similarity:.2f})")
        ok("headline_matches", f"similaridade {similarity:.2f} com o título da página")

        # 4. fonte identificada
        tier = source_tier(domain_of(fetched.final_url or candidate.url))
        decision.source_tier = tier
        decision.source = meta.site_name or meta.publisher or candidate.source or domain
        method = "og:site_name" if meta.site_name else "json-ld publisher" if meta.publisher else "domínio + buscador"
        ok("source_identified", {"source": decision.source, "method": method, "domain": domain, "tier": tier})

        # 5. data de publicação confirmada na própria página
        if meta.published_at is None:
            return fail("publication_date_confirmed", "data de publicação não encontrada na página", "pending_verification")
        published = meta.published_at if meta.published_at.tzinfo else meta.published_at.replace(tzinfo=BRT)
        decision.published_at = published
        local_published = published.astimezone(BRT).date()
        date_detail = {"published_at": published.isoformat(), "method": meta.published_source}
        if candidate.claimed_published_at is not None:
            claimed = candidate.claimed_published_at
            if claimed.tzinfo is None:
                claimed = claimed.replace(tzinfo=timezone.utc)
            gap = abs((claimed.astimezone(BRT).date() - local_published).days)
            date_detail["claimed_by_search_engine"] = candidate.claimed_published_at.isoformat()
            if gap > self.claimed_date_tolerance_days:
                date_detail["note"] = f"data alegada pelo buscador difere {gap} dias; prevalece a da página"
                decision.reasons.append("claimed_date_differs: data do buscador divergente da página")
        ok("publication_date_confirmed", date_detail)

        # 6. relação temática com evento de precipitação
        title_n = normalize_text(page_title)
        lead_n = normalize_text(meta.lead)
        body_n = normalize_text(meta.text)
        strong_title, _ = theme_terms(title_n)
        strong_body, weak_body = theme_terms(f"{lead_n} {body_n}")
        event_date, evidence = estimate_event_date(
            f"{title_n} {lead_n}", local_published, ctx.anomaly_date - timedelta(days=7)
        )
        decision.event_date, decision.event_date_evidence = event_date, evidence
        theme_detail = {"title_terms": sorted(strong_title), "body_terms": sorted(strong_body), "context_terms": sorted(weak_body)}
        if not strong_title:
            # sem termo de evento na manchete, o texto precisa descrever um evento datado
            if len(strong_body) < 3 or event_date is None:
                return fail(
                    "thematic_relation",
                    f"manchete sem termo de evento de chuva e texto sem relato datado de evento "
                    f"(corpo {sorted(strong_body)}, data do evento {'não ' if event_date is None else ''}identificada)",
                )
        ok("thematic_relation", theme_detail)

        # 7. compatibilidade geográfica
        place = ctx.municipality
        raw_text = f"{page_title}\n{meta.lead}\n{meta.text}"
        target = mentions_place(raw_text, place.name, place.colliding_names)
        neighbors = [n for n in place.neighbors if mentions_place(raw_text, n)]
        state_ok = mentions_state(raw_text, place.state, place.uf)
        if target and place.homonym:
            # homônimo exato em outra UF: o estado precisa aparecer no texto
            target = state_ok
        elif target and place.colliding_names and not mentions_place(page_title, place.name, place.colliding_names):
            # nome que também é expressão comum (bairros, rios, outros municípios):
            # fora da manchete, só vale com o estado ou um vizinho no texto
            target = state_ok or bool(neighbors)
        if target:
            decision.municipality_match = "target"
            ok("geographic_relation", {"match": "target", "municipality": place.label()})
        elif neighbors:
            decision.municipality_match = "neighbor"
            ok("geographic_relation", {"match": "neighbor", "neighbors_mentioned": neighbors})
        else:
            return fail("geographic_relation", f"não menciona {place.label()} nem municípios vizinhos")

        # 8. relação temporal (publicação na janela e sem indício de outro evento)
        if not ctx.window_start <= local_published <= ctx.window_end:
            return fail(
                "temporal_relation",
                f"publicada em {local_published}, fora da janela {ctx.window_start}..{ctx.window_end} da anomalia {ctx.anomaly_date}",
            )
        other_years = {y for y in years_mentioned(title_n) if abs(y - ctx.anomaly_date.year) >= 1}
        if other_years:
            return fail("temporal_relation", f"manchete trata de outro período/evento ({sorted(other_years)}); provável retrospectiva")
        cue = RETROSPECTIVE_CUES.search(f"{title_n} {lead_n[:600]}")
        if cue:
            return fail("temporal_relation", f"matéria retrospectiva sobre evento anterior (pista: {cue.group(0)!r})")
        event_low, event_high = ctx.event_range
        if event_date is not None and not event_low <= event_date <= event_high:
            return fail(
                "temporal_relation",
                f"texto relata evento em {event_date} ({evidence!r}), fora de {event_low}..{event_high}: "
                "provável outro evento dentro da janela de publicação",
            )
        ok(
            "temporal_relation",
            {
                "anomaly_date": ctx.anomaly_date.isoformat(),
                "published_local_date": local_published.isoformat(),
                "days_after_anomaly": (local_published - ctx.anomaly_date).days,
                "estimated_event_date": event_date.isoformat() if event_date else None,
                "event_date_evidence": evidence,
                "accepted_event_range": [event_low.isoformat(), event_high.isoformat()],
            },
        )

        # 9. duplicação / republicação
        canonical = normalize_url(meta.canonical_url) if meta.canonical_url else None
        decision.canonical_url = canonical
        fingerprint = f"{title_n}|{local_published.isoformat()}"
        decision.duplicate_of, decision.duplicate_kind = self._register(key, canonical, fingerprint)
        checks["duplicate"] = {
            "passed": True,
            "detail": {"duplicate_of": decision.duplicate_of, "kind": decision.duplicate_kind, "canonical_url": canonical},
        }

        # 10. confiabilidade da evidência
        strong_date = meta.published_source and not meta.published_source.startswith("html:visible")
        if tier in ("official", "news_agency", "recognized_media") and strong_date:
            decision.reliability = "high"
        elif strong_date or tier != "regional_or_other":
            decision.reliability = "medium"
        else:
            decision.reliability = "low"
        checks["reliability"] = {"passed": True, "detail": decision.reliability}

        decision.status = "verified"
        decision.relevance_status = "relevant" if decision.municipality_match == "target" else "regional"
        return decision
