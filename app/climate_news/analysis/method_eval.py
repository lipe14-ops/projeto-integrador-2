"""Avaliação do método ARIMA + Z para a chuva diária (Tarefas A e E).

Reexecuta o detector de produção (``detect_anomalies``, sem nenhuma alteração)
numa amostra estratificada de municípios e mede, sobre os resíduos de
previsão de um passo **fora da amostra**:

1. **Taxa empírica de alertas × taxa nominal.** Sob normalidade, P(Z > 3) =
   0,135%. A taxa observada mostra quanto a cauda real é mais pesada.
2. **Heterocedasticidade sazonal.** O detector usa um σ único por ano de
   treino. Se a variância do resíduo muda com a estação, o Z > 3 se concentra
   na estação mais variável. Medimos o desvio-padrão de Z por estação, o teste
   de Brown–Forsythe (Levene com mediana) e a distribuição sazonal dos
   alertas com σ único × com σ por estação (estimado só com anos anteriores).
3. **Sensibilidade ao limiar.** Número de alertas para k = 2,5; 3; 3,5; 4.
4. **Comparação com um método climatológico.** Dias ≥ P95/P99 dos dias
   chuvosos (≥ 1 mm) dos anos anteriores (limiares do tipo usado nos índices
   R95p/R99p do ETCCDI; aqui por dia, não como total anual).
   Medimos a sobreposição com os alertas Z > 3 (Jaccard, % dos alertas que
   são extremos e % dos extremos que viram alerta).
5. **Simulação nula (dados sintéticos).** Séries geradas por um processo
   estacionário sazonal (ocorrência Bernoulli + intensidade gama), sem evento
   algum inserido: todo alerta é, por construção, "falso" do ponto de vista de
   evento. Mede a taxa de alarmes que o método produz só pela forma da
   distribuição da chuva.

Funções puras + um executor paralelo que lê o banco. Nada é gravado no banco.
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from scipy import stats

from app.climate_news.analysis.seasons import SEASONS, season_array

log = logging.getLogger("climate_news.analysis")

THRESHOLDS = (2.5, 3.0, 3.5, 4.0)
WET_DAY_MM = 1.0
GAUSSIAN_TAIL = {k: float(stats.norm.sf(k)) for k in THRESHOLDS}


# ---------------------------------------------------------------------------
# Métricas sobre a saída diária do detector
# ---------------------------------------------------------------------------


def seasonal_sigma_z(daily: pd.DataFrame, min_days: int = 60) -> pd.Series:
    """Z repadronizado pela média e pelo DP de Z da mesma estação nos anos anteriores.

    Para o ano Y: (Z − μ_estação)/σ_estação, com μ e σ dos Z fora da amostra
    de anos < Y na mesma estação (só passado, sem vazamento). O primeiro ano
    pontuado fica NaN. Atenção: na estação seca, Z é uma mistura de muitos
    dias secos com poucos chuvosos; σ_estação pequeno torna "surpreendente"
    qualquer chuva moderada. É uma definição alternativa, não uma correção.
    """
    z = daily["z_score"]
    years = daily.index.year
    seasons = season_array(daily.index.month.to_numpy())
    out = pd.Series(np.nan, index=daily.index)
    for year in np.unique(years):
        past = years < year
        if not past.any():
            continue
        for season in SEASONS:
            ref = z[past & (seasons == season)].dropna()
            mask = (years == year) & (seasons == season)
            if len(ref) >= min_days:
                out[mask] = (z[mask] - ref.mean()) / ref.std(ddof=1)
    return out


def climatological_flags(observed: pd.Series, percentile: float) -> pd.Series:
    """Dia ≥ percentil dos dias chuvosos (≥ 1 mm) dos anos anteriores (expansivo)."""
    years = observed.index.year
    flags = pd.Series(False, index=observed.index)
    for year in np.unique(years):
        past = observed[(years < year) & (observed >= WET_DAY_MM)].dropna()
        if len(past) < 50:
            continue
        threshold = float(np.percentile(past, percentile))
        mask = years == year
        flags[mask] = (observed[mask] >= max(threshold, WET_DAY_MM)).fillna(False).to_numpy()
    return flags


def evaluate_daily(daily: pd.DataFrame, observed: pd.Series) -> dict:
    """Métricas de um município a partir de ``DetectionResult.daily``."""
    daily = daily.copy()
    # mesma regra do snapshot: só dias com o dia anterior válido (senão a previsão é de dois passos)
    previous_ok = observed.shift(1).reindex(daily.index).notna()
    daily = daily[daily["z_score"].notna() & previous_ok]
    z = daily["z_score"]
    seasons = season_array(daily.index.month.to_numpy())
    obs = observed.reindex(daily.index)
    out: dict = {"n_scored": int(len(z))}

    for k in THRESHOLDS:
        out[f"rate_pos_{k}"] = float((z > k).mean())
    out["z_std"] = float(z.std(ddof=1))
    out["z_skew"] = float(stats.skew(z))

    groups = [z[seasons == s].to_numpy() for s in SEASONS]
    for season, values in zip(SEASONS, groups):
        out[f"z_std_{season}"] = float(np.std(values, ddof=1)) if len(values) > 1 else np.nan
        out[f"days_{season}"] = int(len(values))
        out[f"alerts_{season}"] = int((values > 3).sum())
    if all(len(g) > 10 for g in groups):
        out["brown_forsythe_p"] = float(stats.levene(*groups, center="median").pvalue)
    else:
        out["brown_forsythe_p"] = np.nan

    zs = seasonal_sigma_z(daily)
    ok = zs.notna()
    for season in SEASONS:
        mask = ok.to_numpy() & (seasons == season)
        out[f"alerts_global_{season}"] = int((z[mask] > 3).sum())
        out[f"alerts_seasonal_{season}"] = int((zs[mask] > 3).sum())
        out[f"days_cmp_{season}"] = int(mask.sum())

    arima = z > 3
    for pct in (95, 99):
        clim = climatological_flags(observed, pct).reindex(daily.index).fillna(False)
        both = int((arima & clim).sum())
        either = int((arima | clim).sum())
        out[f"p{pct}_days"] = int(clim.sum())
        for season in SEASONS:  # referência independente do modelo para a distribuição sazonal
            out[f"p{pct}_{season}"] = int(clim[seasons == season].sum())
        out[f"p{pct}_and_arima"] = both
        out[f"jaccard_p{pct}"] = both / either if either else np.nan
    out["arima_alerts"] = int(arima.sum())
    out["arima_alerts_dry_before"] = int((arima & (obs < 20)).sum())  # alertas com < 20 mm
    return out


# ---------------------------------------------------------------------------
# Simulação nula
# ---------------------------------------------------------------------------


def synthetic_null_rain(years: int = 11, seed: int = 0, wet_base: float = 0.4, wet_amp: float = 0.2,
                        mean_mm: float = 9.0, mean_amp: float = 0.5, shape: float = 0.7) -> pd.Series:
    """DADOS SINTÉTICOS — chuva diária estacionária, sem eventos inseridos.

    Ocorrência ~ Bernoulli(p sazonal); intensidade ~ Gama(shape, escala sazonal).
    """
    rng = np.random.default_rng(seed)
    index = pd.date_range("2015-01-01", periods=int(365.25 * years), freq="D")
    phase = 2 * np.pi * (index.dayofyear.to_numpy() - 15) / 365.25
    p_wet = np.clip(wet_base + wet_amp * np.cos(phase), 0.02, 0.95)
    scale = mean_mm * (1 + mean_amp * np.cos(phase)) / shape
    wet = rng.random(len(index)) < p_wet
    amount = rng.gamma(shape, np.maximum(scale, 0.1))
    return pd.Series(np.where(wet, amount, 0.0).round(2), index=index, name="precipitation_mm")


def null_simulation(n_series: int = 20, seed: int = 0) -> pd.DataFrame:
    from app.climate_news.detection.arima_zscore import detect_anomalies

    rows = []
    for i in range(n_series):
        series = synthetic_null_rain(seed=seed + i, shape=[0.5, 0.7, 1.0][i % 3])
        result = detect_anomalies(series)
        z = result.daily["z_score"].dropna()
        rows.append({"serie": i, "shape": [0.5, 0.7, 1.0][i % 3], "n_scored": len(z),
                     **{f"rate_pos_{k}": float((z > k).mean()) for k in THRESHOLDS},
                     "z_skew": float(stats.skew(z))})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Execução sobre o banco
# ---------------------------------------------------------------------------


def sample_municipalities(municipalities: pd.DataFrame, per_region: int, seed: int = 42,
                          always: tuple[int, ...] = (4314902,)) -> list[int]:
    """Amostra aleatória estratificada por região (semente fixa) + municípios obrigatórios."""
    frame = municipalities.dropna(subset=["regiao"])
    picked = (
        frame.groupby("regiao", group_keys=False)
        .apply(lambda g: g.sample(min(per_region, len(g)), random_state=seed))["codigo_ibge"]
        .astype(int)
        .tolist()
    )
    return sorted(set(picked) | set(always))


def _evaluate_one(database_url: str, codigo: int) -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.climate_news.data_source import load_daily_series
    from app.climate_news.detection.arima_zscore import detect_anomalies

    engine = create_engine(database_url)
    try:
        with Session(engine) as db:
            series, quality = load_daily_series(db, codigo)
        result = detect_anomalies(series, quality=quality)
        metrics = evaluate_daily(result.daily, series)
        metrics.update({"codigo_ibge": codigo, "order": str(result.selected_spec["order"]),
                        "seasonal_terms": result.selected_spec["seasonal"]})
        return metrics
    except Exception as error:  # noqa: BLE001
        return {"codigo_ibge": codigo, "error": str(error)}
    finally:
        engine.dispose()


def run_method_evaluation(engine, codes: list[int], workers: int = 4) -> pd.DataFrame:
    url = engine.url.render_as_string(hide_password=False)
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_evaluate_one, url, c) for c in codes]
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if i % 10 == 0:
                log.info("avaliação do método: %d/%d municípios", i, len(codes))
    return pd.DataFrame(rows)
