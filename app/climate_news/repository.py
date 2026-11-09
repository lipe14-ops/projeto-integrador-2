"""Persistência das execuções, anomalias, investigações e notícias."""

from __future__ import annotations

import uuid
from dataclasses import asdict

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.climate_news import ALGORITHM_VERSION
from app.climate_news.agents.base import AgentReport, MunicipalityContext, utcnow
from app.climate_news.agents.fact_checker import FactCheckDecision
from app.climate_news.agents.news_researcher import NewsCandidate
from app.climate_news.detection.arima_zscore import Anomaly
from app.climate_news.models import (
    AnomalyNews,
    NewsArticle,
    NewsInvestigation,
    NewsVerificationAttempt,
    PipelineRun,
    PrecipitationAnomaly,
)

# Critérios que dependem só da página (valem para todas as anomalias)
PAGE_LEVEL_CHECKS = (
    "url_is_article",
    "page_exists",
    "headline_matches",
    "source_identified",
    "publication_date_confirmed",
    "thematic_relation",
)


class UnverifiedApprovalError(PermissionError):
    """Tentativa de marcar como verificada uma notícia sem decisão do Fact-Checker."""


def create_run(db: Session, run_type: str, **fields) -> PipelineRun:
    run = PipelineRun(
        id=uuid.uuid4(),
        run_type=run_type,
        status="processing",
        algorithm_version=fields.pop("algorithm_version", ALGORITHM_VERSION),
        started_at=utcnow(),
        **fields,
    )
    db.add(run)
    db.commit()
    return run


def finish_run(db: Session, run: PipelineRun, status: str, summary: dict, errors: list | None = None) -> None:
    run.status = status
    run.summary = summary
    run.errors = list(errors or [])
    run.finished_at = utcnow()
    db.commit()


def save_anomaly(
    db: Session,
    run: PipelineRun,
    context: MunicipalityContext,
    anomaly: Anomaly,
    status: str,
    model_params: dict,
    reviews: list[AgentReport],
    decision: dict,
) -> PrecipitationAnomaly:
    row = PrecipitationAnomaly(
        id=uuid.uuid4(),
        run_id=run.id,
        codigo_ibge=context.codigo_ibge,
        municipality=context.name,
        uf=context.uf,
        anomaly_date=anomaly.date,
        detector=anomaly.detector,
        observed_mm=anomaly.observed_mm,
        predicted_mm=anomaly.predicted_mm,
        residual=anomaly.residual,
        z_score=anomaly.z_score,
        direction=anomaly.direction,
        severity=anomaly.severity,
        classification=anomaly.classification,
        episode_id=anomaly.episode_id,
        status=status,
        model_params=model_params,
        scientific_review={
            "decision": decision,
            "reviews": [r.to_dict() for r in reviews],
            "quality_flags": anomaly.quality_flags,
            "details": anomaly.details,
            "residual_mm": anomaly.residual_mm,
        },
    )
    db.add(row)
    return row


def _guard_verified(decision: FactCheckDecision) -> None:
    if decision.status == "verified" and (
        decision.agent != "fact_checker" or not decision.checks or decision.published_at is None
    ):
        raise UnverifiedApprovalError("Somente o Fact-Checker, com evidências, pode aprovar uma notícia.")


def record_decision(
    db: Session,
    candidate: NewsCandidate,
    decision: FactCheckDecision,
    anomaly: PrecipitationAnomaly,
    investigation: NewsInvestigation,
) -> NewsArticle:
    """Grava/atualiza notícia, vínculo com a anomalia e tentativa de verificação."""
    _guard_verified(decision)
    lookups = [NewsArticle.url == decision.url]
    if decision.canonical_url:
        lookups += [NewsArticle.url == decision.canonical_url, NewsArticle.canonical_url == decision.canonical_url]
    if decision.duplicate_kind == "same_article" and decision.duplicate_of:
        lookups.append(NewsArticle.url == decision.duplicate_of)
    news = db.scalars(select(NewsArticle).where(or_(*lookups)).limit(1)).first()
    if news is None:
        news = NewsArticle(
            id=uuid.uuid4(),
            url=decision.url,
            original_url=decision.original_url,
            headline=decision.headline or candidate.headline,
            source=decision.source or candidate.source,
            source_domain=decision.source_domain,
            verification_status="discovered",
            discovered_by={
                "agent": "news_researcher",
                "provider": candidate.provider,
                "query": candidate.query,
                "claimed_headline": candidate.headline,
                "claimed_source": candidate.source,
                "claimed_published_at": candidate.claimed_published_at.isoformat() if candidate.claimed_published_at else None,
                "investigation_id": str(investigation.id),
            },
        )
        db.add(news)
        db.flush()

    page_failed = any(
        name in decision.checks and not decision.checks[name]["passed"] for name in PAGE_LEVEL_CHECKS
    )
    if decision.headline:
        news.headline = decision.headline
    if decision.source:
        news.source = decision.source
    if decision.published_at:
        news.published_at = decision.published_at
    if decision.canonical_url:
        news.canonical_url = decision.canonical_url
    news.verification_attempts += 1
    news.last_verified_at = decision.checked_at

    link = db.get(AnomalyNews, (anomaly.id, news.id))
    if link is None:
        link = AnomalyNews(anomaly_id=anomaly.id, news_id=news.id)
        db.add(link)
    link.investigation_id = investigation.id
    link.relevance_status = decision.relevance_status
    link.link_status = decision.status
    link.municipality_match = decision.municipality_match
    link.event_date = decision.event_date
    link.decision = decision.evidence()
    db.flush()

    # Status global: falha de página prevalece; senão, verificado se algum
    # vínculo foi aprovado pelo Fact-Checker.
    if page_failed:
        status = decision.status
    else:
        statuses = set(db.scalars(select(AnomalyNews.link_status).where(AnomalyNews.news_id == news.id)))
        status = (
            "verified" if "verified" in statuses
            else "pending_verification" if "pending_verification" in statuses
            else "rejected"
        )
    news.verification_status = status
    if status == "verified":
        news.verified_by = "fact_checker"
        # um vínculo rejeitado por contexto não substitui a evidência da aprovação
        if decision.status == "verified" or news.verification_evidence is None:
            news.reliability = decision.reliability
            news.verification_evidence = decision.evidence()
    else:
        news.verified_by = None
        news.reliability = None
        news.verification_evidence = decision.evidence()

    db.add(
        NewsVerificationAttempt(
            id=uuid.uuid4(),
            news_id=news.id,
            investigation_id=investigation.id,
            anomaly_id=anomaly.id,
            agent=decision.agent,
            decision=decision.status,
            http_status=decision.http_status,
            reasons=decision.reasons,
            checks=decision.checks,
            checked_at=decision.checked_at,
        )
    )
    return news


def config_dict(config) -> dict:
    return asdict(config) if config is not None else {}
