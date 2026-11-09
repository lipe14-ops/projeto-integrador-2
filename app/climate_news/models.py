"""Modelo relacional de execuções, anomalias, investigações e notícias.

    pipeline_run 1─N precipitation_anomaly 1─N news_investigation
                                  │                    │
                                  └──N anomaly_news N──┘ (vínculo + relevância)
                                           │
                                     news_article 1─N news_verification_attempt

A notícia (``news_article``) é única por URL normalizada e pode estar ligada a
várias anomalias. Os campos que dependem da anomalia (data da anomalia, data
estimada do evento, município, relevância) ficam no vínculo ``anomaly_news``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

RUN_STATUSES = ("pending", "processing", "completed", "failed")
ANOMALY_STATUSES = ("detected", "scientifically_reviewed", "rejected")
NEWS_STATUSES = ("discovered", "pending_verification", "verified", "rejected")
INVESTIGATION_STATUSES = ("pending", "processing", "completed", "failed")
RELEVANCE_STATUSES = ("relevant", "regional", "not_relevant", "undetermined")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PipelineRun(TimestampMixin, Base):
    __tablename__ = "pipeline_run"
    __table_args__ = (
        CheckConstraint(_in("status", RUN_STATUSES), name="ck_pipeline_run_status"),
        CheckConstraint(_in("run_type", ("detection", "investigation")), name="ck_pipeline_run_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pipeline_run.id", ondelete="SET NULL"))
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    codigo_ibge: Mapped[int | None] = mapped_column(BigInteger)
    municipality: Mapped[str | None] = mapped_column(String(150))
    uf: Mapped[str | None] = mapped_column(String(2))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    agents: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    anomalies = relationship("PrecipitationAnomaly", back_populates="run")


class PrecipitationAnomaly(TimestampMixin, Base):
    __tablename__ = "precipitation_anomaly"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "municipality", "uf", "anomaly_date", "detector",
            name="uq_anomaly_run_place_date", postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(_in("status", ANOMALY_STATUSES), name="ck_anomaly_status"),
        CheckConstraint(_in("direction", ("positive", "negative")), name="ck_anomaly_direction"),
        Index("ix_anomaly_date_place", "anomaly_date", "codigo_ibge"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipeline_run.id", ondelete="CASCADE"), nullable=False)
    codigo_ibge: Mapped[int | None] = mapped_column(BigInteger, index=True)
    municipality: Mapped[str] = mapped_column(String(150), nullable=False)
    uf: Mapped[str | None] = mapped_column(String(2))
    anomaly_date: Mapped[date] = mapped_column(Date, nullable=False)
    detector: Mapped[str] = mapped_column(String(40), nullable=False, default="arima_zscore")
    observed_mm: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_mm: Mapped[float | None] = mapped_column(Float)
    residual: Mapped[float | None] = mapped_column(Float)
    z_score: Mapped[float | None] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(20))
    classification: Mapped[str] = mapped_column(String(80), nullable=False)
    episode_id: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="detected")
    model_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    scientific_review: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    run = relationship("PipelineRun", back_populates="anomalies")
    links = relationship("AnomalyNews", back_populates="anomaly")


class NewsInvestigation(TimestampMixin, Base):
    __tablename__ = "news_investigation"
    __table_args__ = (
        UniqueConstraint("run_id", "anomaly_id", name="uq_investigation_run_anomaly"),
        CheckConstraint(_in("status", INVESTIGATION_STATUSES), name="ck_investigation_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipeline_run.id", ondelete="CASCADE"), nullable=False)
    anomaly_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("precipitation_anomaly.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)
    queries: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sources_consulted: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    n_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_verified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    anomaly = relationship("PrecipitationAnomaly")


class NewsArticle(TimestampMixin, Base):
    __tablename__ = "news_article"
    __table_args__ = (
        CheckConstraint(_in("verification_status", NEWS_STATUSES), name="ck_news_verification_status"),
        # Nenhuma notícia é "verified" sem decisão do Fact-Checker com evidências
        CheckConstraint(
            "verification_status <> 'verified' OR (verified_by = 'fact_checker' "
            "AND verification_evidence IS NOT NULL AND published_at IS NOT NULL AND source IS NOT NULL)",
            name="ck_news_verified_requires_fact_checker",
        ),
        Index("ix_news_canonical_url", "canonical_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="discovered")
    verification_evidence: Mapped[dict | None] = mapped_column(JSONB)
    reliability: Mapped[str | None] = mapped_column(String(10))
    verified_by: Mapped[str | None] = mapped_column(String(30))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discovered_by: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    links = relationship("AnomalyNews", back_populates="news")


class AnomalyNews(TimestampMixin, Base):
    __tablename__ = "anomaly_news"
    __table_args__ = (
        CheckConstraint(_in("relevance_status", RELEVANCE_STATUSES), name="ck_anomaly_news_relevance"),
    )

    anomaly_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("precipitation_anomaly.id", ondelete="CASCADE"), primary_key=True
    )
    news_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("news_article.id", ondelete="CASCADE"), primary_key=True, index=True)
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("news_investigation.id", ondelete="SET NULL"))
    relevance_status: Mapped[str] = mapped_column(String(20), nullable=False)
    link_status: Mapped[str] = mapped_column(String(30), nullable=False)
    municipality_match: Mapped[str | None] = mapped_column(String(20))
    event_date: Mapped[date | None] = mapped_column(Date)
    decision: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    anomaly = relationship("PrecipitationAnomaly", back_populates="links")
    news = relationship("NewsArticle", back_populates="links")


class NewsVerificationAttempt(Base):
    __tablename__ = "news_verification_attempt"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    news_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("news_article.id", ondelete="CASCADE"), nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("news_investigation.id", ondelete="SET NULL"))
    anomaly_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("precipitation_anomaly.id", ondelete="SET NULL"))
    agent: Mapped[str] = mapped_column(String(30), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    checks: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
