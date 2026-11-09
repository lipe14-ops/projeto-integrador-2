"""Fluxo integrado (banco de teste): detecção → investigação → persistência."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.climate_news.agents.base import MunicipalityContext
from app.climate_news.agents.fact_checker import FactCheckerAgent
from app.climate_news.agents.news_researcher import NewsResearcherAgent
from app.climate_news.agents.orchestrator import InvestigationConfig, Orchestrator
from app.climate_news.detection.arima_zscore import DetectionConfig
from app.climate_news.detection.preparation import prepare_daily_series
from app.climate_news.models import (
    AnomalyNews,
    NewsArticle,
    NewsInvestigation,
    NewsVerificationAttempt,
    PipelineRun,
    PrecipitationAnomaly,
)
from app.climate_news.news.google_news import SearchError, SearchHit
from tests.conftest import FakeHttpClient, article_html, as_frame, synthetic_rain

pytestmark = pytest.mark.db

POA = MunicipalityContext(
    name="Porto Alegre", uf="RS", state="Rio Grande do Sul", region="Sul", codigo_ibge=4314902, neighbors=["Canoas"]
)
PEAK = pd.Timestamp("2018-07-10")
CONFIG = DetectionConfig(max_p=1, max_q=1, seasonal="fourier")
GOOD = "https://g1.globo.com/rs/noticia/2018/07/11/temporal-alaga-porto-alegre.ghtml"
FAR = "https://g1.globo.com/rs/noticia/2018/08/30/chuva-porto-alegre-balanco.ghtml"
MISSING = "https://gauchazh.clicrbs.com.br/geral/noticia/2018/07/removida.html"


class Provider:
    name = "fake"

    def __init__(self, fail_dates=()):
        self.fail_dates = set(fail_dates)

    def search(self, terms, start, end):
        if start in self.fail_dates:
            raise SearchError("HTTP 503 simulado")
        if '"Porto Alegre" (' in terms and start <= PEAK.date() <= end:
            return [
                SearchHit("Temporal alaga ruas de Porto Alegre", "G1", None, GOOD, datetime(2018, 7, 11, tzinfo=timezone.utc), terms),
                SearchHit("Chuva: balanço do inverno em Porto Alegre", "G1", None, FAR, datetime(2018, 7, 12, tzinfo=timezone.utc), terms),
                SearchHit("Matéria removida", "GZH", None, MISSING, None, terms),
            ], terms
        return [], terms

    def resolve(self, link):
        return link


def pages():
    body = "A chuva forte e o temporal provocaram alagamentos em Porto Alegre, informou a Defesa Civil."
    return {
        GOOD: (200, article_html("Temporal alaga ruas de Porto Alegre", body, "2018-07-11T08:00:00-03:00")),
        FAR: (200, article_html("Chuva: balanço do inverno em Porto Alegre", body, "2018-08-30T08:00:00-03:00")),
    }


def series_with_peak() -> pd.Series:
    s = synthetic_rain(years=4, seed=21)
    s.loc[PEAK] = 160.0
    s.loc[PEAK - pd.Timedelta(days=1)] = 0.0
    return s


def build(session_factory, provider=None):
    return Orchestrator(
        session_factory,
        NewsResearcherAgent(provider or Provider()),
        FactCheckerAgent(FakeHttpClient(pages())),
    )


def detect(orchestrator):
    series, quality = prepare_daily_series(as_frame(series_with_peak()))
    return orchestrator.run_detection(POA, series, quality, CONFIG, enso={(2018, 7): 0.1})


def test_full_flow_persists_only_fact_checked_news(session_factory):
    orchestrator = build(session_factory)
    detection = detect(orchestrator)
    assert detection.summary["anomalies_by_detector"]["arima_zscore"] >= 1
    assert PEAK.date().isoformat() in detection.summary["candidate_dates_for_investigation"]

    run_id = orchestrator.run_investigation(detection.run_id, POA, InvestigationConfig(workers=2))
    with session_factory() as db:
        run = db.get(PipelineRun, run_id)
        assert run.status == "completed"
        assert run.parent_run_id == detection.run_id
        assert run.summary["unprocessed_dates"] == [] and run.summary["failed_dates"] == []
        candidates = set(detection.summary["candidate_dates_for_investigation"])
        assert set(run.summary["dates_investigated"]) == candidates  # nenhuma data ignorada
        # datas cuja janela (-3/+7 dias) contém o pico encontram a notícia; as demais ficam sem resultados
        covering = {d for d in candidates if -7 <= (PEAK.date() - date.fromisoformat(d)).days <= 3}
        assert PEAK.date().isoformat() in covering
        assert set(run.summary["dates_without_results"]) == candidates - covering
        assert set(run.summary["dates_with_verified_news"]) == covering

        news = {n.original_url: n for n in db.scalars(select(NewsArticle))}
        assert news[GOOD].verification_status == "verified"
        assert news[GOOD].verified_by == "fact_checker"
        assert news[FAR].verification_status == "rejected"  # publicada fora da janela
        assert news[MISSING].verification_status == "rejected"  # 404
        attempts = db.scalars(select(NewsVerificationAttempt)).all()
        assert {a.agent for a in attempts} == {"fact_checker"}
        anomaly = db.scalars(
            select(PrecipitationAnomaly).where(
                PrecipitationAnomaly.anomaly_date == PEAK.date(), PrecipitationAnomaly.detector == "arima_zscore"
            )
        ).one()
        assert anomaly.status == "scientifically_reviewed"
        agents = {r["agent"] for r in anomaly.scientific_review["reviews"]}
        assert agents == {"data_scientist", "climatologist", "meteorologist"}
        link = db.get(AnomalyNews, (anomaly.id, news[GOOD].id))
        assert link.relevance_status == "relevant"
        detection_run = db.get(PipelineRun, detection.run_id)
        assert detection_run.summary["blocks"] and detection_run.parameters["detection"]["z_threshold"] == 3.0


def test_failed_searches_mark_run_failed_and_resume_completes(session_factory):
    orchestrator = build(session_factory)
    detection = detect(orchestrator)
    peak_window_start = (PEAK - pd.Timedelta(days=3)).date()
    failing = build(session_factory, Provider(fail_dates={peak_window_start}))
    run_id = failing.run_investigation(detection.run_id, POA, InvestigationConfig(workers=1))
    with session_factory() as db:
        run = db.get(PipelineRun, run_id)
        assert run.status == "failed"  # não é concluída com datas falhas
        assert run.summary["failed_dates"] == [PEAK.date().isoformat()]
        assert run.errors

    orchestrator.resume_investigation(run_id, POA)
    with session_factory() as db:
        run = db.get(PipelineRun, run_id)
        assert run.status == "completed"
        inv = db.scalars(select(NewsInvestigation).where(NewsInvestigation.run_id == run_id, NewsInvestigation.attempts == 2)).one()
        assert inv.status == "completed" and inv.n_verified == 1


def test_news_linked_to_several_anomalies_is_stored_once(session_factory):
    orchestrator = build(session_factory)
    detection = detect(orchestrator)
    orchestrator.run_investigation(detection.run_id, POA)
    orchestrator.run_investigation(detection.run_id, POA)  # revalidação
    with session_factory() as db:
        assert db.scalar(select(NewsArticle).where(NewsArticle.original_url == GOOD)).verification_attempts >= 2
        assert len(db.scalars(select(NewsArticle).where(NewsArticle.original_url == GOOD)).all()) == 1


def test_database_refuses_verified_news_without_fact_checker(session_factory):
    with session_factory() as db:
        db.add(
            NewsArticle(
                id=uuid.uuid4(), url="https://x.com/a/b-c-d", original_url="https://x.com/a/b-c-d", headline="h",
                source="X", source_domain="x.com", published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                verification_status="verified", verified_by="news_researcher", verification_evidence={},
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_investigation_requires_completed_detection(session_factory):
    orchestrator = build(session_factory)
    with pytest.raises(LookupError):
        orchestrator.run_investigation(uuid.uuid4(), POA)


def test_rejected_anomalies_are_kept_but_not_investigated_by_default(session_factory):
    orchestrator = build(session_factory)
    detection = detect(orchestrator)
    with session_factory() as db:
        rows = db.execute(
            select(PrecipitationAnomaly.anomaly_date, PrecipitationAnomaly.status, PrecipitationAnomaly.direction).where(
                PrecipitationAnomaly.run_id == detection.run_id
            )
        ).all()
    assert {status for _, status, _ in rows} <= {"scientifically_reviewed", "rejected"}
    assert {d.isoformat() for d, *_ in rows} == set(detection.summary["detected_dates"])
    candidates = set(detection.summary["candidate_dates_for_investigation"])
    expected = {d.isoformat() for d, status, direction in rows if status != "rejected" and direction == "positive"}
    assert candidates == expected


def test_revalidation_rechecks_stored_news_without_new_search(session_factory):
    orchestrator = build(session_factory)
    detection = detect(orchestrator)
    run_id = orchestrator.run_investigation(detection.run_id, POA)
    # a matéria saiu do ar: a revalidação deve rebaixá-la, sem nova busca
    gone = Orchestrator(session_factory, NewsResearcherAgent(Provider(fail_dates={date(1900, 1, 1)})),
                        FactCheckerAgent(FakeHttpClient({FAR: pages()[FAR]})))
    summary = gone.revalidate_investigation(run_id, POA)
    with session_factory() as db:
        news = db.scalar(select(NewsArticle).where(NewsArticle.original_url == GOOD))
        assert news.verification_status == "rejected"
        assert news.verified_by is None
        decisions = [a.decision for a in db.scalars(select(NewsVerificationAttempt).where(NewsVerificationAttempt.news_id == news.id))]
        assert decisions[0] == "verified" and "rejected" in decisions
    assert summary["news_verified"] == 0


def test_main_news_mode_stops_after_n_verified(session_factory):
    second = "https://g1.globo.com/rs/noticia/2018/07/11/chuva-alaga-porto-alegre-de-novo.ghtml"

    class Dois(Provider):
        def search(self, terms, start, end):
            hits, query = super().search(terms, start, end)
            if hits:
                hits.insert(1, SearchHit("Chuva alaga Porto Alegre de novo", "G1", None, second,
                                         datetime(2018, 7, 11, tzinfo=timezone.utc), terms))
            return hits, query

    body = "A chuva forte e o temporal provocaram alagamentos em Porto Alegre, informou a Defesa Civil."
    paginas = pages() | {second: (200, article_html("Chuva alaga Porto Alegre de novo", body, "2018-07-11T09:00:00-03:00"))}
    researcher = NewsResearcherAgent(Dois(), main_only=True)
    checker = FactCheckerAgent(FakeHttpClient(paginas))
    orchestrator = Orchestrator(session_factory, researcher, checker)
    assert researcher.build_queries(
        __import__("app.climate_news.agents.news_researcher", fromlist=["x"]).InvestigationTask("a", PEAK.date(), POA)
    ) == ['"Porto Alegre" (chuva OR chuvas OR temporal OR enchente OR alagamento OR inundação OR deslizamento OR granizo OR vendaval OR tempestade OR transbordamento)']
    detection = detect(orchestrator)
    run_id = orchestrator.run_investigation(detection.run_id, POA, InvestigationConfig(max_verified=1, workers=1),
                                            only_dates=[PEAK.date()])
    with session_factory() as db:
        inv = db.scalars(select(NewsInvestigation).where(NewsInvestigation.run_id == run_id)).one()
        assert inv.n_verified == 1
        assert inv.n_rejected == 0  # parou antes de verificar as demais
        assert any("[principais]" in q for q in inv.queries)
