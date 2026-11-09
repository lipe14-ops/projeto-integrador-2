"""Detecção estatística: preparação, ARIMA + Z-Score e acumulados."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.climate_news.agents.base import MunicipalityContext
from app.climate_news.agents.climatologist import ClimatologistAgent
from app.climate_news.agents.data_scientist import DataScientistAgent
from app.climate_news.agents.meteorologist import MeteorologistAgent
from app.climate_news.agents.orchestrator import decide_scientific_status
from app.climate_news.detection.accumulation import detect_accumulation_extremes
from app.climate_news.detection.arima_zscore import Anomaly, DetectionConfig, detect_anomalies
from app.climate_news.detection.preparation import aggregate_era5_12h_to_daily, prepare_daily_series
from tests.conftest import as_frame, synthetic_rain

FAST = DetectionConfig(max_p=1, max_q=1, seasonal="fourier")
CONTEXT = MunicipalityContext(name="Teste", uf="RS", region="Sul")


def run(series: pd.Series, config: DetectionConfig = FAST):
    prepared, quality = prepare_daily_series(as_frame(series))
    return detect_anomalies(prepared, config, quality), prepared


@pytest.fixture(scope="module")
def base_series():
    return synthetic_rain(years=5)


@pytest.fixture(scope="module")
def base_result(base_series):
    return run(base_series)


# ---- preparação ------------------------------------------------------------


def test_inconsistent_data_is_flagged_not_used():
    s = synthetic_rain(years=1)
    frame = as_frame(s)
    frame.loc[10, "precipitation_mm"] = -5.0  # negativo
    frame.loc[20, "precipitation_mm"] = 1500.0  # fisicamente implausível
    frame.loc[30, "precipitation_mm"] = 450.0  # suspeito, mantido
    dup_same = frame.iloc[[40]]  # duplicata idêntica
    dup_conflict = frame.iloc[[50]].assign(precipitation_mm=99.0)  # duplicata conflitante
    frame = pd.concat([frame, dup_same, dup_conflict]).sample(frac=1, random_state=1)  # desordenado
    series, quality = prepare_daily_series(frame)

    assert series.index.is_monotonic_increasing
    assert np.isnan(series.iloc[10]) and np.isnan(series.iloc[20]) and np.isnan(series.iloc[50])
    assert series.iloc[30] == 450.0
    assert quality.n_negative == 1
    assert quality.n_implausible == 1
    assert quality.n_suspect == 1
    assert quality.n_duplicates_consolidated == 1
    assert quality.n_duplicates_conflicting == 1


def test_missing_days_are_nan_not_zero():
    s = synthetic_rain(years=1)
    frame = as_frame(s).drop(index=range(100, 110))  # datas faltando na entrada
    frame.loc[200, "precipitation_mm"] = np.nan
    series, quality = prepare_daily_series(frame)
    assert series.loc["2015-04-11":"2015-04-20"].isna().all()
    assert quality.n_missing_dates_inserted == 10
    assert quality.n_missing == 11
    assert (series == 0).sum() == (s.drop(s.index[range(100, 110)]).drop(s.index[200]) == 0).sum()


def test_era5_12h_aggregation_maps_halves_to_utc_day():
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(
                ["2024-05-01 12:00", "2024-05-02 00:00", "2024-05-02 12:00", "2024-05-03 00:00", "2024-05-03 12:00"],
                utc=True,
            ),
            "precipitacao": [10.0, 5.0, 0.0, np.nan, 3.0],
        }
    )
    daily, incomplete = aggregate_era5_12h_to_daily(frame)
    by_day = daily.set_index("date")["precipitation_mm"]
    assert by_day[pd.Timestamp("2024-05-01")] == 15.0  # 00–12 + 12–24 UTC
    assert np.isnan(by_day[pd.Timestamp("2024-05-02")])  # metade ausente -> dia ausente
    assert np.isnan(by_day[pd.Timestamp("2024-05-03")])  # só uma metade disponível
    assert incomplete == 2


# ---- ARIMA + Z ----------------------------------------------------------------


def test_series_without_anomalies_has_low_false_positive_rate():
    rng = np.random.default_rng(3)
    index = pd.date_range("2015-01-01", periods=365 * 4, freq="D")
    smooth = np.expm1(2.0 + 0.5 * np.sin(2 * np.pi * index.dayofyear / 365.25) + rng.normal(0, 0.2, len(index)))
    result, _ = run(pd.Series(smooth, index=index))
    assert len(result.positive_anomalies) <= 0.005 * result.diagnostics["n_scored"]
    assert result.diagnostics["all_blocks_converged"]


def test_isolated_peaks_are_detected(base_series):
    series = base_series.copy()
    peaks = pd.to_datetime(["2017-07-10", "2018-08-05", "2019-06-20", "2019-09-01"])
    series.loc[peaks] = 180.0
    series.loc[peaks - pd.Timedelta(days=1)] = 0.0
    result, _ = run(series)
    detected = {pd.Timestamp(a.date) for a in result.positive_anomalies}
    assert set(peaks) <= detected
    for anomaly in result.positive_anomalies:
        if pd.Timestamp(anomaly.date) in peaks:
            assert anomaly.z_score > 3
            assert anomaly.classification == "statistical_anomaly_above_expected"
            assert anomaly.observed_mm == 180.0


def test_prolonged_event_detected_by_accumulation_and_classified_as_prolonged(base_series):
    series = base_series.copy()
    event = pd.date_range("2019-07-01", periods=7, freq="D")
    series.loc[event] = 45.0
    prepared, quality = prepare_daily_series(as_frame(series))
    result = detect_anomalies(prepared, FAST, quality)
    accumulation = detect_accumulation_extremes(prepared, pd.Timestamp(result.scored_period[0]))
    in_event = [a for a in accumulation if event[0] <= pd.Timestamp(a.date) <= event[-1] + pd.Timedelta(days=4)]
    assert in_event, "acumulado extremo de 7 dias deve ser detectado"
    review = MeteorologistAgent().review(in_event[0], prepared, CONTEXT)
    assert review.metrics["persistence"] == "prolonged"
    assert review.verdict == "plausible_extreme_event"
    # o ARIMA marca ao menos o início do episódio (surpresa em relação ao passado)
    arima_days = {pd.Timestamp(a.date) for a in result.positive_anomalies}
    assert event[0] in arima_days


def test_seasonal_series_selects_fourier_and_does_not_flag_wet_season():
    series = synthetic_rain(years=5, wet_amp=0.45, mean_amp=0.9, seed=11)
    result, _ = run(series, DetectionConfig(max_p=1, max_q=1, seasonal="auto"))
    assert result.selected_spec["seasonal"] == "fourier"
    rate = len(result.positive_anomalies) / result.diagnostics["n_scored"]
    assert rate < 0.02


def test_missing_values_do_not_become_anomalies(base_series):
    series = base_series.copy()
    gap = pd.date_range("2018-03-01", periods=20, freq="D")
    series.loc[gap] = np.nan
    series.loc["2018-03-21"] = 120.0
    result, prepared = run(series)
    assert prepared.loc[gap].isna().all()
    assert result.daily.loc[gap, "z_score"].isna().all()
    flagged = {a.date.isoformat(): a for a in result.positive_anomalies}
    assert "2018-03-21" in flagged
    assert "previous_day_missing" in flagged["2018-03-21"].quality_flags


def test_many_dry_days_trace_anomalies_are_rejected():
    series = synthetic_rain(years=5, wet_base=0.08, wet_amp=0.06, mean_mm=4, seed=5)
    assert (series == 0).mean() > 0.85
    result, prepared = run(series)
    data = DataScientistAgent()
    for anomaly in result.positive_anomalies:
        review = data.review_anomaly(anomaly)
        if anomaly.observed_mm < 1.0:
            assert review.verdict == "possible_artifact"
            climate = ClimatologistAgent().review(anomaly, prepared, CONTEXT)
            weather = MeteorologistAgent().review(anomaly, prepared, CONTEXT)
            assert decide_scientific_status(review, climate, weather)[0] == "rejected"


def test_no_future_information_leaks_into_past_scores(base_series):
    full, _ = run(base_series)
    cut = pd.Timestamp("2018-06-30")
    truncated, _ = run(base_series[:cut])
    common = truncated.daily.index
    np.testing.assert_allclose(
        full.daily.loc[common, "z_score"].to_numpy(),
        truncated.daily["z_score"].to_numpy(),
        rtol=1e-6,
        equal_nan=True,
    )


def test_reference_statistics_come_from_past_only(base_result):
    result, _ = base_result
    for block in result.blocks:
        assert block.train_end < block.block_start
        assert block.n_reference_residuals > 300


def test_anomaly_records_have_required_fields(base_result):
    result, _ = base_result
    payload = result.to_dict()
    assert payload["run_id"] and payload["algorithm_version"]
    for anomaly in payload["anomalies"]:
        for key in ("date", "observed_mm", "predicted_mm", "residual", "z_score", "classification", "model_block"):
            assert anomaly[key] is not None


def test_short_series_is_rejected():
    with pytest.raises(ValueError, match="curta"):
        run(synthetic_rain(years=1))


def test_dry_season_rain_is_unusual_for_season_not_normal():
    # estação seca marcada (jun–ago quase sem chuva), como no Cerrado
    series = synthetic_rain(years=5, wet_base=0.3, wet_amp=0.3, seed=9)
    dry = series.index.month.isin([6, 7, 8])
    series[dry] = 0.0
    day = pd.Timestamp("2019-07-15")
    series.loc[day] = 15.0
    prepared, _ = prepare_daily_series(as_frame(series))
    anomaly = Anomaly(
        date=day.date(), observed_mm=15.0, predicted_mm=0.1, residual=2.6, residual_mm=14.9, z_score=3.4,
        direction="positive", severity="moderate", classification="statistical_anomaly_above_expected",
        model_block="2019",
    )
    review = ClimatologistAgent().review(anomaly, prepared, CONTEXT)
    assert review.verdict == "unusual_for_season"
    assert review.metrics["seasonal_wet_day_percentile"] is None  # amostra de dias chuvosos insuficiente
