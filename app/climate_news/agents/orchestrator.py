"""Agente 1 — Orquestrador.

Coordena o fluxo completo:

    dados → Cientista de Dados (ARIMA+Z) → Climatologista (acumulados)
          → revisão científica em paralelo (Dados, Climatologia, Meteorologia)
          → Cientista da Computação (auditoria) → persistência das anomalias
          → tarefas de investigação (uma por data, em paralelo)
              → News Researcher (descobre) → Fact-Checker (verifica)
              → persistência (somente decisões do Fact-Checker aprovam)

Garantias:
- nenhuma data candidata é ignorada: cada uma vira uma ``news_investigation``;
- a execução só é ``completed`` se todas as investigações terminaram;
- falhas ficam registradas na investigação e na execução (nunca escondidas);
- o pesquisador nunca valida as próprias descobertas.
"""

from __future__ import annotations

import logging
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.climate_news import ALGORITHM_VERSION
from app.climate_news.agents.base import AGENT_NAMES, AgentReport, MunicipalityContext, utcnow
from app.climate_news.agents.climatologist import ClimatologistAgent
from app.climate_news.agents.computer_scientist import ComputerScientistAgent
from app.climate_news.agents.data_scientist import DataScientistAgent
from app.climate_news.agents.fact_checker import FactCheckerAgent, VerificationContext
from app.climate_news.agents.meteorologist import MeteorologistAgent
from app.climate_news.agents.news_researcher import InvestigationTask, NewsCandidate, NewsResearcherAgent
from app.climate_news.detection.accumulation import AccumulationConfig
from app.climate_news.detection.arima_zscore import Anomaly, DetectionConfig
from app.climate_news.detection.preparation import DataQualityReport
from app.climate_news.models import AnomalyNews, NewsInvestigation, PipelineRun, PrecipitationAnomaly
from app.climate_news.repository import create_run, finish_run, record_decision, save_anomaly

log = logging.getLogger("climate_news.orchestrator")


@dataclass
class InvestigationConfig:
    window_before: int = 3
    window_after: int = 7
    workers: int = 3
    include_rejected: bool = False
    include_neighbors: bool = True
    # "principais notícias": para de verificar após N aprovadas (None = todas)
    max_verified: int | None = None

    def __post_init__(self):
        if self.window_before < 0 or self.window_after < 0:
            raise ValueError("a janela temporal não pode ser negativa")
        if self.workers < 1:
            raise ValueError("workers deve ser >= 1")


@dataclass
class DetectionOutcome:
    run_id: uuid.UUID
    anomalies: int
    candidates: int
    summary: dict = field(default_factory=dict)


def decide_scientific_status(data: AgentReport, climate: AgentReport, weather: AgentReport) -> tuple[str, list[str]]:
    """Consolida os pareceres; nenhum agente decide sozinho."""
    if data.verdict == "possible_artifact":
        return "rejected", ["Cientista de Dados: provável artefato (traço de chuva / base próxima de zero)."]
    if climate.verdict == "within_normal_variability" and weather.verdict == "low_meteorological_significance":
        return "rejected", [
            "Climatologista: dentro da variabilidade local; Meteorologista: baixa significância. "
            "Anomalia apenas estatística."
        ]
    reasons = [f"Climatologista: {climate.verdict}", f"Meteorologista: {weather.verdict}"]
    if climate.verdict == "within_normal_variability" or weather.verdict == "low_meteorological_significance":
        reasons.append("Pareceres divergentes: mantida para investigação, com ressalva.")
    return "scientifically_reviewed", reasons


def verification_context(anomaly: PrecipitationAnomaly, window_start, window_end, context) -> VerificationContext:
    """Contexto para o Fact-Checker; acumulados cobrem o período do evento."""
    details = (anomaly.scientific_review or {}).get("details") or {}
    event_start = event_end = None
    if details.get("event_start"):
        days = int(details.get("window_days", 1))
        event_start = date.fromisoformat(details["event_start"]) - timedelta(days=days - 1)
        event_end = date.fromisoformat(details["event_end"])
    return VerificationContext(
        anomaly_date=anomaly.anomaly_date,
        window_start=window_start,
        window_end=window_end,
        municipality=context,
        event_start=event_start,
        event_end=event_end,
    )


