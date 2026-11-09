"""Etapas 2 a 4 — ARIMA + Z-Score para anomalias de precipitação diária.

Pode ser usado como biblioteca (``detect_anomalies``) ou como script
independente::

    python -m app.climate_news.detection.arima_zscore --csv chuva.csv \\
        --date-col date --value-col precipitation_mm --out-csv anomalias.csv

Método (resumo; ver docs/anomalias_noticias/ARQUITETURA.md):

1. ``y_t = log1p(P_t)`` reduz a assimetria da chuva diária.
2. Estacionariedade avaliada com ADF + KPSS no período inicial de treino;
   ``d = 1`` somente quando os dois testes concordam que há raiz unitária.
3. A sazonalidade anual entra como regressores de Fourier (regressão com
   erros ARMA). Um SARIMA com período 365 é inviável (estado com centenas de
   dimensões) e é substituído por essa formulação equivalente e barata. O
   critério BIC decide entre o modelo com e sem sazonalidade.
4. Ordem (p, q) escolhida por BIC no período inicial de treino.
5. Janela expansiva com reajuste anual: os parâmetros usados no ano Y são
   estimados apenas com dados anteriores a Y, e cada previsão de um passo usa
   apenas observações anteriores ao dia previsto. Não há vazamento de dados.
6. ``e_t = y_t − ŷ_t`` e ``Z_t = (e_t − μ_e) / σ_e``, com μ_e e σ_e
   calculados nos resíduos de um passo do próprio período de treino do bloco
   (passado), também sem usar informação futura.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
import warnings
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tools.sm_exceptions import ConvergenceWarning, InterpolationWarning
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller, kpss

from app.climate_news import ALGORITHM_VERSION
from app.climate_news.detection.preparation import (
    DataQualityReport,
    aggregate_era5_12h_to_daily,
    prepare_daily_series,
)

GAUSSIAN_TAIL_3 = float(stats.norm.sf(3.0))


@dataclass
class DetectionConfig:
    z_threshold: float = 3.0
    transform: str = "log1p"  # "log1p" | "none"
    max_p: int = 2
    max_q: int = 2
    seasonal: str = "auto"  # "auto" | "fourier" | "none"
    fourier_harmonics: int = 3
    initial_train_years: int = 2
    burn_in_days: int = 30
    min_reference_residuals: int = 300
    maxiter: int = 200
    algorithm_version: str = ALGORITHM_VERSION

    def __post_init__(self):
        if self.z_threshold <= 0:
            raise ValueError("z_threshold deve ser positivo")
        if self.transform not in {"log1p", "none"}:
            raise ValueError("transform deve ser 'log1p' ou 'none'")
        if self.seasonal not in {"auto", "fourier", "none"}:
            raise ValueError("seasonal deve ser 'auto', 'fourier' ou 'none'")
        if self.initial_train_years < 1:
            raise ValueError("initial_train_years deve ser >= 1")


@dataclass
class ModelBlock:
    """Modelo usado para pontuar um bloco (ano) da série."""

    block_start: str
    block_end: str
    train_start: str
    train_end: str
    order: tuple[int, int, int]
    seasonal: str
    params: dict[str, float]
    aic: float
    bic: float
    converged: bool
    residual_mean: float
    residual_std: float
    n_reference_residuals: int
    fit_seconds: float


@dataclass
class Anomaly:
    date: date
    observed_mm: float
    predicted_mm: float
    residual: float
    residual_mm: float
    z_score: float
    direction: str  # "positive" | "negative"
    severity: str
    classification: str
    model_block: str
    episode_id: str | None = None
    quality_flags: list[str] = field(default_factory=list)
    detector: str = "arima_zscore"  # "arima_zscore" | "accumulation_percentile"
    accumulation_days: int = 1
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["date"] = self.date.isoformat()
        return data


@dataclass
class DetectionResult:
    run_id: str
    config: DetectionConfig
    quality: DataQualityReport
    stationarity: dict
    model_selection: list[dict]
    selected_spec: dict
    blocks: list[ModelBlock]
    daily: pd.DataFrame
    anomalies: list[Anomaly]
    diagnostics: dict
    scored_period: tuple[date, date]
    runtime_seconds: float

    @property
    def positive_anomalies(self) -> list[Anomaly]:
        return [a for a in self.anomalies if a.direction == "positive"]

    def anomalies_frame(self) -> pd.DataFrame:
        return pd.DataFrame([a.to_dict() for a in self.anomalies])

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "algorithm_version": self.config.algorithm_version,
            "config": asdict(self.config),
            "quality": self.quality.to_dict(),
            "stationarity": self.stationarity,
            "model_selection": self.model_selection,
            "selected_spec": self.selected_spec,
            "blocks": [asdict(b) for b in self.blocks],
            "scored_period": [d.isoformat() for d in self.scored_period],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "diagnostics": self.diagnostics,
            "runtime_seconds": round(self.runtime_seconds, 3),
        }


# ---------------------------------------------------------------------------
# Componentes do modelo
# ---------------------------------------------------------------------------


def fourier_terms(index: pd.DatetimeIndex, harmonics: int) -> pd.DataFrame:
    angle = 2 * np.pi * (index.dayofyear.to_numpy() - 1) / 365.25
    columns = {}
    for k in range(1, harmonics + 1):
        columns[f"sin{k}"] = np.sin(k * angle)
        columns[f"cos{k}"] = np.cos(k * angle)
    return pd.DataFrame(columns, index=index)


def stationarity_tests(y: pd.Series) -> dict:
    values = y.dropna().to_numpy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InterpolationWarning)
        warnings.simplefilter("ignore", FutureWarning)
        adf_stat, adf_p, *_ = adfuller(values, autolag="AIC")
        kpss_stat, kpss_p, *_ = kpss(values, regression="c", nlags="auto")
    unit_root = adf_p > 0.05 and kpss_p < 0.05
    return {
        "adf_statistic": round(float(adf_stat), 4),
        "adf_pvalue": round(float(adf_p), 4),
        "kpss_statistic": round(float(kpss_stat), 4),
        "kpss_pvalue": round(float(kpss_p), 4),
        "d": 1 if unit_root else 0,
        "decision": (
            "raiz unitária (ADF não rejeita e KPSS rejeita estacionariedade): d=1"
            if unit_root
            else "série tratada como estacionária: d=0"
        ),
    }


def _build_model(y: pd.Series, exog: pd.DataFrame | None, order) -> SARIMAX:
    trend = "c" if order[1] == 0 else "n"
    return SARIMAX(
        y,
        exog=exog,
        order=order,
        trend=trend,
        enforce_stationarity=True,
        enforce_invertibility=True,
    )


def _fit(model: SARIMAX, maxiter: int, start_params=None):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        result = model.fit(disp=False, maxiter=maxiter, start_params=start_params)
    converged = bool(result.mle_retvals.get("converged", True)) and not any(
        issubclass(w.category, ConvergenceWarning) for w in caught
    )
    return result, converged


def _severity(z: float) -> str:
    magnitude = abs(z)
    if magnitude >= 5:
        return "very_strong"
    if magnitude >= 4:
        return "strong"
    return "moderate"


def _assign_episodes(anomalies: list[Anomaly], max_gap_days: int = 1) -> None:
    """Agrupa anomalias positivas próximas em episódios (E1, E2, ...)."""
    positives = sorted(
        (a for a in anomalies if a.direction == "positive" and a.detector == "arima_zscore"),
        key=lambda a: a.date,
    )
    episode = 0
    previous: date | None = None
    for anomaly in positives:
        if previous is None or (anomaly.date - previous).days > max_gap_days + 1:
            episode += 1
        anomaly.episode_id = f"E{episode}"
        previous = anomaly.date


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def detect_anomalies(
    series: pd.Series,
    config: DetectionConfig | None = None,
    quality: DataQualityReport | None = None,
    run_id: str | None = None,
) -> DetectionResult:
    """Detecta anomalias em uma série diária (índice diário, valores em mm)."""
    config = config or DetectionConfig()
    started = time.perf_counter()
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("A série precisa de índice DatetimeIndex diário.")
    if quality is None:
        series, quality = prepare_daily_series(
            series.rename("precipitation_mm").rename_axis("date").reset_index()
        )
    series = series.asfreq("D")

    y = np.log1p(series) if config.transform == "log1p" else series.copy()
    exog_all = fourier_terms(series.index, config.fourier_harmonics)

    first_day = series.index[0]
    first_test_year = first_day.year + config.initial_train_years
    if first_day.dayofyear > 1:
        first_test_year += 1
    last_year = series.index[-1].year
    if first_test_year > last_year:
        raise ValueError(
            "Série curta demais: são necessários pelo menos "
            f"{config.initial_train_years} anos completos de treino antes do período pontuado."
        )
    initial_train = y[: pd.Timestamp(first_test_year - 1, 12, 31)]
    if initial_train.notna().sum() < config.min_reference_residuals:
        raise ValueError("Dados válidos insuficientes no período inicial de treino.")

    stationarity = stationarity_tests(initial_train)
    d = stationarity["d"]

    # ---- seleção do modelo (somente período inicial de treino) ----------
    seasonal_options = ["none", "fourier"] if config.seasonal == "auto" else [config.seasonal]
    candidates = []
    for seasonal in seasonal_options:
        exog = exog_all.loc[initial_train.index] if seasonal == "fourier" else None
        for p in range(config.max_p + 1):
            for q in range(config.max_q + 1):
                if p == q == 0 and seasonal == "none":
                    continue
                order = (p, d, q)
                try:
                    result, converged = _fit(_build_model(initial_train, exog, order), config.maxiter)
                except Exception as error:  # noqa: BLE001 — registra e segue
                    candidates.append({"order": order, "seasonal": seasonal, "error": str(error)})
                    continue
                candidates.append(
                    {
                        "order": order,
                        "seasonal": seasonal,
                        "aic": round(float(result.aic), 3),
                        "bic": round(float(result.bic), 3),
                        "converged": converged,
                    }
                )
    valid = [c for c in candidates if "bic" in c and c["converged"]] or [
        c for c in candidates if "bic" in c
    ]
    if not valid:
        raise RuntimeError("Nenhum modelo ARIMA pôde ser ajustado.")
    best = min(valid, key=lambda c: c["bic"])
    order = tuple(best["order"])
    seasonal = best["seasonal"]
    selected_spec = {
        "order": list(order),
        "seasonal": seasonal,
        "fourier_harmonics": config.fourier_harmonics if seasonal == "fourier" else 0,
        "transform": config.transform,
        "criterion": "BIC",
        "selected_on": [str(initial_train.index[0].date()), str(initial_train.index[-1].date())],
    }

    # ---- pontuação fora da amostra com reajuste anual ---------------------
    blocks: list[ModelBlock] = []
    frames = []
    start_params = None
    for year in range(first_test_year, last_year + 1):
        block_start = pd.Timestamp(year, 1, 1)
        block_end = min(pd.Timestamp(year, 12, 31), series.index[-1])
        train = y[: block_start - pd.Timedelta(days=1)]
        exog_train = exog_all.loc[train.index] if seasonal == "fourier" else None
        t0 = time.perf_counter()
        fitted, converged = _fit(_build_model(train, exog_train, order), config.maxiter, start_params)
        start_params = fitted.params.to_numpy()

        reference = fitted.resid.iloc[config.burn_in_days :].where(train.iloc[config.burn_in_days :].notna())
        reference = reference.dropna()
        mu, sigma = float(reference.mean()), float(reference.std(ddof=1))

        upto = y[:block_end]
        exog_upto = exog_all.loc[upto.index] if seasonal == "fourier" else None
        filtered = _build_model(upto, exog_upto, order).filter(fitted.params)
        prediction = filtered.fittedvalues.loc[block_start:block_end]
        observed = y.loc[block_start:block_end]
        residual = observed - prediction
        z = (residual - mu) / sigma
        label = f"{year}"
        frames.append(
            pd.DataFrame(
                {
                    "observed_mm": series.loc[block_start:block_end],
                    "prediction_t": prediction,
                    "residual": residual,
                    "z_score": z,
                    "model_block": label,
                }
            )
        )
        blocks.append(
            ModelBlock(
                block_start=str(block_start.date()),
                block_end=str(block_end.date()),
                train_start=str(train.index[0].date()),
                train_end=str(train.index[-1].date()),
                order=order,
                seasonal=seasonal,
                params={k: round(float(v), 6) for k, v in fitted.params.items()},
                aic=round(float(fitted.aic), 3),
                bic=round(float(fitted.bic), 3),
                converged=converged,
                residual_mean=round(mu, 6),
                residual_std=round(sigma, 6),
                n_reference_residuals=int(len(reference)),
                fit_seconds=round(time.perf_counter() - t0, 3),
            )
        )

    daily = pd.concat(frames)
    if config.transform == "log1p":
        daily["predicted_mm"] = np.expm1(daily["prediction_t"]).clip(lower=0)
    else:
        daily["predicted_mm"] = daily["prediction_t"].clip(lower=0)
    daily["residual_mm"] = daily["observed_mm"] - daily["predicted_mm"]
    previous_missing = series.shift(1).isna().reindex(daily.index)

    anomalies: list[Anomaly] = []
    threshold = config.z_threshold
    flagged = daily[daily["z_score"].abs() > threshold]
    for day, row in flagged.iterrows():
        direction = "positive" if row.z_score > 0 else "negative"
        flags = ["previous_day_missing"] if previous_missing.loc[day] else []
        anomalies.append(
            Anomaly(
                date=day.date(),
                observed_mm=round(float(row.observed_mm), 3),
                predicted_mm=round(float(row.predicted_mm), 3),
                residual=round(float(row.residual), 6),
                residual_mm=round(float(row.residual_mm), 3),
                z_score=round(float(row.z_score), 4),
                direction=direction,
                severity=_severity(row.z_score),
                classification=(
                    "statistical_anomaly_above_expected"
                    if direction == "positive"
                    else "statistical_anomaly_below_expected"
                ),
                model_block=row.model_block,
                quality_flags=flags,
            )
        )
    _assign_episodes(anomalies)

    diagnostics = residual_diagnostics(daily, blocks, threshold)
    return DetectionResult(
        run_id=run_id or str(uuid.uuid4()),
        config=config,
        quality=quality,
        stationarity=stationarity,
        model_selection=candidates,
        selected_spec=selected_spec,
        blocks=blocks,
        daily=daily,
        anomalies=anomalies,
        diagnostics=diagnostics,
        scored_period=(daily.index[0].date(), daily.index[-1].date()),
        runtime_seconds=time.perf_counter() - started,
    )


def residual_diagnostics(daily: pd.DataFrame, blocks: list[ModelBlock], threshold: float) -> dict:
    """Diagnósticos dos resíduos fora da amostra (z) e estabilidade do modelo."""
    z = daily["z_score"].dropna()
    n = len(z)
    result: dict = {"n_scored": int(n)}
    if n < 30:
        return result
    lags = [lag for lag in (1, 7, 30) if lag < n // 2]
    ljung = acorr_ljungbox(z.to_numpy(), lags=lags, return_df=True)
    jb_stat, jb_p = stats.jarque_bera(z.to_numpy())
    positive_rate = float((z > threshold).mean())
    negative_rate = float((z < -threshold).mean())
    expected = float(stats.norm.sf(threshold))
    result.update(
        {
            "z_mean": round(float(z.mean()), 4),
            "z_std": round(float(z.std()), 4),
            "z_skewness": round(float(stats.skew(z)), 4),
            "z_excess_kurtosis": round(float(stats.kurtosis(z)), 4),
            "jarque_bera_pvalue": float(jb_p),
            "ljung_box_pvalues": {f"lag_{lag}": float(p) for lag, p in zip(lags, ljung["lb_pvalue"])},
            "acf_lag1": round(float(z.autocorr(1)), 4),
            "positive_rate": round(positive_rate, 6),
            "negative_rate": round(negative_rate, 6),
            "gaussian_expected_rate_each_tail": round(expected, 6),
            "positive_rate_ratio_to_gaussian": round(positive_rate / expected, 2),
            "all_blocks_converged": all(b.converged for b in blocks),
        }
    )
    params = pd.DataFrame([b.params for b in blocks])
    arma_cols = [c for c in params.columns if c.startswith(("ar.", "ma.", "sigma2"))]
    result["parameter_stability"] = {
        col: {
            "min": round(float(params[col].min()), 4),
            "max": round(float(params[col].max()), 4),
            "std": round(float(params[col].std(ddof=0)), 4),
        }
        for col in arma_cols
    }
    return result


# ---------------------------------------------------------------------------
# Script independente
# ---------------------------------------------------------------------------


def load_series_from_csv(
    path: Path,
    date_col: str,
    value_col: str,
    era5_12h: bool = False,
    filter_col: str | None = None,
    filter_value: str | None = None,
) -> tuple[pd.Series, DataQualityReport]:
    frame = pd.read_csv(path)
    if filter_col:
        frame = frame[frame[filter_col].astype(str) == str(filter_value)]
        if frame.empty:
            raise ValueError(f"Nenhuma linha com {filter_col} = {filter_value!r}")
    incomplete = 0
    if era5_12h:
        frame, incomplete = aggregate_era5_12h_to_daily(frame, date_col, value_col)
        date_col, value_col = "date", "precipitation_mm"
    return prepare_daily_series(frame, date_col, value_col, incomplete_aggregation=incomplete)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detecção de anomalias de precipitação (ARIMA + Z-Score)")
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--value-col", default="precipitation_mm")
    parser.add_argument("--era5-12h", action="store_true", help="entrada com acumulados ERA5 de 12 h")
    parser.add_argument("--filter-col")
    parser.add_argument("--filter-value")
    parser.add_argument("--threshold", type=float, default=3.0)
    parser.add_argument("--seasonal", choices=["auto", "fourier", "none"], default="auto")
    parser.add_argument("--initial-train-years", type=int, default=2)
    parser.add_argument("--out-csv", type=Path)
    parser.add_argument("--out-json", type=Path)
    args = parser.parse_args(argv)

    series, quality = load_series_from_csv(
        args.csv, args.date_col, args.value_col, args.era5_12h, args.filter_col, args.filter_value
    )
    config = DetectionConfig(
        z_threshold=args.threshold,
        seasonal=args.seasonal,
        initial_train_years=args.initial_train_years,
    )
    result = detect_anomalies(series, config, quality)
    positives = result.positive_anomalies
    print(
        f"run {result.run_id}: modelo {result.selected_spec['order']} "
        f"sazonal={result.selected_spec['seasonal']}, período pontuado "
        f"{result.scored_period[0]}..{result.scored_period[1]}, "
        f"{len(positives)} anomalias positivas, "
        f"{len(result.anomalies) - len(positives)} negativas"
    )
    for anomaly in positives:
        print(
            f"  {anomaly.date}  obs={anomaly.observed_mm:7.1f} mm  "
            f"prev={anomaly.predicted_mm:6.1f} mm  z={anomaly.z_score:5.2f}  {anomaly.episode_id}"
        )
    if args.out_csv:
        result.anomalies_frame().to_csv(args.out_csv, index=False)
    if args.out_json:
        args.out_json.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
