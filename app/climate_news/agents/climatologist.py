"""Agente 5 — Climatologista.

Interpreta cada anomalia à luz da climatologia local: o mesmo volume pode ser
extremo em uma região e habitual em outra. Usa apenas anos anteriores ao da
anomalia como referência climatológica, coerente com a detecção.

Também é responsável pelo detector suplementar de acumulados extremos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from app.climate_news.agents.base import AgentReport, MunicipalityContext
from app.climate_news.detection.accumulation import (
    AccumulationConfig,
    detect_accumulation_extremes,
    rolling_accumulation,
)
from app.climate_news.detection.arima_zscore import Anomaly

UNUSUAL_SEASON_MIN_MM = 10.0

MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

# Teleconexões amplamente documentadas; usadas só como contexto.
ENSO_NOTES = {
    "Sul": {
        "el_nino": "El Niño costuma favorecer chuva acima da média no Sul (sobretudo primavera e inverno).",
        "la_nina": "La Niña costuma favorecer chuva abaixo da média no Sul.",
    },
    "Norte": {
        "el_nino": "El Niño costuma favorecer chuva abaixo da média no norte da Amazônia.",
        "la_nina": "La Niña costuma favorecer chuva acima da média no norte da Amazônia.",
    },
    "Nordeste": {
        "el_nino": "El Niño costuma favorecer chuva abaixo da média no norte do Nordeste.",
        "la_nina": "La Niña costuma favorecer chuva acima da média no norte do Nordeste.",
    },
}


def enso_phase(oni: float | None) -> str | None:
    if oni is None:
        return None
    if oni >= 0.5:
        return "el_nino"
    if oni <= -0.5:
        return "la_nina"
    return "neutral"


class ClimatologistAgent:
    name = "climatologist"

    def __init__(self, accumulation: AccumulationConfig | None = None):
        self.accumulation = accumulation or AccumulationConfig()

    def detect_accumulation_extremes(self, series: pd.Series, scored_start) -> list[Anomaly]:
        return detect_accumulation_extremes(series, pd.Timestamp(scored_start), self.accumulation)

    def review(
        self,
        anomaly: Anomaly,
        series: pd.Series,
        context: MunicipalityContext,
        enso: dict[tuple[int, int], float] | None = None,
    ) -> AgentReport:
        day = pd.Timestamp(anomaly.date)
        prior = series[: pd.Timestamp(day.year - 1, 12, 31)].dropna()
        notes: list[str] = []
        if len(prior) < 365:
            prior = series.drop(day, errors="ignore").dropna()
            notes.append("Menos de um ano anterior disponível: climatologia calculada com a série completa.")
        reference = f"{prior.index[0].date()}..{prior.index[-1].date()}"

        monthly = prior.resample("MS").sum(min_count=20)
        month_means = monthly.groupby(monthly.index.month).mean()
        rainy_months = [int(m) for m in month_means.index[month_means > month_means.mean()]]
        in_rainy_season = day.month in rainy_months
        metrics: dict = {
            "reference_period": reference,
            "monthly_mean_mm": {MONTHS_PT[int(m) - 1]: round(float(v), 1) for m, v in month_means.items()},
            "rainy_season_months": [MONTHS_PT[m - 1] for m in rainy_months],
            "in_rainy_season": in_rainy_season,
        }

        if anomaly.detector == "accumulation_percentile":
            k = anomaly.accumulation_days
            acc_prior = rolling_accumulation(prior, k).dropna()
            percentile = float(stats.percentileofscore(acc_prior, anomaly.observed_mm, kind="weak"))
            metrics.update(
                {
                    "accumulation_days": k,
                    "accumulation_percentile_all_days": round(percentile, 2),
                    "accumulation_p99_mm": round(float(acc_prior.quantile(0.99)), 1),
                    "accumulation_max_prior_mm": round(float(acc_prior.max()), 1),
                }
            )
            if anomaly.observed_mm > acc_prior.max():
                verdict = "record_accumulation"
                notes.append(
                    f"Acumulado de {k} dias ({anomaly.observed_mm:.0f} mm) supera o máximo do período de referência "
                    f"({acc_prior.max():.0f} mm)."
                )
            else:
                verdict = "exceptional_accumulation"
                notes.append(
                    f"Acumulado de {k} dias ({anomaly.observed_mm:.0f} mm) no percentil {percentile:.1f} "
                    f"dos acumulados de {k} dias de {reference}."
                )
        else:
            wet = prior[prior >= 1.0]
            p95, p99 = float(wet.quantile(0.95)), float(wet.quantile(0.99))
            difference = np.abs(prior.index.dayofyear.to_numpy() - day.dayofyear)
            distance = np.minimum(difference, 366 - difference)  # distância circular no ano
            window = prior[distance <= 15]
            seasonal = window[window >= 1.0]
            seasonal_pct = (
                float(stats.percentileofscore(seasonal, anomaly.observed_mm, kind="weak"))
                if len(seasonal) >= 20
                else None
            )
            # na estação seca há poucos dias chuvosos para um percentil entre dias
            # chuvosos; o percentil entre TODOS os dias da época (zeros incluídos)
            # sempre tem amostra e mostra se chover esse volume é raro na época
            all_days_pct = float(stats.percentileofscore(window, anomaly.observed_mm, kind="weak"))
            wet_share = float((window >= 1.0).mean())
            overall_pct = float(stats.percentileofscore(wet, anomaly.observed_mm, kind="weak"))
            metrics.update(
                {
                    "wet_day_p95_mm": round(p95, 1),
                    "wet_day_p99_mm": round(p99, 1),
                    "wet_day_percentile": round(overall_pct, 2),
                    "seasonal_wet_day_percentile": None if seasonal_pct is None else round(seasonal_pct, 2),
                    "seasonal_all_days_percentile": round(all_days_pct, 2),
                    "seasonal_wet_day_frequency": round(wet_share, 3),
                    "max_prior_daily_mm": round(float(prior.max()), 1),
                }
            )
            if anomaly.observed_mm >= p99:
                verdict = "exceptional_for_location"
                notes.append(f"{anomaly.observed_mm:.1f} mm ≥ P99 dos dias chuvosos ({p99:.1f} mm) em {reference}.")
            elif anomaly.observed_mm >= p95:
                verdict = "very_heavy_for_location"
                notes.append(f"{anomaly.observed_mm:.1f} mm entre P95 ({p95:.1f}) e P99 ({p99:.1f}) dos dias chuvosos.")
            elif seasonal_pct is not None and seasonal_pct >= 95:
                verdict = "unusual_for_season"
                notes.append(
                    f"{anomaly.observed_mm:.1f} mm é comum no ano todo (percentil {overall_pct:.0f}), "
                    f"mas incomum para a época (percentil sazonal {seasonal_pct:.0f})."
                )
            elif anomaly.observed_mm >= UNUSUAL_SEASON_MIN_MM and all_days_pct >= 99:
                verdict = "unusual_for_season"
                notes.append(
                    f"Época seca: só {wet_share:.0%} dos dias com chuva ≥ 1 mm em ±15 dias; "
                    f"{anomaly.observed_mm:.1f} mm está no percentil {all_days_pct:.1f} de todos os dias da época."
                )
            else:
                verdict = "within_normal_variability"
                notes.append(
                    f"{anomaly.observed_mm:.1f} mm está dentro da variabilidade local "
                    f"(percentil {overall_pct:.0f} dos dias chuvosos)."
                )

        season = "estação chuvosa" if in_rainy_season else "estação menos chuvosa"
        notes.append(f"{MONTHS_PT[day.month - 1]} é {season} em {context.label()} (médias mensais {reference}).")

        oni = (enso or {}).get((day.year, day.month))
        phase = enso_phase(oni)
        metrics["oni"] = oni
        metrics["enso_phase"] = phase
        if phase:
            remark = ENSO_NOTES.get(context.region or "", {}).get(phase)
            text = f"ONI {oni:+.2f} ({phase})."
            if remark:
                text += f" {remark}"
            notes.append(text + " Contexto, não evidência causal.")
        return AgentReport(self.name, verdict, notes, metrics)
