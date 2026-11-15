"""Anomalias de temperatura e umidade: climatologia de Fourier + AR(p) + Z.

Mesmo princípio do detector de chuva (Z sobre o resíduo de previsão de um
passo, fora da amostra), com um modelo leve o bastante para os 5.570
municípios × 2 variáveis:

1. Valor diário = média das observações de 00 e 12 UTC do ERA5-Land (só dias
   com as duas). Não é a média de 24 h: é um índice diário consistente.
2. Climatologia da média: regressão de Fourier anual (K = 3) ajustada nos anos
   anteriores ao ano pontuado.
3. Heterocedasticidade sazonal: a variância do desvio também tem ciclo anual
   (frentes frias tornam o inverno do Sul mais variável). Ajustamos o desvio ao
   quadrado com Fourier (K = 2) e padronizamos o desvio por esse desvio-padrão
   sazonal. Sem isso, o Z ficaria inflado na estação mais variável e o mapa
   sazonal mostraria a variância, não a anomalia.
4. AR(p) por mínimos quadrados na anomalia padronizada; p ∈ {1, 2, 3} por BIC
   no período inicial (2 anos); coeficientes reestimados a cada ano com dados
   anteriores (janela expansiva), como no detector de chuva.
5. ``e_t = a_t − â_{t|t−1}``; ``Z_t = (e_t − μ_e)/σ_e`` com μ_e, σ_e do treino.
   |Z| > 3 → anomalia (positiva: mais quente/úmido; negativa: mais frio/seco).
6. Para a classificação climatológica, o percentil do valor observado entre
   todos os dias da mesma época (±15 dias) dos anos anteriores.

Função pura (sem banco): recebe uma série diária e devolve anomalias,
exposição (dias pontuados por ano/mês) e diagnósticos.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

VARIABLES = {"temperatura": "°C", "umidade": "%"}


@dataclass
class ThermalConfig:
    z_threshold: float = 3.0
    mean_harmonics: int = 3
    variance_harmonics: int = 2
    max_p: int = 3
    initial_train_years: int = 2
    window_days: int = 15
    min_train_days: int = 365

    def __post_init__(self):
        if self.z_threshold <= 0:
            raise ValueError("z_threshold deve ser positivo")
        if self.max_p < 1:
            raise ValueError("max_p deve ser >= 1")
        if self.initial_train_years < 1:
            raise ValueError("initial_train_years deve ser >= 1")


@dataclass
class ThermalResult:
    anomalies: pd.DataFrame  # date, value, expected, z, direction, climate_percentile
    exposure: pd.DataFrame  # year, month, scored_days
    diagnostics: dict = field(default_factory=dict)


def _fourier(doy: np.ndarray, harmonics: int) -> np.ndarray:
    angle = 2 * np.pi * (doy - 1) / 365.25
    columns = [np.ones_like(angle)]
    for k in range(1, harmonics + 1):
        columns += [np.sin(k * angle), np.cos(k * angle)]
    return np.column_stack(columns)


def _lstsq(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(x, y, rcond=None)[0]


def _lag_matrix(a: np.ndarray, p: int) -> np.ndarray:
    """Colunas [1, a_{t−1}, …, a_{t−p}] alinhadas com a_t (NaN nas bordas)."""
    n = len(a)
    columns = [np.ones(n)]
    for lag in range(1, p + 1):
        shifted = np.full(n, np.nan)
        shifted[lag:] = a[:-lag]
        columns.append(shifted)
    return np.column_stack(columns)


def _fit_ar(a: np.ndarray, p: int) -> tuple[np.ndarray, np.ndarray, int]:
    x = _lag_matrix(a, p)
    ok = np.isfinite(a) & np.isfinite(x).all(axis=1)
    if ok.sum() < 10 * (p + 1):
        raise ValueError("dados insuficientes para o AR")
    beta = _lstsq(x[ok], a[ok])
    residual = np.full(len(a), np.nan)
    residual[ok] = a[ok] - x[ok] @ beta
    return beta, residual, int(ok.sum())


def _climate_model(values: np.ndarray, doy: np.ndarray, train: np.ndarray, config: ThermalConfig):
    """Média e desvio-padrão sazonais ajustados apenas em ``train``."""
    fm = _fourier(doy, config.mean_harmonics)
    ok = train & np.isfinite(values)
    mean_beta = _lstsq(fm[ok], values[ok])
    deviation = values - fm @ mean_beta
    fv = _fourier(doy, config.variance_harmonics)
    var_beta = _lstsq(fv[ok], deviation[ok] ** 2)
    variance = fv @ var_beta
    floor = max(float(np.nanvar(deviation[ok])) * 0.05, 1e-6)
    sd = np.sqrt(np.maximum(variance, floor))
    return fm @ mean_beta, sd


def _window_percentile(values: np.ndarray, doy: np.ndarray, years: np.ndarray, i: int, window: int) -> float:
    """Percentil (0–100, 'weak') de values[i] entre os dias da mesma época de anos anteriores."""
    difference = np.abs(doy - doy[i])
    distance = np.minimum(difference, 366 - difference)
    reference = values[(years < years[i]) & (distance <= window) & np.isfinite(values)]
    if len(reference) < 30:
        return float("nan")
    return float(100.0 * np.mean(reference <= values[i]))


def detect_thermal_anomalies(series: pd.Series, config: ThermalConfig | None = None) -> ThermalResult:
    """Detecta anomalias em uma série diária de temperatura ou umidade."""
    config = config or ThermalConfig()
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("A série precisa de índice DatetimeIndex diário.")
    series = series.sort_index()
    if series.index.has_duplicates:
        raise ValueError("A série tem datas duplicadas.")
    series = series.asfreq("D").astype(float)
    values = series.to_numpy(dtype=float, copy=True)
    values[~np.isfinite(values)] = np.nan
    index = series.index
    doy = index.dayofyear.to_numpy().astype(float)
    years = index.year.to_numpy()

    first_test_year = index[0].year + config.initial_train_years + (1 if index[0].dayofyear > 1 else 0)
    last_year = index[-1].year
    if first_test_year > last_year:
        raise ValueError("Série curta demais para o treino inicial.")
    initial = years < first_test_year
    if np.isfinite(values[initial]).sum() < config.min_train_days:
        raise ValueError("Dados válidos insuficientes no treino inicial.")

    # ---- ordem p por BIC no treino inicial ------------------------------
    clim_mean, clim_sd = _climate_model(values, doy, initial, config)
    a0 = np.where(initial, (values - clim_mean) / clim_sd, np.nan)
    bic = {}
    for p in range(1, config.max_p + 1):
        _, residual, n = _fit_ar(a0, p)
        rss = float(np.nansum(residual**2))
        bic[p] = n * np.log(rss / n) + (p + 1) * np.log(n)
    p = min(bic, key=bic.get)

    # ---- pontuação ano a ano (janela expansiva) ------------------------
    z = np.full(len(values), np.nan)
    expected = np.full(len(values), np.nan)
    for year in range(first_test_year, last_year + 1):
        train = years < year
        block = years == year
        clim_mean, clim_sd = _climate_model(values, doy, train, config)
        a = (values - clim_mean) / clim_sd
        a_train = np.where(train, a, np.nan)
        beta, residual, _ = _fit_ar(a_train, p)
        mu, sigma = float(np.nanmean(residual)), float(np.nanstd(residual, ddof=1))
        x = _lag_matrix(a, p)  # lags usam observações reais até t−1
        prediction = x @ beta
        z[block] = ((a - prediction - mu) / sigma)[block]
        expected[block] = (clim_mean + clim_sd * prediction)[block]

    scored = np.isfinite(z)
    flagged = np.flatnonzero(scored & (np.abs(z) > config.z_threshold))
    anomalies = pd.DataFrame(
        {
            "date": index[flagged].date,
            "value": values[flagged],
            "expected": expected[flagged],
            "z": z[flagged],
            "direction": np.where(z[flagged] > 0, "positive", "negative"),
            "climate_percentile": [
                _window_percentile(values, doy, years, i, config.window_days) for i in flagged
            ],
        }
    )
    exposure = (
        pd.DataFrame({"year": years[scored], "month": index.month.to_numpy()[scored]})
        .value_counts()
        .rename("scored_days")
        .reset_index()
        .sort_values(["year", "month"], ignore_index=True)
    )
    zs = z[scored]
    diagnostics = {
        "ar_order": int(p),
        "n_scored": int(scored.sum()),
        "z_mean": round(float(np.mean(zs)), 4) if zs.size else None,
        "z_std": round(float(np.std(zs, ddof=1)), 4) if zs.size > 1 else None,
        "rate_positive": round(float(np.mean(zs > config.z_threshold)), 6) if zs.size else None,
        "rate_negative": round(float(np.mean(zs < -config.z_threshold)), 6) if zs.size else None,
    }
    return ThermalResult(anomalies, exposure, diagnostics)
