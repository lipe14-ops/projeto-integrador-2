"""Investigação jornalística: News Researcher e Fact-Checker (HTTP simulado)."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.climate_news.agents.base import MunicipalityContext
from app.climate_news.agents.fact_checker import FactCheckerAgent, VerificationContext
from app.climate_news.agents.news_researcher import InvestigationTask, NewsCandidate, NewsResearcherAgent
from app.climate_news.news.google_news import SearchError, SearchHit
from app.climate_news.news.text import non_article_reason, normalize_url
from tests.conftest import FakeHttpClient, article_html

POA = MunicipalityContext(
    name="Porto Alegre", uf="RS", state="Rio Grande do Sul", region="Sul", codigo_ibge=4314902,
    neighbors=["Canoas", "Viamão"],
)
CTX = VerificationContext(date(2024, 5, 1), date(2024, 4, 28), date(2024, 5, 8), POA)
URL = "https://g1.globo.com/rs/rio-grande-do-sul/noticia/2024/05/02/chuva-alaga-bairros-de-porto-alegre.ghtml"
TITLE = "Chuva alaga bairros de Porto Alegre e Defesa Civil emite alerta"
BODY = (
    "A chuva intensa desta quarta-feira provocou alagamentos em vários bairros de Porto Alegre, segundo a Defesa Civil.\n"
    "O temporal derrubou árvores e o nível do Guaíba subiu, com risco de enchente nas áreas ribeirinhas da capital."
)


def candidate(url=URL, headline=TITLE, claimed=datetime(2024, 5, 2, 13, tzinfo=timezone.utc)) -> NewsCandidate:
    return NewsCandidate(url, headline, "G1", claimed, "q", "fake", "https://news.google.com/rss/articles/x")


def checker(pages) -> tuple[FactCheckerAgent, FakeHttpClient]:
    client = FakeHttpClient(pages)
    return FactCheckerAgent(client), client


def test_real_related_news_is_verified():
    agent, _ = checker({URL: (200, article_html(TITLE, BODY))})
    decision = agent.verify(candidate(), CTX)
    assert decision.status == "verified", decision.reasons
    assert decision.relevance_status == "relevant"
    assert decision.municipality_match == "target"
    assert decision.reliability == "high"
    assert decision.source == "G1"
    assert decision.published_at.date() == date(2024, 5, 2)
    assert decision.event_date == date(2024, 5, 1)  # "desta quarta-feira" antes de 02/05 (quinta)
    assert all(check["passed"] for check in decision.checks.values())


def test_nonexistent_url_is_rejected():
    agent, _ = checker({})
    decision = agent.verify(candidate(), CTX)
    assert decision.status == "rejected"
    assert "page_exists" in decision.reasons[0]


def test_network_failure_stays_pending_not_verified():
    agent, _ = checker({URL: (None, None)})
    decision = agent.verify(candidate(), CTX)
    assert decision.status == "pending_verification"


def test_headline_incompatible_with_content_is_rejected():
    page = article_html("Prefeitura anuncia nova linha de ônibus no centro", "Texto sobre transporte público em Porto Alegre.")
    agent, _ = checker({URL: (200, page)})
    decision = agent.verify(candidate(), CTX)
    assert decision.status == "rejected"
    assert not decision.checks["headline_matches"]["passed"]


def test_wrong_publication_date_uses_page_date_and_rejects():
    page = article_html(TITLE, BODY, published="2024-06-20T09:00:00-03:00")
    agent, _ = checker({URL: (200, page)})
    decision = agent.verify(candidate(), CTX)  # buscador alegou 02/05
    assert decision.status == "rejected"
    assert decision.checks["publication_date_confirmed"]["detail"]["note"]
    assert not decision.checks["temporal_relation"]["passed"]


def test_missing_publication_date_is_pending():
    agent, _ = checker({URL: (200, article_html(TITLE, BODY, published=None))})
    assert agent.verify(candidate(), CTX).status == "pending_verification"


def test_news_from_another_municipality_is_rejected():
    title = "Chuva alaga bairros de Goiânia e Defesa Civil emite alerta"
    body = BODY.replace("Porto Alegre", "Goiânia").replace("Guaíba", "Meia Ponte")
    agent, _ = checker({URL: (200, article_html(title, body))})
    decision = agent.verify(candidate(headline=title), CTX)
    assert decision.status == "rejected"
    assert not decision.checks["geographic_relation"]["passed"]


def test_neighbor_municipality_is_verified_as_regional():
    title = "Temporal causa alagamentos em Canoas"
    body = "A chuva forte provocou alagamentos e deslizamentos em Canoas, na Região Metropolitana."
    agent, _ = checker({URL: (200, article_html(title, body))})
    decision = agent.verify(candidate(headline=title), CTX)
    assert decision.status == "verified"
    assert decision.relevance_status == "regional"


def test_duplicate_same_article_is_detected():
    other = URL.replace("g1.globo.com/rs", "g1.globo.com/rs/amp")
    page = article_html(TITLE, BODY, canonical=URL)
    agent, _ = checker({URL: (200, page), other: (200, page)})
    first = agent.verify(candidate(), CTX)
    second = agent.verify(candidate(url=other), CTX)
    assert first.duplicate_of is None
    assert second.duplicate_of == normalize_url(URL)
    assert second.duplicate_kind == "same_article"


def test_page_is_fetched_once_per_url():
    agent, client = checker({URL: (200, article_html(TITLE, BODY))})
    agent.verify(candidate(), CTX)
    agent.verify(candidate(), CTX)
    assert client.calls == [URL]


def test_news_published_much_later_is_rejected():
    page = article_html(TITLE, BODY, published="2024-07-15T10:00:00-03:00")
    agent, _ = checker({URL: (200, page)})
    decision = agent.verify(candidate(claimed=datetime(2024, 7, 15, tzinfo=timezone.utc)), CTX)
    assert decision.status == "rejected"
    assert "fora da janela" in decision.checks["temporal_relation"]["detail"]


def test_retrospective_about_other_event_is_rejected():
    title = "Chuva em Porto Alegre: como foi a histórica enchente de 1941"
    body = "Relembre a enchente de 1941 em Porto Alegre, quando a chuva e a cheia do Guaíba inundaram o centro."
    agent, _ = checker({URL: (200, article_html(title, body))})
    decision = agent.verify(candidate(headline=title), CTX)
    assert decision.status == "rejected"
    assert "1941" in decision.checks["temporal_relation"]["detail"]


def test_off_topic_news_is_rejected():
    title = "Porto Alegre inaugura nova ciclovia na orla"
    agent, _ = checker({URL: (200, article_html(title, "Obra de mobilidade urbana em Porto Alegre foi entregue."))})
    decision = agent.verify(candidate(headline=title), CTX)
    assert decision.status == "rejected"
    assert not decision.checks["thematic_relation"]["passed"]


@pytest.mark.parametrize(
    "url",
    [
        "https://g1.globo.com/",
        "https://g1.globo.com/busca/?q=chuva+porto+alegre",
        "https://gauchazh.clicrbs.com.br/tag/chuva",
        "https://news.google.com/rss/articles/abc",
        "https://www.example.com/?s=chuva",
    ],
)
def test_homepages_and_search_pages_are_never_news(url):
    assert non_article_reason(url) is not None
    agent, client = checker({})
    assert agent.verify(candidate(url=url), CTX).status == "rejected"
    assert client.calls == []


# ---- News Researcher -------------------------------------------------------


class FakeProvider:
    name = "fake"

    def __init__(self, hits_by_query=None, fail=False):
        self.hits_by_query = hits_by_query or {}
        self.fail = fail
        self.calls = []

    def search(self, terms, start, end):
        self.calls.append((terms, start, end))
        if self.fail:
            raise SearchError("HTTP 503")
        for key, hits in self.hits_by_query.items():
            if key in terms:
                return hits, terms
        return [], terms

    def resolve(self, link):
        return link.replace("gn:", "")


def hit(url, title="Chuva em Porto Alegre"):
    return SearchHit(title, "G1", None, f"gn:{url}", datetime(2024, 5, 2, tzinfo=timezone.utc), "q")


def task(**kwargs):
    return InvestigationTask("a1", date(2024, 5, 1), POA, **kwargs)


def test_researcher_uses_configurable_window_and_all_queries():
    provider = FakeProvider()
    outcome = NewsResearcherAgent(provider).research(task(window_before=2, window_after=10))
    assert {(s, e) for _, s, e in provider.calls} == {(date(2024, 4, 29), date(2024, 5, 11))}
    assert len(outcome.queries) == 3  # município, Defesa Civil, vizinhos
    assert outcome.candidates == []  # nenhuma notícia: registrado, sem inventar


def test_researcher_deduplicates_and_never_validates():
    url = "https://g1.globo.com/rs/noticia/2024/05/02/chuva.ghtml"
    provider = FakeProvider({"Porto Alegre": [hit(url), hit(url + "?utm_source=x")]})
    outcome = NewsResearcherAgent(provider).research(task(include_neighbors=False))
    assert [c.url for c in outcome.candidates] == [url]
    assert not hasattr(outcome.candidates[0], "status")


def test_researcher_records_search_errors():
    outcome = NewsResearcherAgent(FakeProvider(fail=True)).research(task())
    assert len(outcome.errors) == 3
    assert outcome.candidates == []


def test_homonym_queries_include_state():
    ctx = MunicipalityContext(name="Bom Jesus", uf="RS", state="Rio Grande do Sul", homonym=True)
    queries = NewsResearcherAgent(FakeProvider()).build_queries(InvestigationTask("a", date(2024, 1, 1), ctx))
    assert all('"Rio Grande do Sul"' in q for q in queries[:2])


# ---- regressões encontradas na auditoria manual da execução real (Porto Alegre) ----


def test_marco_temporal_is_not_a_storm():
    title = "Povos indígenas do RS realizam mobilização no centro de Porto Alegre contra o Marco Temporal"
    body = "Lideranças protestaram contra o marco temporal em Porto Alegre nesta quinta-feira (23)."
    agent, _ = checker({URL: (200, article_html(title, body))})
    decision = agent.verify(candidate(headline=title), CTX)
    assert decision.status == "rejected"
    assert not decision.checks["thematic_relation"]["passed"]


def test_different_event_inside_publication_window_is_rejected():
    ctx = VerificationContext(date(2021, 9, 7), date(2021, 9, 4), date(2021, 9, 14), POA)
    title = "Chuva forte provoca queda de árvores em Porto Alegre"
    body = "A chuva forte desta segunda-feira derrubou árvores e causou alagamentos em Porto Alegre."
    page = article_html(title, body, published="2021-09-14T09:00:00-03:00")  # segunda = 13/09
    agent, _ = checker({URL: (200, page)})
    decision = agent.verify(candidate(headline=title, claimed=None), ctx)
    assert decision.status == "rejected"
    assert "outro evento" in decision.checks["temporal_relation"]["detail"]


def test_event_inside_accumulation_period_is_accepted():
    ctx = VerificationContext(date(2024, 5, 4), date(2024, 5, 1), date(2024, 5, 11), POA,
                              event_start=date(2024, 4, 27), event_end=date(2024, 5, 5))
    title = "Temporal alaga bairros de Porto Alegre"
    body = "O temporal de 29 de abril provocou alagamentos e enchente em Porto Alegre, segundo a Defesa Civil."
    page = article_html(title, body, published="2024-05-02T09:00:00-03:00")
    agent, _ = checker({URL: (200, page)})
    decision = agent.verify(candidate(headline=title, claimed=None), ctx)
    assert decision.status == "verified", decision.reasons
    assert decision.event_date == date(2024, 4, 29)


def test_anniversary_retrospective_is_rejected():
    title = "Capivaras em Porto Alegre: como fauna e flora foram afetadas pela enchente"
    body = "Um ano após a enchente que atingiu Porto Alegre, pesquisadores avaliam os efeitos da cheia sobre a fauna."
    agent, _ = checker({URL: (200, article_html(title, body))})
    decision = agent.verify(candidate(headline=title), CTX)
    assert decision.status == "rejected"
    assert "retrospectiva" in decision.checks["temporal_relation"]["detail"]


def test_body_only_mentions_without_dated_event_are_rejected():
    title = "Secretaria de Obras limpa calha de macrodrenagem em Porto Alegre"
    body = "O serviço previne alagamentos e enchentes em dias de chuva, informou a prefeitura de Porto Alegre."
    agent, _ = checker({URL: (200, article_html(title, body))})
    decision = agent.verify(candidate(headline=title), CTX)
    assert decision.status == "rejected"
    assert not decision.checks["thematic_relation"]["passed"]


def test_months_after_retrospective_is_rejected():
    title = "Sete meses depois da pior enchente de sua história, Rio Grande do Sul ainda trabalha para se recuperar"
    body = "Sete meses depois da enchente, Porto Alegre ainda reconstrói áreas atingidas pela cheia e pelas chuvas."
    agent, _ = checker({URL: (200, article_html(title, body))})
    decision = agent.verify(candidate(headline=title), CTX)
    assert decision.status == "rejected"
    assert "retrospectiva" in decision.checks["temporal_relation"]["detail"]


# ---- regressões da aba Notícias (Rio Verde/GO) ----

RV = MunicipalityContext(
    name="Rio Verde", uf="GO", state="Goiás", region="Centro-Oeste", codigo_ibge=5218805,
    neighbors=["Jataí"], colliding_names=["Lucas do Rio Verde", "Rio Verde de Mato Grosso"],
)
RV_CTX = VerificationContext(date(2024, 5, 1), date(2024, 4, 28), date(2024, 5, 8), RV)


def test_colliding_municipality_name_is_not_a_mention():
    title = "Fortes chuvas causam inundações em Lucas do Rio Verde; veja vídeos"
    body = "A chuva forte provocou alagamentos e inundações em Lucas do Rio Verde, no norte de Mato Grosso."
    agent, _ = checker({URL: (200, article_html(title, body))})
    decision = agent.verify(candidate(headline=title), RV_CTX)
    assert decision.status == "rejected"
    assert not decision.checks["geographic_relation"]["passed"]


def test_river_named_like_the_city_is_not_a_mention():
    title = "Temporal causa alagamentos na região de Sorocaba"
    body = "A chuva forte fez o rio Verde transbordar e causou alagamentos e enchente em bairros de Sorocaba."
    agent, _ = checker({URL: (200, article_html(title, body))})
    assert agent.verify(candidate(headline=title), RV_CTX).status == "rejected"


def test_city_mention_still_verified_with_collisions_masked():
    title = "Chuva forte causa alagamentos em Rio Verde"
    body = "O temporal provocou alagamentos em Rio Verde, no sudoeste goiano, segundo a Defesa Civil."
    agent, _ = checker({URL: (200, article_html(title, body))})
    decision = agent.verify(candidate(headline=title), RV_CTX)
    assert decision.status == "verified", decision.reasons
    assert decision.municipality_match == "target"


def test_neighborhood_with_same_name_needs_state_context():
    title = "Araçoiaba da Serra declara estado de calamidade pública após temporal"
    body = ("O temporal provocou queda de árvores e destelhamentos, além do desabamento da cobertura da quadra "
            "do bairro Rio Verde, em Araçoiaba da Serra, interior de São Paulo, com chuva e alagamentos.")
    agent, _ = checker({URL: (200, article_html(title, body))})
    assert agent.verify(candidate(headline=title), RV_CTX).status == "rejected"
    # com o estado no texto, a mesma menção vale
    body_go = "O temporal provocou alagamentos em Rio Verde, no sudoeste goiano, e a chuva derrubou árvores na cidade."
    agent, _ = checker({URL: (200, article_html("Temporal causa estragos no interior", body_go))})
    assert agent.verify(candidate(headline="Temporal causa estragos no interior"), RV_CTX).status == "verified"
