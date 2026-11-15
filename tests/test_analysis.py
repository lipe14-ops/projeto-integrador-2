"""Testes da análise espacial/sazonal (``app/climate_news/analysis``).

Todos os dados aqui são SINTÉTICOS, gerados nos próprios testes, para checar
propriedades conhecidas por construção (taxas iguais, picos inseridos etc.).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.climate_news.analysis.classification import classify_precipitation, classify_thermal
from app.climate_news.analysis.method_eval import climatological_flags, evaluate_daily, seasonal_sigma_z
from app.climate_news.analysis.seasonal import (
    add_calendar,
    atypical_municipalities,
    benjamini_hochberg,
    concentration,
    decluster,
    knn_weights,
    morans_i,
    rate_ratio_ci,
    seasonal_exposure,
    seasonal_table,
)
from app.climate_news.analysis.seasons import enso_episodes, season_array, season_of_month, season_year
from app.climate_news.analysis.thermal import ThermalConfig, detect_thermal_anomalies

# ---------------------------------------------------------------------------
# Estações e ENSO
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "month,season",
    [(12, "verao"), (1, "verao"), (2, "verao"), (3, "outono"), (5, "outono"), (6, "inverno"), (8, "inverno"),
     (9, "primavera"), (11, "primavera")],
)
def test_southern_hemisphere_seasons(month, season):
    assert season_of_month(month) == season
    assert season_array([month])[0] == season


@pytest.mark.parametrize("bad", [0, 13, None, "x"])
def test_invalid_month_raises(bad):
    with pytest.raises(ValueError):
        season_of_month(bad)


def test_season_array_rejects_out_of_range():
    with pytest.raises(ValueError):
        season_array([1, 13])


def test_december_belongs_to_next_summer():
    assert season_year(2023, 12) == 2024
    assert season_year(2024, 1) == 2024


def _oni(values, start=(2020, 1)):
    months = pd.period_range(pd.Period(year=start[0], month=start[1], freq="M"), periods=len(values), freq="M")
    return {(p.year, p.month): v for p, v in zip(months, values)}


def test_enso_episode_requires_five_consecutive_seasons():
    phases = enso_episodes(_oni([0.6, 0.7, 0.8, 0.9, 1.0, 0.2, 0.6, 0.6, 0.6, 0.6, 0.0]))
    assert [phases[(2020, m)] for m in range(1, 6)] == ["el_nino"] * 5
    assert [phases[(2020, m)] for m in range(7, 11)] == ["neutro"] * 4  # só 4 meses: não é episódio


def test_enso_la_nina_and_missing_breaks_run():
    phases = enso_episodes(_oni([-0.6, -0.7, None, -0.8, -0.9, -1.0, -0.6, -0.5]))
    assert phases[(2020, 1)] == "neutro"  # sequência interrompida pelo mês sem ONI
    assert all(phases[(2020, m)] == "la_nina" for m in range(4, 9))
    assert enso_episodes({}) == {}


# ---------------------------------------------------------------------------
# Classificação operacional
# ---------------------------------------------------------------------------


def test_artifact_is_excluded_before_anything_else():
    c = classify_precipitation("arima_zscore", "positive", "possible_artifact", "exceptional_for_location", None, 3)
    assert c.event_class == "artefato_provavel" and not c.counted and not c.is_extreme
    assert c.documented_impact  # o eixo de impacto é independente da classe


def test_negative_anomaly_is_not_a_rain_event():
    c = classify_precipitation("arima_zscore", "negative", None, None, None)
    assert c.event_class == "anomalia_negativa" and not c.counted


@pytest.mark.parametrize(
    "verdict,expected,level",
    [
        ("within_normal_variability", "anomalia_estatistica", None),
        ("unusual_for_season", "extremo_sazonal", None),
        ("very_heavy_for_location", "extremo_local", "p95"),
        ("exceptional_for_location", "extremo_local", "p99"),
        (None, "anomalia_estatistica", None),  # sem evidência climatológica: hipótese conservadora
        ("record_accumulation", "anomalia_estatistica", None),  # veredito incoerente com detector diário
    ],
)
def test_arima_classes_follow_local_climatology(verdict, expected, level):
    c = classify_precipitation("arima_zscore", "positive", "ok", verdict, None)
    assert (c.event_class, c.level) == (expected, level)
    assert c.is_extreme == expected.startswith("extremo")


def test_accumulation_is_always_persistent_extreme():
    assert classify_precipitation("accumulation_percentile", "positive", None, "record_accumulation", None).level == "recorde"
    c = classify_precipitation("accumulation_percentile", "positive", None, None, "plausible_extreme_event")
    assert c.event_class == "extremo_acumulado" and c.high_absolute_intensity


def test_statistical_anomaly_with_news_is_still_not_extreme():
    c = classify_precipitation("arima_zscore", "positive", "ok", "within_normal_variability", None, verified_news=5)
    assert c.documented_impact and not c.is_extreme


def test_invalid_detector_or_direction_raises():
    with pytest.raises(ValueError):
        classify_precipitation("isolation_forest", "positive", None, None, None)
    with pytest.raises(ValueError):
        classify_precipitation("arima_zscore", "up", None, None, None)


@pytest.mark.parametrize(
    "percentile,cls,level",
    [(None, "anomalia_estatistica", None), (float("nan"), "anomalia_estatistica", None), (50, "anomalia_estatistica", None),
     (89.9, "anomalia_estatistica", None), (90, "extremo_local", "p90"), (5, "extremo_local", "p90"),
     (99.5, "extremo_local", "p99"), (0.5, "extremo_local", "p99")],
)
def test_thermal_classes_by_seasonal_percentile(percentile, cls, level):
    c = classify_thermal(percentile)
    assert (c.event_class, c.level) == (cls, level)


def test_thermal_percentile_out_of_range():
    with pytest.raises(ValueError):
        classify_thermal(101)


# ---------------------------------------------------------------------------
# Distribuição sazonal
# ---------------------------------------------------------------------------


def test_decluster_counts_consecutive_days_once_and_keeps_peak():
    frame = pd.DataFrame({
        "codigo_ibge": [1, 1, 1, 1, 2],
        "date": ["2024-05-01", "2024-05-02", "2024-05-03", "2024-05-10", "2024-05-02"],
        "abs_z": [3.1, 5.0, 3.2, 3.3, 4.0],
    })
    events = decluster(frame, ["codigo_ibge"], gap_days=1)
    assert len(events) == 3
    first = events[(events.codigo_ibge == 1)].sort_values("date").iloc[0]
    assert first["abs_z"] == 5.0 and first["event_days"] == 3
    assert str(first["event_start"].date()) == "2024-05-01" and str(first["event_end"].date()) == "2024-05-03"
    # um dia de intervalo ainda é o mesmo evento com gap_days=1; dois dias, não
    gap = pd.DataFrame({"codigo_ibge": [1, 1, 1], "date": ["2024-01-01", "2024-01-03", "2024-01-06"], "abs_z": [3, 4, 5]})
    assert len(decluster(gap, ["codigo_ibge"], gap_days=1)) == 2
    with pytest.raises(ValueError):
        decluster(gap, ["codigo_ibge"], gap_days=-1)


def test_decluster_empty_frame():
    empty = pd.DataFrame({"codigo_ibge": [], "date": [], "abs_z": []})
    assert decluster(empty, ["codigo_ibge"]).empty


def _exposure(days_per_season: dict[str, int], code: int = 1) -> pd.DataFrame:
    month_of = {"verao": 1, "outono": 4, "inverno": 7, "primavera": 10}
    return pd.DataFrame([{"codigo_ibge": code, "year": 2020, "month": month_of[s], "days": d}
                         for s, d in days_per_season.items()])


def _events(counts: dict[str, int], code: int = 1) -> pd.DataFrame:
    month_of = {"verao": 1, "outono": 4, "inverno": 7, "primavera": 10}
    rows = [{"codigo_ibge": code, "date": pd.Timestamp(2020, month_of[s], 1)} for s, n in counts.items() for _ in range(n)]
    return add_calendar(pd.DataFrame(rows))


def test_normalised_share_corrects_for_unequal_exposure():
    # mesma taxa (1 evento / 10 dias) em todas as estações, exposição desigual
    days = {"verao": 100, "outono": 400, "inverno": 200, "primavera": 300}
    events = _events({s: d // 10 for s, d in days.items()})
    table = seasonal_table(events, seasonal_exposure(_exposure(days), ["codigo_ibge"]), ["codigo_ibge"])
    assert np.allclose(table["share_norm"], 0.25)
    assert not np.allclose(table["share_abs"], 0.25)  # a contagem bruta enganaria
    assert np.isclose(table["share_abs"].sum(), 1) and np.isclose(table["share_norm"].sum(), 1)
    conc = concentration(table, ["codigo_ibge"], min_events=20)
    assert conc.loc[0, "concentration"] == pytest.approx(0, abs=1e-9)
    assert conc.loc[0, "chi2_pvalue"] == pytest.approx(1.0)
    assert conc.loc[0, "pattern"] == "sem_predominio"


def test_strong_concentration_is_significant():
    days = {s: 900 for s in ("verao", "outono", "inverno", "primavera")}
    table = seasonal_table(_events({"verao": 2, "outono": 30, "inverno": 25, "primavera": 3}),
                           seasonal_exposure(_exposure(days), ["codigo_ibge"]), ["codigo_ibge"])
    conc = concentration(table, ["codigo_ibge"])
    assert conc.loc[0, "dominant_season"] == "outono"
    assert conc.loc[0, "pattern"] == "predominio_outono"
    assert conc.loc[0, "autumn_winter_share"] == pytest.approx(55 / 60)
    assert 0 < conc.loc[0, "concentration"] < 1


def test_few_events_are_insufficient_and_missing_season_is_zero():
    days = {s: 900 for s in ("verao", "outono", "inverno", "primavera")}
    table = seasonal_table(_events({"inverno": 5}), seasonal_exposure(_exposure(days), ["codigo_ibge"]), ["codigo_ibge"])
    assert len(table) == 4 and table["n"].sum() == 5
    conc = concentration(table, ["codigo_ibge"])
    assert conc.loc[0, "pattern"] == "insuficiente" and np.isnan(conc.loc[0, "chi2_pvalue"])


def test_benjamini_hochberg_matches_hand_computation():
    q = benjamini_hochberg(np.array([0.01, 0.04, 0.03, np.nan, 0.5]))
    # m = 4 válidos; p·m/posto: 0.01→0.04, 0.03→0.06, 0.04→0.0533, 0.5→0.5;
    # mínimo acumulado de cima para baixo: 0.03 herda 0.0533
    assert np.allclose(q[[0, 1, 2, 4]], [0.04, 0.16 / 3, 0.16 / 3, 0.5])
    assert np.isnan(q[3])
    assert np.isnan(benjamini_hochberg(np.array([np.nan]))).all()


def test_rate_ratio_ci_covers_truth_and_handles_edges():
    ratio, low, high = rate_ratio_ci(40, 1000, 20, 1000)
    assert ratio == pytest.approx(2.0) and low < 2.0 < high and low > 1.0
    assert all(np.isnan(rate_ratio_ci(0, 100, 0, 100)))
    assert all(np.isnan(rate_ratio_ci(1, 0, 1, 100)))
    assert rate_ratio_ci(5, 100, 0, 100)[0] == np.inf


def test_morans_i_detects_spatial_structure():
    rng = np.random.default_rng(0)
    lat = rng.uniform(-30, -5, 400)
    lon = rng.uniform(-60, -35, 400)
    neighbors = knn_weights(lat, lon, k=8)
    smooth = morans_i(lat + rng.normal(0, 0.5, 400), neighbors, 99)
    noise = morans_i(rng.normal(size=400), neighbors, 99)
    assert smooth["I"] > 0.8 and smooth["p_value"] <= 0.02
    assert abs(noise["I"]) < 0.15 and noise["p_value"] > 0.02
    with pytest.raises(ValueError):
        morans_i(np.array([np.nan] * 20), neighbors[:20] % 20)


def test_atypical_municipality_differs_from_neighbours():
    conc = pd.DataFrame({"pattern": ["predominio_inverno"] + ["predominio_verao"] * 8 + ["insuficiente"]})
    neighbors = np.array([[j for j in range(10) if j != i][:8] for i in range(10)])
    flags = atypical_municipalities(conc, neighbors, min_agreeing=5)
    assert flags.iloc[0] and not flags.iloc[1:].any()


# ---------------------------------------------------------------------------
# Detector de temperatura/umidade
# ---------------------------------------------------------------------------


def synthetic_temperature(years: int = 6, seed: int = 1, spikes: dict | None = None) -> pd.Series:
    """DADOS SINTÉTICOS: ciclo anual + variância sazonal + ruído AR(1)."""
    rng = np.random.default_rng(seed)
    index = pd.date_range("2015-01-01", periods=int(365.25 * years), freq="D")
    phase = 2 * np.pi * (index.dayofyear.to_numpy() - 1) / 365.25
    sd = 1.5 + 1.0 * np.cos(phase)  # mais variável no "inverno"
    noise = np.zeros(len(index))
    eps = rng.normal(size=len(index))
    for t in range(1, len(index)):
        noise[t] = 0.6 * noise[t - 1] + np.sqrt(1 - 0.36) * eps[t]
    values = 22 + 5 * np.cos(phase) + sd * noise
    series = pd.Series(values, index=index)
    for day, delta in (spikes or {}).items():
        series[pd.Timestamp(day)] += delta
    return series


def test_thermal_detector_finds_injected_spikes_and_is_calibrated():
    spikes = {"2019-03-10": 12.0, "2020-08-20": -12.0}
    result = detect_thermal_anomalies(synthetic_temperature(spikes=spikes))
    flagged = {str(d): row for d, row in zip(result.anomalies["date"], result.anomalies.itertuples())}
    assert "2019-03-10" in flagged and flagged["2019-03-10"].direction == "positive"
    assert "2020-08-20" in flagged and flagged["2020-08-20"].direction == "negative"
    d = detect_thermal_anomalies(synthetic_temperature()).diagnostics  # série sem picos
    assert 0.9 < d["z_std"] < 1.1 and abs(d["z_mean"]) < 0.1
    assert d["rate_positive"] < 0.01 and d["rate_negative"] < 0.01
    assert result.exposure["scored_days"].sum() == result.diagnostics["n_scored"]
    assert result.exposure["year"].min() == 2017  # 2 anos de treino inicial


def test_thermal_detector_has_no_look_ahead():
    base = synthetic_temperature()
    changed = base.copy()
    changed["2020-06-01":] += 30  # mudar o futuro não pode alterar Z do passado
    a = detect_thermal_anomalies(base).anomalies
    b = detect_thermal_anomalies(changed).anomalies
    before = lambda f: f[pd.to_datetime(f["date"]) < "2020-01-01"].reset_index(drop=True)  # noqa: E731
    pd.testing.assert_frame_equal(before(a), before(b))


def test_thermal_detector_handles_missing_values():
    series = synthetic_temperature()
    series["2018-02-01":"2018-02-20"] = np.nan
    result = detect_thermal_anomalies(series)
    assert result.diagnostics["n_scored"] < len(series)
    assert result.anomalies["z"].notna().all()


def test_thermal_detector_rejects_bad_input():
    with pytest.raises(TypeError):
        detect_thermal_anomalies(pd.Series([1.0, 2.0]))
    short = synthetic_temperature(years=2)
    with pytest.raises(ValueError):
        detect_thermal_anomalies(short)
    dup = synthetic_temperature()
    with pytest.raises(ValueError):
        detect_thermal_anomalies(pd.concat([dup, dup.iloc[:1]]))
    with pytest.raises(ValueError):
        ThermalConfig(z_threshold=0)


# ---------------------------------------------------------------------------
# Avaliação do método
# ---------------------------------------------------------------------------


def _daily(years: int = 5, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2017-01-01", periods=365 * years, freq="D")
    winter = index.month.isin([6, 7, 8])
    z = pd.Series(rng.normal(size=len(index)) * np.where(winter, 2.0, 1.0), index=index)
    observed = pd.Series(np.where(rng.random(len(index)) < 0.4, rng.gamma(0.8, 10, len(index)), 0.0), index=index)
    return pd.DataFrame({"z_score": z}), observed


def test_seasonal_sigma_uses_only_past_years():
    daily, _ = _daily()
    zs = seasonal_sigma_z(daily)
    assert zs[daily.index.year == 2017].isna().all()
    later = zs[daily.index.year >= 2018]
    winter = later[later.index.month.isin([6, 7, 8])]
    assert winter.std() == pytest.approx(1.0, abs=0.15)  # reescalado pelo σ do inverno
    changed = daily.copy()
    changed.loc["2020-01-01":, "z_score"] *= 10
    pd.testing.assert_series_equal(seasonal_sigma_z(changed)[:"2019-12-31"], zs[:"2019-12-31"])


def test_heteroscedastic_residuals_concentrate_alerts_in_variable_season():
    daily, observed = _daily(years=8)
    m = evaluate_daily(daily, observed)
    assert m["brown_forsythe_p"] < 1e-6
    assert m["alerts_global_inverno"] > 5 * m["alerts_global_verao"]
    assert m["alerts_seasonal_inverno"] < m["alerts_global_inverno"]  # σ sazonal desfaz o viés


def test_climatological_flags_use_previous_years_only():
    index = pd.date_range("2015-01-01", periods=365 * 3, freq="D")
    observed = pd.Series(np.tile(np.r_[np.zeros(265), np.linspace(1, 100, 100)], 3), index=index)
    flags = climatological_flags(observed, 99)
    assert not flags[index.year == 2015].any()  # sem passado, sem limiar
    assert 0 < flags[index.year == 2016].sum() <= 3


# ---------------------------------------------------------------------------
# Correções da revisão independente
# ---------------------------------------------------------------------------


def test_incomplete_input_is_excluded_before_climatology():
    c = classify_precipitation("accumulation_percentile", "positive", None, "record_accumulation", None, 6,
                               complete_input=False)
    assert c.event_class == "dado_incompleto" and not c.counted and not c.is_extreme
    assert c.documented_impact  # a notícia continua registrada, mas o evento não entra nas contagens


@pytest.mark.parametrize(
    "percentile,direction,cls",
    [(5, "positive", "anomalia_estatistica"),  # mais quente que o previsto, mas valor baixo para a época
     (95, "positive", "extremo_local"), (5, "negative", "extremo_local"), (95, "negative", "anomalia_estatistica")],
)
def test_thermal_tail_must_match_direction(percentile, direction, cls):
    assert classify_thermal(percentile, direction).event_class == cls


def test_thermal_direction_validated():
    with pytest.raises(ValueError):
        classify_thermal(50, "up")


def test_decluster_merges_accumulation_window_with_daily_anomaly():
    frame = pd.DataFrame({
        "codigo_ibge": [1, 1, 1],
        "date": ["2024-05-02", "2024-05-06", "2024-05-20"],  # ARIMA em 02/05; acumulado de 5 dias até 06/05
        "start": ["2024-05-02", "2024-05-02", "2024-05-20"],
        "abs_z": [3.2, 2.0, 3.1],
    })
    events = decluster(frame, ["codigo_ibge"], gap_days=1, start_col="start")
    assert len(events) == 2
    first = events.sort_values("date").iloc[0]
    assert first["event_days"] == 2 and str(first["event_start"].date()) == "2024-05-02"
    # sem a janela, os dois seriam eventos separados (4 dias de distância)
    assert len(decluster(frame, ["codigo_ibge"], gap_days=1)) == 3


def test_seasonal_sigma_is_recentred():
    daily, _ = _daily(years=6)
    daily.loc[daily.index.month.isin([12, 1, 2]), "z_score"] += 2.0  # verão deslocado
    zs = seasonal_sigma_z(daily)
    summer = zs[(zs.index.year >= 2018) & zs.index.month.isin([12, 1, 2])]
    assert abs(summer.mean()) < 0.2
