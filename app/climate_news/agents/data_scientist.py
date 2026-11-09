"""Agente 4 — Cientista de Dados.

Executa a detecção ARIMA + Z-Score e revisa qualidade dos dados e resíduos.
Também marca anomalias que podem ser artefatos de qualidade dos dados, para
que não sejam interpretadas como eventos climáticos.
"""

from __future__ import annotations

import pandas as pd

from app.climate_news.agents.base import AgentReport
from app.climate_news.detection.arima_zscore import (
    Anomaly,
    DetectionConfig,
    DetectionResult,
    detect_anomalies,
)
from app.climate_news.detection.preparation import DataQualityReport

TRACE_MM = 1.0


class DataScientistAgent:
    name = "data_scientist"

    def detect(
        self,
        series: pd.Series,
        quality: DataQualityReport,
        config: DetectionConfig,
        run_id: str | None = None,
    ) -> DetectionResult:
        return detect_anomalies(series, config, quality, run_id=run_id)

    def review_run(self, result: DetectionResult) -> AgentReport:
        q = result.quality
        d = result.diagnostics
        notes: list[str] = []
        verdict = "acceptable"
        if q.missing_fraction > 0.10:
            verdict = "acceptable_with_caveats"
            notes.append(f"{q.missing_fraction:.1%} dos dias estão ausentes; a cobertura limita a detecção.")
        elif q.n_missing:
            notes.append(
                f"{q.n_missing} dias ausentes ({q.missing_fraction:.1%}) mantidos como NaN "
                f"({q.n_incomplete_aggregation} por agregação ERA5 incompleta)."
            )
        if q.zero_fraction > 0.6:
            notes.append(
                f"{q.zero_fraction:.0%} dos dias válidos sem chuva: distribuição com massa em zero; "
                "log1p reduz, mas não elimina, a assimetria."
            )
        if q.n_negative or q.n_implausible or q.n_duplicates_conflicting:
            verdict = "acceptable_with_caveats"
            notes.append(
                f"Inconsistências removidas: {q.n_negative} negativos, {q.n_implausible} implausíveis, "
                f"{q.n_duplicates_conflicting} duplicatas conflitantes."
            )
        lb = d.get("ljung_box_pvalues", {})
        if lb and min(lb.values()) < 0.01:
            verdict = "acceptable_with_caveats"
            notes.append(f"Autocorrelação residual significativa (Ljung-Box {lb}); o modelo não capturou toda a dependência.")
        elif lb:
            notes.append(f"Resíduos sem autocorrelação significativa a 1% (Ljung-Box {lb}).")
        ratio = d.get("positive_rate_ratio_to_gaussian")
        if ratio is not None:
            notes.append(
                f"Taxa de Z > limiar = {d['positive_rate']:.3%}, {ratio}× a esperada sob normalidade "
                f"(assimetria dos resíduos = {d.get('z_skewness')}). O limiar |Z| > 3 não tem "
                "interpretação probabilística exata para chuva."
            )
        if not d.get("all_blocks_converged", True):
            verdict = "acceptable_with_caveats"
            notes.append("Algum bloco anual não convergiu; ver parâmetros por bloco.")
        return AgentReport(self.name, verdict, notes, {"quality": q.to_dict(), "diagnostics": d})

    def review_anomaly(self, anomaly: Anomaly) -> AgentReport:
        flags = list(anomaly.quality_flags)
        notes = []
        verdict = "data_ok"
        if anomaly.observed_mm < TRACE_MM:
            verdict = "possible_artifact"
            flags.append("trace_precipitation")
            notes.append(
                f"Precipitação observada {anomaly.observed_mm} mm < {TRACE_MM} mm: anomalia "
                "decorre da base próxima de zero na escala log, não de chuva relevante."
            )
        if "previous_day_missing" in flags:
            notes.append("Dia anterior ausente: a previsão de um passo foi feita sem a observação imediata.")
        if "window_with_missing_day" in flags:
            notes.append("Janela do acumulado contém dia ausente; soma escalonada pelos dias válidos.")
        if not notes:
            notes.append("Sem problemas de qualidade associados ao dia.")
        return AgentReport(self.name, verdict, notes, {"quality_flags": flags})
