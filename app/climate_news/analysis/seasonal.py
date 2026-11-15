"""Distribuição sazonal das anomalias por município, região e fase do ENSO.

Decisões metodológicas (ver docs/avaliacao_professor/RELATORIO_FINAL.md):

- **Desagrupamento (declustering).** Dias anômalos separados por até
  ``gap_days`` dias sem anomalia (padrão: 1), do mesmo município e da mesma
  variável, formam *um* evento; acumulados ocupam a janela inteira,
  datado pelo dia de maior |Z|. Uma tempestade de 5 dias conta uma vez; sem
  isso, a contagem e o teste qui-quadrado (que supõe independência) seriam
  inflados por eventos longos.
- **Exposição.** Cada estação tem número diferente de dias válidos (DJF tem
  90–91 dias, MAM/JJA 92; dados ausentes reduzem ainda mais). A frequência
  comparável é a **taxa** = eventos / dias válidos × 1000. A *participação
  normalizada* de uma estação é a sua taxa dividida pela soma das 4 taxas.
- **Teste.** Qui-quadrado de aderência contra as contagens esperadas sob
  "mesma taxa em todas as estações" (proporcional à exposição). Com milhares
  de municípios, os p-valores são corrigidos por Benjamini–Hochberg (FDR).
  Municípios com menos de ``min_events`` eventos ficam "insuficientes".
- **Concentração.** 1 − H/ln 4, com H a entropia das participações
  normalizadas: 0 = uniforme entre as estações, 1 = tudo em uma estação.
- **Estrutura espacial.** I de Moran global (vizinhos mais próximos pelos
  centróides, teste por permutação) da participação outono+inverno.

Funções puras sobre DataFrames; não acessam o banco.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial import cKDTree

from app.climate_news.analysis.seasons import SEASONS, season_array, season_year

MIN_EVENTS = 20
ALPHA = 0.05


# ---------------------------------------------------------------------------
# Preparação
# ---------------------------------------------------------------------------


def add_calendar(frame: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    out = frame.copy()
    dates = pd.to_datetime(out[date_col])
    out["year"] = dates.dt.year.astype(int)
    out["month"] = dates.dt.month.astype(int)
    out["season"] = season_array(out["month"].to_numpy())
    out["season_year"] = [season_year(y, m) for y, m in zip(out["year"], out["month"])]
    return out


def decluster(
    frame: pd.DataFrame,
    keys: list[str],
    date_col: str = "date",
    score_col: str = "abs_z",
    gap_days: int = 1,
    start_col: str | None = None,
) -> pd.DataFrame:
    """Um evento por sequência de dias anômalos (até ``gap_days`` dias sem anomalia entre eles).

    Com ``start_col``, cada linha cobre o intervalo [início, data] (p.ex. a
    janela de um acumulado de 3 ou 5 dias); intervalos que se tocam ou ficam a
    até ``gap_days`` dias formam o mesmo evento. Assim um dia ARIMA dentro da
    janela de um acumulado da mesma tempestade não conta duas vezes.

    Mantém a linha de maior ``score_col`` de cada sequência e acrescenta
    ``event_days`` (linhas agrupadas) e ``event_start``/``event_end``.
    """
    if gap_days < 0:
        raise ValueError("gap_days deve ser >= 0")
    if frame.empty:
        return frame.assign(event_days=pd.Series(dtype=int))
    out = frame.copy()
    out[date_col] = pd.to_datetime(out[date_col])
    start = pd.to_datetime(out[start_col]) if start_col else out[date_col]
    out["_start"] = start.where(start <= out[date_col], out[date_col])
    out = out.sort_values(keys + ["_start", date_col], kind="mergesort")
    # fim acumulado do grupo até a linha anterior (intervalos podem se sobrepor)
    previous_end = out.groupby(keys, sort=False)[date_col].transform(lambda d: d.cummax().shift(1))
    gap = (out["_start"] - previous_end).dt.days
    new_group = gap.isna() | (gap > gap_days + 1)
    out["_event"] = new_group.cumsum()
    grouped = out.groupby("_event", sort=False)
    best = out.loc[grouped[score_col].idxmax()].copy()
    best["event_days"] = grouped.size().to_numpy()
    best["event_start"] = grouped["_start"].min().to_numpy()
    best["event_end"] = grouped[date_col].max().to_numpy()
    return best.drop(columns=["_event", "_start"]).reset_index(drop=True)


def seasonal_exposure(exposure: pd.DataFrame, keys: list[str], days_col: str = "days") -> pd.DataFrame:
    """Dias válidos por chave e estação (exposição já filtrada por período/fase)."""
    frame = exposure.copy()
    frame["season"] = season_array(frame["month"].to_numpy())
    return frame.groupby(keys + ["season"], as_index=False)[days_col].sum().rename(columns={days_col: "days"})


# ---------------------------------------------------------------------------
# Tabela sazonal e concentração
# ---------------------------------------------------------------------------


def seasonal_table(events: pd.DataFrame, exposure_by_season: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Contagem, exposição, taxa e participações por chave × estação (sempre 4 linhas por chave)."""
    counts = events.groupby(keys + ["season"]).size().rename("n").reset_index()
    groups = exposure_by_season[keys].drop_duplicates()
    grid = groups.merge(pd.DataFrame({"season": list(SEASONS)}), how="cross")
    table = grid.merge(exposure_by_season, on=keys + ["season"], how="left").merge(
        counts, on=keys + ["season"], how="left"
    )
    table["n"] = table["n"].fillna(0).astype(int)
    table["days"] = table["days"].fillna(0).astype(int)
    table["rate_per_1000"] = np.where(table["days"] > 0, 1000 * table["n"] / table["days"].clip(lower=1), np.nan)
    by = table.groupby(keys, sort=False)
    total_n = by["n"].transform("sum")
    total_rate = by["rate_per_1000"].transform("sum")
    table["share_abs"] = np.where(total_n > 0, table["n"] / total_n.clip(lower=1), np.nan)
    table["share_norm"] = np.where(total_rate > 0, table["rate_per_1000"] / total_rate, np.nan)
    table["season"] = pd.Categorical(table["season"], categories=list(SEASONS), ordered=True)
    return table.sort_values(keys + ["season"], ignore_index=True)