class Orchestrator:
    name = "orchestrator"

    def __init__(
        self,
        session_factory: sessionmaker,
        researcher: NewsResearcherAgent | None = None,
        fact_checker: FactCheckerAgent | None = None,
        accumulation: AccumulationConfig | None = AccumulationConfig(),
    ):
        self.session_factory = session_factory
        self.data_scientist = DataScientistAgent()
        self.computer_scientist = ComputerScientistAgent()
        self.climatologist = ClimatologistAgent(accumulation or AccumulationConfig())
        self.meteorologist = MeteorologistAgent()
        self.researcher = researcher
        self.fact_checker = fact_checker
        self.accumulation_enabled = accumulation is not None
        self.accumulation = accumulation
        self._persist_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Detecção + revisão científica
    # ------------------------------------------------------------------
    def run_detection(
        self,
        context: MunicipalityContext,
        series: pd.Series,
        quality: DataQualityReport,
        config: DetectionConfig | None = None,
        enso: dict | None = None,
        source: str = "database",
    ) -> DetectionOutcome:
        config = config or DetectionConfig()
        with self.session_factory() as db:
            run = create_run(
                db,
                "detection",
                algorithm_version=config.algorithm_version,
                codigo_ibge=context.codigo_ibge,
                municipality=context.name,
                uf=context.uf,
                period_start=quality.start,
                period_end=quality.end,
                parameters={
                    "source": source,
                    "detection": asdict(config),
                    "accumulation": asdict(self.accumulation) if self.accumulation_enabled else None,
                },
                agents=[
                    {"agent": a, "role": AGENT_NAMES[a]}
                    for a in ("orchestrator", "data_scientist", "climatologist", "meteorologist", "computer_scientist")
                ],
            )
            try:
                outcome = self._detect(db, run, context, series, quality, config, enso)
            except Exception as error:
                db.rollback()
                finish_run(db, run, "failed", {"error": str(error)}, [traceback.format_exc()])
                raise
            return outcome

    def _detect(self, db, run, context, series, quality, config, enso) -> DetectionOutcome:
        result = self.data_scientist.detect(series, quality, config, run_id=str(run.id))
        supplementary = (
            self.climatologist.detect_accumulation_extremes(series, result.scored_period[0])
            if self.accumulation_enabled
            else []
        )
        run_reviews = [
            self.data_scientist.review_run(result),
            self.computer_scientist.audit(series, result, len(supplementary)),
        ]
        anomalies: list[Anomaly] = result.anomalies + supplementary
        blocks = {b.block_start[:4]: asdict(b) for b in result.blocks}

        def review(anomaly: Anomaly):
            return (
                self.data_scientist.review_anomaly(anomaly),
                self.climatologist.review(anomaly, series, context, enso),
                self.meteorologist.review(anomaly, series, context),
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            reviews = list(pool.map(review, anomalies))

        counts = {"detected": 0, "scientifically_reviewed": 0, "rejected": 0}
        candidates = []
        for anomaly, (data, climate, weather) in zip(anomalies, reviews):
            status, reasons = decide_scientific_status(data, climate, weather)
            counts[status] += 1
            if anomaly.detector == "arima_zscore":
                params = {
                    "detector": "arima_zscore",
                    "spec": result.selected_spec,
                    "block": blocks.get(anomaly.model_block),
                    "z_threshold": config.z_threshold,
                }
            else:
                params = {"detector": "accumulation_percentile", **asdict(self.accumulation)}
            decision = {"agent": "orchestrator", "status": status, "reasons": reasons, "decided_at": utcnow().isoformat()}
            save_anomaly(db, run, context, anomaly, status, params, [data, climate, weather], decision)
            if anomaly.direction == "positive" and status != "rejected":
                candidates.append(anomaly.date.isoformat())
        summary = {
            "algorithm_version": config.algorithm_version,
            "selected_spec": result.selected_spec,
            "stationarity": result.stationarity,
            "scored_period": [d.isoformat() for d in result.scored_period],
            "z_threshold": config.z_threshold,
            "anomalies_total": len(anomalies),
            "anomalies_by_detector": {
                "arima_zscore": len(result.anomalies),
                "accumulation_percentile": len(supplementary),
            },
            "anomalies_by_status": counts,
            "detected_dates": sorted({a.date.isoformat() for a in anomalies}),
            "candidate_dates_for_investigation": sorted(set(candidates)),
            "model_selection": result.model_selection,
            "blocks": [asdict(b) for b in result.blocks],
            "diagnostics": result.diagnostics,
            "quality": quality.to_dict(),
            "run_reviews": [r.to_dict() for r in run_reviews],
        }
        finish_run(db, run, "completed", summary)
        log.info("detecção %s: %d anomalias (%d candidatas)", run.id, len(anomalies), len(candidates))
        return DetectionOutcome(run.id, len(anomalies), len(set(candidates)), summary)

    # ------------------------------------------------------------------
    # Investigação de notícias
    # ------------------------------------------------------------------
    def run_investigation(
        self,
        detection_run_id: uuid.UUID,
        context: MunicipalityContext,
        config: InvestigationConfig | None = None,
        only_dates: list[date] | None = None,
    ) -> uuid.UUID:
        if self.researcher is None or self.fact_checker is None:
            raise RuntimeError("Investigação requer News Researcher e Fact-Checker configurados.")
        config = config or InvestigationConfig()
        with self.session_factory() as db:
            detection = db.get(PipelineRun, detection_run_id)
            if detection is None or detection.run_type != "detection":
                raise LookupError(f"Execução de detecção não encontrada: {detection_run_id}")
            if detection.status != "completed":
                raise RuntimeError(f"A detecção {detection_run_id} não terminou (status {detection.status}).")
            stmt = select(PrecipitationAnomaly).where(
                PrecipitationAnomaly.run_id == detection_run_id,
                PrecipitationAnomaly.direction == "positive",
            )
            if not config.include_rejected:
                stmt = stmt.where(PrecipitationAnomaly.status != "rejected")
            if only_dates:
                stmt = stmt.where(PrecipitationAnomaly.anomaly_date.in_(only_dates))
            anomalies = db.scalars(stmt.order_by(PrecipitationAnomaly.anomaly_date)).all()
            run = create_run(
                db,
                "investigation",
                parent_run_id=detection_run_id,
                algorithm_version=ALGORITHM_VERSION,
                codigo_ibge=context.codigo_ibge,
                municipality=context.name,
                uf=context.uf,
                period_start=detection.period_start,
                period_end=detection.period_end,
                parameters={
                    **asdict(config),
                    "only_dates": [d.isoformat() for d in only_dates] if only_dates else None,
                    "search_provider": self.researcher.provider.name,
                    "max_candidates_per_task": self.researcher.max_candidates,
                    "headline_threshold": self.fact_checker.headline_threshold,
                },
                agents=[
                    {"agent": a, "role": AGENT_NAMES[a]}
                    for a in ("orchestrator", "news_researcher", "fact_checker", "software_engineer")
                ],
            )
            for anomaly in anomalies:
                db.add(
                    NewsInvestigation(
                        id=uuid.uuid4(),
                        run_id=run.id,
                        anomaly_id=anomaly.id,
                        status="pending",
                        window_start=anomaly.anomaly_date - timedelta(days=config.window_before),
                        window_end=anomaly.anomaly_date + timedelta(days=config.window_after),
                    )
                )
            db.commit()
            run_id = run.id
        self._process_pending(run_id, context, config)
        return run_id

    def resume_investigation(self, run_id: uuid.UUID, context: MunicipalityContext) -> uuid.UUID:
        with self.session_factory() as db:
            run = db.get(PipelineRun, run_id)
            if run is None or run.run_type != "investigation":
                raise LookupError(f"Investigação não encontrada: {run_id}")
            known = {k: v for k, v in run.parameters.items() if k in InvestigationConfig.__dataclass_fields__}
            config = InvestigationConfig(**known)
            run.status = "processing"
            db.commit()
        self._process_pending(run_id, context, config)
        return run_id

    def _process_pending(self, run_id: uuid.UUID, context: MunicipalityContext, config: InvestigationConfig) -> None:
        with self.session_factory() as db:
            ids = db.scalars(
                select(NewsInvestigation.id).where(
                    NewsInvestigation.run_id == run_id,
                    NewsInvestigation.status.in_(("pending", "processing", "failed")),
                )
            ).all()
        log.info("investigação %s: %d tarefas", run_id, len(ids))
        with ThreadPoolExecutor(max_workers=config.workers) as pool:
            list(pool.map(lambda i: self._investigate(i, context, config), ids))
        self._finalize_investigation(run_id)

    def _investigate(self, investigation_id: uuid.UUID, context: MunicipalityContext, config: InvestigationConfig) -> None:
        with self.session_factory() as db:
            inv = db.get(NewsInvestigation, investigation_id)
            anomaly = inv.anomaly
            inv.status = "processing"
            inv.attempts += 1
            inv.started_at = utcnow()
            inv.errors = []
            db.commit()
            try:
                task = InvestigationTask(
                    anomaly_id=str(anomaly.id),
                    anomaly_date=anomaly.anomaly_date,
                    municipality=context,
                    window_before=config.window_before,
                    window_after=config.window_after,
                    include_neighbors=config.include_neighbors,
                )
                outcome = self.researcher.research(task)
                verification = verification_context(anomaly, task.window_start, task.window_end, context)
                counts = {"verified": 0, "rejected": 0, "pending_verification": 0}
                for checked, candidate in enumerate(outcome.candidates):
                    if config.max_verified is not None and counts["verified"] >= config.max_verified:
                        outcome.queries.append(
                            f"[principais] verificação encerrada após {config.max_verified} aprovadas; "
                            f"{len(outcome.candidates) - checked} candidatas seguintes não foram verificadas"
                        )
                        break
                    decision = self.fact_checker.verify(candidate, verification)
                    counts[decision.status] += 1
                    with self._persist_lock:
                        record_decision(db, candidate, decision, anomaly, inv)
                        db.commit()
                inv.queries = outcome.queries
                inv.sources_consulted = outcome.sources_consulted
                inv.n_found = len(outcome.candidates)
                inv.n_verified = counts["verified"]
                inv.n_rejected = counts["rejected"]
                inv.n_pending = counts["pending_verification"]
                inv.errors = outcome.errors + (
                    [f"{outcome.unresolved_links} links do buscador não puderam ser resolvidos"]
                    if outcome.unresolved_links
                    else []
                )
                all_queries_failed = outcome.errors and len(outcome.errors) >= len(outcome.queries)
                inv.status = "failed" if all_queries_failed else "completed"
            except Exception as error:  # noqa: BLE001 — registrado, nunca escondido
                db.rollback()
                inv = db.get(NewsInvestigation, investigation_id)
                inv.status = "failed"
                inv.errors = [f"{type(error).__name__}: {error}", traceback.format_exc()]
                log.exception("investigação %s falhou", investigation_id)
            inv.finished_at = utcnow()
            db.commit()

    def revalidate_investigation(self, run_id: uuid.UUID, context: MunicipalityContext) -> dict:
        """Reverifica (Fact-Checker) todas as notícias já vinculadas a uma investigação.

        Não faz novas buscas: reconstrói a candidata a partir do que o News
        Researcher registrou (URL, manchete, fonte e data alegadas) e reacessa a
        página. Cada nova decisão vira uma ``news_verification_attempt``.
        """
        if self.fact_checker is None:
            raise RuntimeError("Revalidação requer o Fact-Checker.")
        with self.session_factory() as db:
            investigations = db.scalars(select(NewsInvestigation).where(NewsInvestigation.run_id == run_id)).all()
            if not investigations:
                raise LookupError(f"Investigação sem tarefas: {run_id}")
            for inv in investigations:
                anomaly = inv.anomaly
                verification = verification_context(anomaly, inv.window_start, inv.window_end, context)
                links = db.scalars(select(AnomalyNews).where(AnomalyNews.investigation_id == inv.id)).all()
                counts = {"verified": 0, "rejected": 0, "pending_verification": 0}
                for link in links:
                    news = link.news
                    claims = news.discovered_by or {}
                    claimed = claims.get("claimed_published_at")
                    candidate = NewsCandidate(
                        url=news.original_url,
                        headline=claims.get("claimed_headline") or news.headline,
                        source=claims.get("claimed_source") or news.source,
                        claimed_published_at=datetime.fromisoformat(claimed) if claimed else None,
                        query=claims.get("query", ""),
                        provider=claims.get("provider", ""),
                        search_link="",
                    )
                    decision = self.fact_checker.verify(candidate, verification)
                    counts[decision.status] += 1
                    record_decision(db, candidate, decision, anomaly, inv)
                inv.n_verified = counts["verified"]
                inv.n_rejected = counts["rejected"]
                inv.n_pending = counts["pending_verification"]
                db.commit()
        return self._finalize_investigation(run_id)

    def _finalize_investigation(self, run_id: uuid.UUID) -> dict:
        with self.session_factory() as db:
            run = db.get(PipelineRun, run_id)
            rows = db.execute(
                select(NewsInvestigation, PrecipitationAnomaly.anomaly_date)
                .join(PrecipitationAnomaly, PrecipitationAnomaly.id == NewsInvestigation.anomaly_id)
                .where(NewsInvestigation.run_id == run_id)
                .order_by(PrecipitationAnomaly.anomaly_date)
            ).all()
            by_status: dict[str, list[str]] = {}
            for inv, day in rows:
                by_status.setdefault(inv.status, []).append(day.isoformat())
            summary = {
                "dates_investigated": [d.isoformat() for _, d in rows],
                "investigations_by_status": {k: len(v) for k, v in by_status.items()},
                "failed_dates": by_status.get("failed", []),
                "unprocessed_dates": by_status.get("pending", []) + by_status.get("processing", []),
                "dates_without_results": [d.isoformat() for inv, d in rows if inv.status == "completed" and inv.n_found == 0],
                "dates_with_verified_news": [d.isoformat() for inv, d in rows if inv.n_verified > 0],
                "news_found": sum(inv.n_found for inv, _ in rows),
                "news_verified": sum(inv.n_verified for inv, _ in rows),
                "news_rejected": sum(inv.n_rejected for inv, _ in rows),
                "news_pending": sum(inv.n_pending for inv, _ in rows),
                "queries": sum(len(inv.queries) for inv, _ in rows),
            }
            errors = [
                {"anomaly_date": d.isoformat(), "errors": inv.errors[:3]} for inv, d in rows if inv.errors
            ]
            done = all(inv.status == "completed" for inv, _ in rows)
            finish_run(db, run, "completed" if done else "failed", summary, errors)
            return summary
