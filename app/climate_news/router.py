"""API REST: notícias relacionadas a anomalias de precipitação.

O filtro de período sempre usa a DATA DA ANOMALIA (``anomaly_date``); a data
de publicação é retornada como informação independente.
"""

from __future__ import annotations

import math
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select, true
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, aliased

from app.climate_news.models import AnomalyNews, NewsArticle, NewsInvestigation, PipelineRun, PrecipitationAnomaly
from app.climate_news.schemas import (
    AnalyzedMunicipality,
    AnomaliesResponse,
    NewsResponse,
    RunResponse,
    VerificationStatus,
)
from app.database import get_db
from app.models.municipio import Municipio
from app.models.municipio_details import MunicipioDetails

router = APIRouter(tags=["Anomalias climáticas e notícias"])


def _validate_period(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date não pode ser posterior a end_date")


def _place_filters(db: Session, municipality: str | None, uf: str | None, codigo_ibge: int | None) -> list:
    """Filtros de município; 404 se o município não existe."""
    filters = []
    if uf:
        filters.append(PrecipitationAnomaly.uf == uf.upper())
    if codigo_ibge is not None:
        filters.append(PrecipitationAnomaly.codigo_ibge == codigo_ibge)
    if municipality:
        name = municipality.strip().lower()
        filters.append(func.lower(PrecipitationAnomaly.municipality) == name)
        known = db.scalar(
            select(func.count()).select_from(MunicipioDetails).where(
                func.lower(MunicipioDetails.municipio) == name,
                *( [MunicipioDetails.uf == uf.upper()] if uf else [] ),
            )
        ) or db.scalar(
            select(func.count()).select_from(PrecipitationAnomaly).where(
                func.lower(PrecipitationAnomaly.municipality) == name
            )
        )
        if not known:
            raise HTTPException(status_code=404, detail=f"Município não encontrado: {municipality}")
    return filters


@router.get(
    "/news",
    response_model=NewsResponse,
    summary="Notícias associadas a anomalias de precipitação no período",
    description=(
        "Retorna notícias cujas anomalias relacionadas têm `anomaly_date` dentro de "
        "[start_date, end_date]. Por padrão, só notícias **verificadas** pelo Fact-Checker e com "
        "vínculo relevante (município alvo ou vizinho). Cada notícia aparece uma vez, com a lista "
        "de anomalias relacionadas no período."
    ),
)
def list_news(
    start_date: date = Query(description="Início do período (data da anomalia), AAAA-MM-DD"),
    end_date: date = Query(description="Fim do período (data da anomalia), AAAA-MM-DD"),
    municipality: str | None = Query(default=None, min_length=2, max_length=150, description="Nome do município"),
    uf: str | None = Query(default=None, pattern="^[A-Za-z]{2}$", description="UF, para desambiguar homônimos"),
    codigo_ibge: int | None = Query(default=None, description="Código IBGE do município"),
    source: str | None = Query(default=None, min_length=2, max_length=255, description="Fonte (trecho do nome ou domínio)"),
    verification_status: VerificationStatus = Query(default="verified"),
    sort_by: Literal["anomaly_date", "published_at"] = Query(default="anomaly_date"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _validate_period(start_date, end_date)
    filters = [
        PrecipitationAnomaly.anomaly_date >= start_date,
        PrecipitationAnomaly.anomaly_date <= end_date,
        NewsArticle.verification_status == verification_status,
        *_place_filters(db, municipality, uf, codigo_ibge),
    ]
    if verification_status == "verified":
        # notícia aprovada E vínculo com esta anomalia aprovado e relevante
        filters += [
            AnomalyNews.link_status == "verified",
            AnomalyNews.relevance_status.in_(("relevant", "regional")),
        ]
    if source:
        pattern = f"%{source.strip()}%"
        filters.append(or_(NewsArticle.source.ilike(pattern), NewsArticle.source_domain.ilike(pattern)))

    joined = (
        select(NewsArticle.id)
        .select_from(AnomalyNews)
        .join(PrecipitationAnomaly, PrecipitationAnomaly.id == AnomalyNews.anomaly_id)
        .join(NewsArticle, NewsArticle.id == AnomalyNews.news_id)
        .where(and_(*filters))
    )
    grouped = (
        joined.add_columns(
            func.min(PrecipitationAnomaly.anomaly_date).label("first_anomaly"),
            NewsArticle.published_at,
        )
        .group_by(NewsArticle.id)
        .subquery()
    )
    total = db.scalar(select(func.count()).select_from(grouped)) or 0
    sort_column = grouped.c.first_anomaly if sort_by == "anomaly_date" else grouped.c.published_at
    sort = sort_column.desc().nulls_last() if order == "desc" else sort_column.asc().nulls_last()
    page_ids = db.scalars(
        select(grouped.c.id).order_by(sort, grouped.c.id).offset((page - 1) * limit).limit(limit)
    ).all()

    rows = db.execute(
        select(AnomalyNews, PrecipitationAnomaly, NewsArticle)
        .join(PrecipitationAnomaly, PrecipitationAnomaly.id == AnomalyNews.anomaly_id)
        .join(NewsArticle, NewsArticle.id == AnomalyNews.news_id)
        .where(and_(*filters), NewsArticle.id.in_(page_ids))
        .order_by(PrecipitationAnomaly.anomaly_date)
    ).all() if page_ids else []

    items: dict[uuid.UUID, dict] = {}
    for link, anomaly, news in rows:
        item = items.get(news.id)
        if item is None:
            item = items[news.id] = {
                "id": news.id,
                "url": news.original_url,
                "headline": news.headline,
                "source": news.source,
                "published_at": news.published_at,
                "anomaly_date": anomaly.anomaly_date,
                "event_date": link.event_date,
                "municipality": anomaly.municipality,
                "verification_status": news.verification_status,
                "relevance_status": link.relevance_status,
                "reliability": news.reliability,
                "related_anomalies": [],
            }
        item["related_anomalies"].append(
            {
                "anomaly_id": anomaly.id,
                "anomaly_date": anomaly.anomaly_date,
                "event_date": link.event_date,
                "municipality": anomaly.municipality,
                "uf": anomaly.uf,
                "codigo_ibge": anomaly.codigo_ibge,
                "detector": anomaly.detector,
                "z_score": anomaly.z_score,
                "observed_mm": anomaly.observed_mm,
                "accumulation_days": _assessments(anomaly)["accumulation_days"],
                "enso_phase": _assessments(anomaly)["enso_phase"],
                "oni": _assessments(anomaly)["oni"],
                "anomaly_status": anomaly.status,
                "relevance_status": link.relevance_status,
                "municipality_match": link.municipality_match,
            }
        )
    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "municipality": municipality,
        "uf": uf.upper() if uf else None,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0,
        "news": [items[i] for i in page_ids if i in items],
    }


def _latest_detection_only():
    """Condição: a anomalia pertence à detecção concluída mais recente do seu município.

    As últimas detecções são calculadas uma única vez (DISTINCT ON por município/UF)
    e filtradas com IN. A versão anterior, com subconsulta correlacionada, ordenava
    as execuções para cada uma das ~70 mil anomalias e levava ~24 s.
    """
    run = aliased(PipelineRun)
    latest_runs = (
        select(run.id)
        .where(run.run_type == "detection", run.status == "completed")
        .ext(distinct_on(run.municipality, run.uf))
        .order_by(run.municipality, run.uf, run.finished_at.desc())
    )
    return PrecipitationAnomaly.run_id.in_(latest_runs)


def _assessments(anomaly: PrecipitationAnomaly) -> dict:
    review = anomaly.scientific_review or {}
    verdicts = {r.get("agent"): r for r in review.get("reviews", [])}
    weather = verdicts.get("meteorologist", {})
    climate_metrics = verdicts.get("climatologist", {}).get("metrics") or {}
    return {
        "enso_phase": climate_metrics.get("enso_phase"),
        "oni": climate_metrics.get("oni"),
        "accumulation_days": (review.get("details") or {}).get("window_days"),
        "climate_assessment": verdicts.get("climatologist", {}).get("verdict"),
        "weather_assessment": weather.get("verdict"),
        "peak_daily_mm": (weather.get("metrics") or {}).get("peak_daily_mm"),
    }


@router.get("/anomalies", response_model=AnomaliesResponse, summary="Anomalias detectadas no período")
def list_anomalies(
    start_date: date = Query(),
    end_date: date = Query(),
    municipality: str | None = Query(default=None, min_length=2, max_length=150),
    uf: str | None = Query(default=None, pattern="^[A-Za-z]{2}$"),
    codigo_ibge: int | None = Query(default=None),
    status: Literal["detected", "scientifically_reviewed", "rejected"] | None = Query(default=None),
    detector: Literal["arima_zscore", "accumulation_percentile"] | None = Query(default=None),
    run_id: uuid.UUID | None = Query(default=None, description="Padrão: última detecção concluída por município"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _validate_period(start_date, end_date)
    filters = [
        PrecipitationAnomaly.anomaly_date >= start_date,
        PrecipitationAnomaly.anomaly_date <= end_date,
        *_place_filters(db, municipality, uf, codigo_ibge),
    ]
    if status:
        filters.append(PrecipitationAnomaly.status == status)
    if detector:
        filters.append(PrecipitationAnomaly.detector == detector)
    if run_id:
        filters.append(PrecipitationAnomaly.run_id == run_id)
    else:
        # por padrão, só a detecção concluída mais recente de cada município
        filters.append(_latest_detection_only())
    verified = (
        select(func.count())
        .select_from(AnomalyNews)
        .join(NewsArticle, NewsArticle.id == AnomalyNews.news_id)
        .where(
            AnomalyNews.anomaly_id == PrecipitationAnomaly.id,
            AnomalyNews.link_status == "verified",
            NewsArticle.verification_status == "verified",
        )
        .scalar_subquery()
    )
    investigated = (
        select(NewsInvestigation.id)
        .where(NewsInvestigation.anomaly_id == PrecipitationAnomaly.id, NewsInvestigation.status == "completed")
        .exists()
    )
    total = db.scalar(select(func.count()).select_from(PrecipitationAnomaly).where(*filters)) or 0
    rows = db.execute(
        select(PrecipitationAnomaly, verified.label("verified_news"), investigated.label("news_investigated"))
        .where(*filters)
        .order_by(PrecipitationAnomaly.anomaly_date, PrecipitationAnomaly.detector)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "total": total,
        "page": page,
        "limit": limit,
        "anomalies": [
            {
                **{c.key: getattr(a, c.key) for c in PrecipitationAnomaly.__table__.columns},
                "verified_news": n,
                "news_investigated": pesquisada,
                **_assessments(a),
            }
            for a, n, pesquisada in rows
        ],
    }


@router.get(
    "/municipalities",
    response_model=list[AnalyzedMunicipality],
    summary="Municípios com análise de anomalias",
    description="Municípios que já têm detecção concluída, com o número de anomalias revisadas e de notícias verificadas.",
)
def list_analyzed_municipalities(
    start_date: date | None = Query(default=None, description="Conta só notícias de anomalias a partir desta data"),
    end_date: date | None = Query(default=None, description="Conta só notícias de anomalias até esta data"),
    source: str | None = Query(default=None, min_length=2, max_length=255, description="Conta só notícias desta fonte"),
    db: Session = Depends(get_db),
):
    if start_date and end_date:
        _validate_period(start_date, end_date)
    link_filters = [AnomalyNews.link_status == "verified", NewsArticle.verification_status == "verified"]
    if source:
        pattern = f"%{source.strip()}%"
        link_filters.append(or_(NewsArticle.source.ilike(pattern), NewsArticle.source_domain.ilike(pattern)))
    verified_links = (
        select(AnomalyNews.anomaly_id, AnomalyNews.news_id)
        .join(NewsArticle, NewsArticle.id == AnomalyNews.news_id)
        .where(*link_filters)
        .subquery()
    )
    period = []
    if start_date:
        period.append(PrecipitationAnomaly.anomaly_date >= start_date)
    if end_date:
        period.append(PrecipitationAnomaly.anomaly_date <= end_date)
    in_period = and_(*period) if period else true()
    rows = db.execute(
        select(
            PrecipitationAnomaly.codigo_ibge,
            PrecipitationAnomaly.municipality,
            PrecipitationAnomaly.uf,
            func.count(func.distinct(PrecipitationAnomaly.id)).filter(PrecipitationAnomaly.status != "rejected", in_period),
            func.count(func.distinct(verified_links.c.news_id)).filter(in_period),
            func.min(PrecipitationAnomaly.anomaly_date),
            func.max(PrecipitationAnomaly.anomaly_date),
            func.max(Municipio.latitude),
            func.max(Municipio.longitude),
        )
        .outerjoin(verified_links, verified_links.c.anomaly_id == PrecipitationAnomaly.id)
        .outerjoin(Municipio, Municipio.codigo_ibge == PrecipitationAnomaly.codigo_ibge)
        .where(_latest_detection_only())
        .group_by(PrecipitationAnomaly.codigo_ibge, PrecipitationAnomaly.municipality, PrecipitationAnomaly.uf)
        .order_by(PrecipitationAnomaly.municipality)
    ).all()
    return [
        {
            "codigo_ibge": codigo, "municipality": nome, "uf": uf, "anomalies": anomalias,
            "verified_news": noticias, "first_date": inicio, "last_date": fim,
            "latitude": float(lat) if lat is not None else None,
            "longitude": float(lon) if lon is not None else None,
        }
        for codigo, nome, uf, anomalias, noticias, inicio, fim, lat, lon in rows
    ]


@router.get("/runs/{run_id}", response_model=RunResponse, summary="Rastreabilidade de uma execução")
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.get(PipelineRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return run