def benjamini_hochberg(pvalues: np.ndarray) -> np.ndarray:
    """q-valores de Benjamini–Hochberg (NaN preservado)."""
    p = np.asarray(pvalues, dtype=float)
    q = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    if not ok.any():
        return q
    values = p[ok]
    order = np.argsort(values)
    ranked = values[order] * len(values) / np.arange(1, len(values) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(values)
    out[order] = np.minimum(ranked, 1.0)
    q[ok] = out
    return q


def concentration(table: pd.DataFrame, keys: list[str], min_events: int = MIN_EVENTS, alpha: float = ALPHA) -> pd.DataFrame:
    """Uma linha por chave: estação dominante, concentração, teste e padrão."""
    rows = []
    for key, group in table.groupby(keys, sort=False, observed=True):
        group = group.set_index("season").reindex(list(SEASONS))
        n = group["n"].to_numpy(dtype=float)
        days = group["days"].to_numpy(dtype=float)
        shares = group["share_norm"].to_numpy(dtype=float)
        total = int(n.sum())
        row = dict(zip(keys, key if isinstance(key, tuple) else (key,)))
        row.update({"n_events": total, "days": int(days.sum())})
        for season, share, abs_share, rate in zip(
            SEASONS, shares, group["share_abs"].to_numpy(), group["rate_per_1000"].to_numpy()
        ):
            row[f"share_norm_{season}"] = share
            row[f"share_abs_{season}"] = abs_share
            row[f"rate_{season}"] = rate
        if total == 0 or not np.all(days > 0):
            row.update({"dominant_season": None, "concentration": np.nan, "chi2_pvalue": np.nan})
        else:
            p = shares[shares > 0]
            entropy = float(-(p * np.log(p)).sum())
            row["concentration"] = 1 - entropy / np.log(len(SEASONS))
            row["dominant_season"] = SEASONS[int(np.nanargmax(shares))]
            expected = total * days / days.sum()
            row["chi2_pvalue"] = float(stats.chisquare(n, expected).pvalue) if total >= min_events else np.nan
        row["autumn_winter_share"] = (
            np.nan if total == 0 else float(np.nansum([row["share_norm_outono"], row["share_norm_inverno"]]))
        )
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["chi2_qvalue"] = benjamini_hochberg(out["chi2_pvalue"].to_numpy())
    out["pattern"] = np.select(
        [
            out["n_events"] < min_events,
            out["chi2_qvalue"] < alpha,
        ],
        ["insuficiente", "predominio_" + out["dominant_season"].fillna("")],
        default="sem_predominio",
    )
    return out


# ---------------------------------------------------------------------------
# Agregações regionais, rankings e ENSO
# ---------------------------------------------------------------------------


def pooled_shares(table: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Taxa agregada (Σn/Σdias) por chave × estação, p.ex. por região ou Brasil."""
    pooled = table.groupby(keys + ["season"], observed=True, as_index=False)[["n", "days"]].sum()
    pooled["rate_per_1000"] = 1000 * pooled["n"] / pooled["days"].clip(lower=1)
    total = pooled.groupby(keys, observed=True)["rate_per_1000"].transform("sum") if keys else pooled["rate_per_1000"].sum()
    pooled["share_norm"] = pooled["rate_per_1000"] / total
    return pooled


def dominant_distribution(conc: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Quantos municípios em cada padrão (predomínio de cada estação, sem predomínio, insuficiente)."""
    counts = conc.groupby(keys + ["pattern"], observed=True).size().rename("municipalities").reset_index()
    counts["share"] = counts["municipalities"] / counts.groupby(keys, observed=True)["municipalities"].transform("sum")
    return counts


def ranking(conc: pd.DataFrame, season: str, limit: int = 20, ascending: bool = False, min_events: int = MIN_EVENTS) -> pd.DataFrame:
    if season not in SEASONS:
        raise ValueError(f"estação inválida: {season!r}")
    eligible = conc[conc["n_events"] >= min_events]
    return eligible.sort_values(f"share_norm_{season}", ascending=ascending).head(limit).reset_index(drop=True)


def rate_ratio_ci(n1: int, d1: float, n0: int, d0: float, level: float = 0.95) -> tuple[float, float, float]:
    """Razão de taxas de Poisson (n1/d1)/(n0/d0) com IC exato condicional (binomial).

    Condicionando em n1+n0, n1 ~ Bin(n1+n0, π) com π = d1·RR/(d1·RR + d0).
    """
    if d1 <= 0 or d0 <= 0 or n1 + n0 == 0:
        return (np.nan, np.nan, np.nan)
    ratio = (n1 / d1) / (n0 / d0) if n0 > 0 else np.inf
    total = n1 + n0
    a = (1 - level) / 2
    low_pi = stats.beta.ppf(a, n1, total - n1 + 1) if n1 > 0 else 0.0
    high_pi = stats.beta.ppf(1 - a, n1 + 1, total - n1) if n1 < total else 1.0
    to_rr = lambda pi: (pi / (1 - pi)) * (d0 / d1) if pi < 1 else np.inf  # noqa: E731
    return (float(ratio), float(to_rr(low_pi)), float(to_rr(high_pi)))


def enso_seasonal_rates(events: pd.DataFrame, exposure: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Taxas por chave × estação × fase ENSO e razão (fase / neutro) com IC 95%.

    ``events`` e ``exposure`` precisam da coluna ``enso_phase``; a exposição
    traz os dias válidos de cada mês com a fase daquele mês.
    """
    exp = exposure.copy()
    exp["season"] = season_array(exp["month"].to_numpy())
    days = exp.groupby(keys + ["season", "enso_phase"], as_index=False)["days"].sum()
    counts = events.groupby(keys + ["season", "enso_phase"]).size().rename("n").reset_index()
    table = days.merge(counts, on=keys + ["season", "enso_phase"], how="left")
    table["n"] = table["n"].fillna(0).astype(int)
    table["rate_per_1000"] = 1000 * table["n"] / table["days"].clip(lower=1)
    neutral = table[table["enso_phase"] == "neutro"][keys + ["season", "n", "days"]].rename(
        columns={"n": "n_neutro", "days": "days_neutro"}
    )
    table = table.merge(neutral, on=keys + ["season"], how="left")
    cis = [
        rate_ratio_ci(int(r.n), float(r.days), int(r.n_neutro or 0), float(r.days_neutro or 0))
        if r.enso_phase != "neutro"
        else (1.0, np.nan, np.nan)
        for r in table.itertuples()
    ]
    table["ratio_vs_neutral"] = [c[0] for c in cis]
    table["ratio_ci_low"] = [c[1] for c in cis]
    table["ratio_ci_high"] = [c[2] for c in cis]
    return table


# ---------------------------------------------------------------------------
# Estrutura espacial
# ---------------------------------------------------------------------------


def knn_weights(lat: np.ndarray, lon: np.ndarray, k: int = 8) -> np.ndarray:
    """Índices dos k vizinhos mais próximos (coordenadas projetadas em km, aproximação equiretangular)."""
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    x = np.radians(lon) * np.cos(np.radians(lat.mean())) * 6371.0
    y = np.radians(lat) * 6371.0
    tree = cKDTree(np.column_stack([x, y]))
    _, idx = tree.query(np.column_stack([x, y]), k=min(k + 1, len(lat)))
    return idx[:, 1:]


def morans_i(values: np.ndarray, neighbors: np.ndarray, permutations: int = 499, seed: int = 0) -> dict:
    """I de Moran global com pesos k-vizinhos (linha-normalizados) e p por permutação."""
    z = np.asarray(values, dtype=float)
    if np.isnan(z).any():
        raise ValueError("valores com NaN: filtre antes de calcular o I de Moran")
    n = len(z)
    if n < 10:
        return {"I": np.nan, "expected": np.nan, "p_value": np.nan, "n": n}
    z = z - z.mean()
    denominator = (z**2).sum()

    def statistic(v: np.ndarray) -> float:
        lag = v[neighbors].mean(axis=1)
        return float((v * lag).sum() / denominator)

    observed = statistic(z)
    rng = np.random.default_rng(seed)
    simulated = np.array([statistic(rng.permutation(z)) for _ in range(permutations)])
    p = (1 + np.sum(simulated >= observed)) / (permutations + 1)
    return {"I": round(observed, 4), "expected": round(-1 / (n - 1), 5), "p_value": float(p), "n": int(n),
            "permutations": permutations}


def atypical_municipalities(conc: pd.DataFrame, neighbors: np.ndarray, min_agreeing: int = 5) -> pd.Series:
    """Município com predomínio significativo de uma estação diferente da de seus vizinhos.

    ``neighbors`` é alinhado com ``conc`` (mesma ordem). Atípico quando pelo menos
    ``min_agreeing`` dos k vizinhos têm predomínio significativo de uma mesma
    estação e ela difere da do município.
    """
    patterns = conc["pattern"].to_numpy()
    flags = np.zeros(len(conc), dtype=bool)
    for i, own in enumerate(patterns):
        if not str(own).startswith("predominio_"):
            continue
        neighbor_patterns = pd.Series(patterns[neighbors[i]])
        neighbor_patterns = neighbor_patterns[neighbor_patterns.str.startswith("predominio_")]
        if neighbor_patterns.empty:
            continue
        mode = neighbor_patterns.value_counts()
        if mode.iloc[0] >= min_agreeing and mode.index[0] != own:
            flags[i] = True
    return pd.Series(flags, index=conc.index)
