"""Detector suplementar de acumulados extremos (proposto pelo Climatologista).

O ARIMA + Z-Score detecta *mudanças inesperadas* em relação ao passado
recente. Chuvas persistentes por vários dias são, por construção, previstas
pelo próprio ARIMA (a persistência entra no modelo) e passam despercebidas,
mesmo quando o acumulado é extremo — caso das enchentes de abril/maio de 2024
em Porto Alegre (20–36 mm/dia durante ~10 dias).

Este detector cobre essa lacuna sem substituir o ARIMA:

- calcula somas móveis de ``k`` dias (padrão 3 e 5);
- o limiar do ano Y é o percentil P99 das somas de todos os anos anteriores a
  Y (janela expansiva, sem dados futuros);
- dias consecutivos acima do limiar formam um evento; a data da anomalia é o
  dia de maior excedência relativa ao limiar;
- o escore padronizado é ``(log1p(S) − μ_m) / σ_m`` com μ_m, σ_m das somas
  do mesmo mês em anos anteriores (anomalia climatológica padronizada).

Cada anomalia é registrada com ``detector = "accumulation_percentile"`` para
nunca ser confundida com as anomalias do ARIMA.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.climate_news.detection.arima_zscore import Anomaly


@dataclass
class AccumulationConfig:
    windows: tuple[int, ...] = (3, 5)
    percentile: float = 0.99
    max_missing_per_window: int = 1
    min_prior_days: int = 365

    def __post_init__(self):
        if not 0.5 < self.percentile < 1:
            raise ValueError("percentile deve estar entre 0.5 e 1")
        if any(k < 2 for k in self.windows):
            raise ValueError("as janelas de acumulado devem ter pelo menos 2 dias")


def rolling_accumulation(series: pd.Series, days: int, max_missing: int = 1) -> pd.Series:
    """Soma móvel de ``days`` dias terminando em cada data.

    Com até ``max_missing`` dias ausentes, a soma é escalonada pela fração de
    dias válidos (média da janela × ``days``); com mais ausências fica NaN.
    """
    window = series.rolling(days, min_periods=days - max_missing)
    return window.sum() * days / window.count()


def _severity(ratio: float) -> str:
    if ratio >= 1.5:
        return "very_strong"
    if ratio >= 1.2:
        return "strong"
    return "moderate"


def detect_accumulation_extremes(
    series: pd.Series,
    scored_start: pd.Timestamp,
    config: AccumulationConfig | None = None,
) -> list[Anomaly]:
    config = config or AccumulationConfig()
    series = series.asfreq("D")
    accumulations = {
        k: rolling_accumulation(series, k, config.max_missing_per_window) for k in config.windows
    }

    rows = []
    for year in range(scored_start.year, series.index[-1].year + 1):
        prior_end = pd.Timestamp(year - 1, 12, 31)
        block = slice(pd.Timestamp(year, 1, 1), pd.Timestamp(year, 12, 31))
        for k, acc in accumulations.items():
            prior = acc[:prior_end].dropna()
            if len(prior) < config.min_prior_days:
                continue
            threshold = float(prior.quantile(config.percentile))
            values = acc.loc[block]
            for day, value in values[values >= threshold].items():
                month_prior = np.log1p(prior[prior.index.month == day.month])
                mu = float(month_prior.mean())
                sd = float(month_prior.std(ddof=1)) or np.nan
                rows.append(
                    {
                        "date": day,
                        "k": k,
                        "value": float(value),
                        "threshold": threshold,
                        "ratio": float(value) / threshold if threshold > 0 else np.inf,
                        "z": (np.log1p(value) - mu) / sd,
                        "mu": mu,
                        "prior_years": f"{prior.index[0].year}-{prior.index[-1].year}",
                    }
                )
    if not rows:
        return []

    flagged = pd.DataFrame(rows).sort_values(["date", "ratio"], ascending=[True, False])
    days = pd.DatetimeIndex(sorted(flagged["date"].unique()))
    event_ids = np.cumsum(np.r_[1, (np.diff(days.values).astype("timedelta64[D]").astype(int) > 1)])
    event_of_day = dict(zip(days, event_ids))
    flagged["event"] = flagged["date"].map(event_of_day)

    anomalies: list[Anomaly] = []
    for event, group in flagged.groupby("event"):
        peak = group.loc[group["ratio"].idxmax()]
        k = int(peak["k"])
        predicted = float(np.expm1(peak["mu"]))
        daily_in_window = series.loc[peak["date"] - pd.Timedelta(days=k - 1) : peak["date"]]
        anomalies.append(
            Anomaly(
                date=peak["date"].date(),
                observed_mm=round(float(peak["value"]), 3),
                predicted_mm=round(predicted, 3),
                residual=round(float(np.log1p(peak["value"]) - peak["mu"]), 6),
                residual_mm=round(float(peak["value"]) - predicted, 3),
                z_score=round(float(peak["z"]), 4),
                direction="positive",
                severity=_severity(float(peak["ratio"])),
                classification=f"climatological_extreme_accumulation_{k}d",
                model_block=str(peak["date"].year),
                episode_id=f"A{event}",
                quality_flags=(["window_with_missing_day"] if daily_in_window.isna().any() else []),
                detector="accumulation_percentile",
                accumulation_days=k,
                details={
                    "window_days": k,
                    "accumulated_mm": round(float(peak["value"]), 2),
                    "threshold_mm": round(float(peak["threshold"]), 2),
                    "percentile": config.percentile,
                    "exceedance_ratio": round(float(peak["ratio"]), 3),
                    "threshold_reference_years": peak["prior_years"],
                    "event_start": str(group["date"].min().date()),
                    "event_end": str(group["date"].max().date()),
                    "event_days_above_threshold": int(group["date"].nunique()),
                    "windows_exceeded": sorted(int(x) for x in group["k"].unique()),
                    "daily_mm_in_window": {
                        str(d.date()): (None if pd.isna(v) else round(float(v), 2))
                        for d, v in daily_in_window.items()
                    },
                    "predicted_mm_meaning": "mediana geométrica climatológica do acumulado no mesmo mês (anos anteriores)",
                },
            )
        )
    return anomalies
