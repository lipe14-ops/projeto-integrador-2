from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

VerificationStatus = Literal["discovered", "pending_verification", "verified", "rejected"]


class Period(BaseModel):
    start_date: date
    end_date: date


class RelatedAnomaly(BaseModel):
    anomaly_id: uuid.UUID
    anomaly_date: date
    event_date: date | None = Field(description="Data estimada de ocorrência, quando identificável no texto")
    municipality: str
    uf: str | None
    codigo_ibge: int | None
    detector: str
    z_score: float | None
    observed_mm: float
    accumulation_days: int | None = None
    enso_phase: Literal["el_nino", "la_nina", "neutral"] | None = Field(
        default=None, description="Fase ENSO pelo ONI do mês da anomalia (≥ 0,5 El Niño; ≤ −0,5 La Niña)")
    oni: float | None = None
    anomaly_status: str
    relevance_status: str
    municipality_match: str | None


class NewsItem(BaseModel):
    id: uuid.UUID
    url: str
    headline: str
    source: str | None
    published_at: datetime | None = Field(description="Data de publicação (independente da data da anomalia)")
    anomaly_date: date = Field(description="Data da primeira anomalia relacionada dentro do período")
    event_date: date | None
    municipality: str
    verification_status: VerificationStatus
    relevance_status: str
    reliability: str | None
    related_anomalies: list[RelatedAnomaly]


class NewsResponse(BaseModel):
    period: Period
    municipality: str | None
    uf: str | None
    total: int
    page: int
    limit: int
    pages: int
    news: list[NewsItem]


class AnomalyItem(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    anomaly_date: date
    municipality: str
    uf: str | None
    codigo_ibge: int | None
    detector: str
    observed_mm: float = Field(description="Chuva observada no dia (ERA5-Land), em mm")
    predicted_mm: float | None = Field(
        description="Previsão típica do modelo levada para mm: exp(ŷ) − 1, com ŷ a previsão de um passo de "
        "ln(1 + chuva). Aproxima um valor típico (mediana), não a média esperada."
    )
    residual: float | None = Field(
        description="Erro de previsão de um passo na escala log: ln(1 + observado) − ŷ. É a base do Z. "
        "Ver docs/avaliacao_professor/RESIDUO_DE_CHUVA.md"
    )
    z_score: float | None = Field(
        description="Resíduo padronizado (resíduo − média)/desvio-padrão dos resíduos do treino; Z > 3 = anomalia estatística"
    )
    direction: str
    severity: str | None
    classification: str
    episode_id: str | None
    status: str
    verified_news: int
    news_investigated: bool = Field(default=False, description="Se a busca de notícias já foi concluída para esta anomalia")
    accumulation_days: int | None = Field(default=None, description="Dias do acumulado (detector de acumulados)")
    climate_assessment: str | None = Field(default=None, description="Veredito do Climatologista")
    weather_assessment: str | None = Field(default=None, description="Veredito do Meteorologista")
    peak_daily_mm: float | None = Field(default=None, description="Maior chuva diária no evento")
    enso_phase: Literal["el_nino", "la_nina", "neutral"] | None = None
    oni: float | None = None


class AnomaliesResponse(BaseModel):
    period: Period
    total: int
    page: int
    limit: int
    anomalies: list[AnomalyItem]


class RunResponse(BaseModel):
    id: uuid.UUID
    run_type: str
    status: str
    parent_run_id: uuid.UUID | None
    algorithm_version: str
    municipality: str | None
    uf: str | None
    period_start: date | None
    period_end: date | None
    parameters: dict
    agents: list
    summary: dict
    errors: list
    started_at: datetime | None
    finished_at: datetime | None


class AnalyzedMunicipality(BaseModel):
    codigo_ibge: int | None
    municipality: str
    uf: str | None
    anomalies: int = Field(description="Anomalias revisadas (não descartadas) na última detecção")
    verified_news: int = Field(description="Notícias verificadas ligadas às anomalias")
    first_date: date | None
    last_date: date | None
    latitude: float | None = None
    longitude: float | None = None
