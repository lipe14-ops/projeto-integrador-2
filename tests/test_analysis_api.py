"""Serviço e API ``/api/analysis`` sobre um snapshot SINTÉTICO (gerado aqui).

Checa a consistência entre os valores do mapa e as contagens/exposição, o
tratamento de municípios sem dados ou com poucos eventos e os erros da API.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.climate_news.analysis import router as analysis_router
from app.climate_news.analysis.service import AnalysisService, Filters, SnapshotMissing

MONTHS = [(y, m) for y in range(2017, 2026) for m in range(1, 13)]


def _snapshot(tmp_path):
    """4 municípios: A (outono forte), B (uniforme), C (poucos eventos), D (sem detecção)."""
    municipalities = pd.DataFrame({
        "codigo_ibge": [1, 2, 3, 4],
        "nome": ["A", "B", "C", "D"],
        "uf": ["RS", "RS", "SP", "SP"],
        "regiao": ["Sul", "Sul", "Sudeste", "Sudeste"],
        "latitude": [-30.0, -29.5, -23.5, -22.0],
        "longitude": [-51.0, -51.5, -46.6, -47.0],
    })
    enso = pd.DataFrame([{"year": y, "month": m, "oni": 0.0, "phase_episode": "el_nino" if y == 2023 else "neutro",
                          "phase_monthly": "neutro"} for y, m in MONTHS])
    exposure = pd.DataFrame([{"codigo_ibge": c, "year": y, "month": m, "valid_days": 30}
                             for c in (1, 2, 3) for y, m in MONTHS])
    rows = []

    def add(code, year, month, day, cls="extremo_local", news=False):
        rows.append({"codigo_ibge": code, "anomaly_date": pd.Timestamp(year, month, day), "detector": "arima_zscore",
                     "event_class": cls, "is_extreme": cls.startswith("extremo"), "documented_impact": news,
                     "z_score": 3.5, "observed_mm": 50.0 if news else 15.0, "counted": cls != "artefato_provavel",
                     "verified_news": int(news), "news_investigated": code != 2, "high_intensity": news})

    for year in range(2017, 2026):  # A: 4 eventos de outono e 1 de verão por ano
        for month in (3, 4, 5, 4):
            add(1, year, month, 3 if month != 4 or not any(r["anomaly_date"] == pd.Timestamp(year, 4, 3) for r in rows) else 20)
        add(1, year, 1, 10, cls="anomalia_estatistica", news=True)
    for year in range(2017, 2026):  # B: um evento por estação por ano
        for month in (1, 4, 7, 10):
            add(2, year, month, 15)
    add(3, 2020, 7, 1)
    add(3, 2020, 7, 2)  # dia seguinte: mesmo evento após o desagrupamento
    add(3, 2021, 7, 1, cls="artefato_provavel")  # não entra em nenhuma contagem
    anomalies = pd.DataFrame(rows)
    for name, frame in {"municipios": municipalities, "enso": enso, "precipitacao_anomalias": anomalies,
                        "precipitacao_exposicao": exposure}.items():
        frame.to_parquet(tmp_path / f"{name}.parquet", index=False)
    return tmp_path


@pytest.fixture
def service(tmp_path):
    return AnalysisService(_snapshot(tmp_path))


@pytest.fixture
def client(service, monkeypatch):
    from app.main import app

    monkeypatch.setattr(analysis_router, "get_service", lambda: service)
    return TestClient(app)


def _values(result):
    return {v["codigo_ibge"]: v for v in result["values"]}


def test_rate_equals_events_over_valid_days(service):
    result = service.choropleth("taxa", Filters())
    values = _values(result)
    assert values[1]["n"] == 45 and values[1]["days"] == 108 * 30
    assert values[1]["value"] == pytest.approx(1000 * 45 / (108 * 30), abs=1e-3)
    assert values[3]["n"] == 1  # dois dias consecutivos = 1 evento; artefato excluído
    assert 4 not in values and result["summary"]["without_detection"] == 1
    assert result["summary"]["total_events"] == sum(v["n"] for v in values.values())
    assert result["unit"] == "eventos por 1.000 dias válidos" and result["definition"]


def test_season_filter_restricts_events_and_exposure(service):
    values = _values(service.choropleth("taxa", Filters(season="outono")))
    assert values[1]["n"] == 36 and values[1]["days"] == 9 * 3 * 30
    assert values[2]["n"] == 9


def test_insufficient_municipality_is_not_coloured(service):
    values = _values(service.choropleth("outono_inverno", Filters()))
    assert values[3]["status"] == "insuficiente" and values[3]["value"] is None
    assert values[1]["value"] == pytest.approx(100 * 36 / 45, abs=0.5)  # exposição igual por estação
    assert values[2]["value"] == pytest.approx(50, abs=0.5)


def test_dominant_season_is_categorical(service):
    values = _values(service.choropleth("estacao_dominante", Filters()))
    assert values[1]["category"] == "predominio_outono"
    assert values[2]["category"] == "sem_predominio"
    assert values[3]["category"] is None and values[3]["status"] == "insuficiente"


def test_class_filters(service):
    stats = _values(service.choropleth("contagem", Filters(event_class="estatisticas")))
    extremes = _values(service.choropleth("contagem", Filters(event_class="extremos")))
    impact = _values(service.choropleth("contagem", Filters(event_class="impacto")))
    assert stats[1]["n"] == 9 and extremes[1]["n"] == 36 and impact[1]["n"] == 9
    assert stats[2]["n"] == 0


def test_enso_ratio(service):
    values = _values(service.choropleth("razao_enso", Filters(), compare_phase="el_nino"))
    assert values[2]["value"] == pytest.approx(1.0)  # B: mesma taxa em todos os anos


def test_ignored_filters_are_reported(service):
    result = service.choropleth("outono_inverno", Filters(season="verao"))
    assert result["ignored_filters"] == ["season"]
    assert service.choropleth("razao_enso", Filters(enso_phase="la_nina"))["ignored_filters"] == ["enso_phase"]
    assert service.choropleth("taxa", Filters(season="verao"))["ignored_filters"] == []
    with pytest.raises(ValueError):  # snapshot sintético não tem meses de La Niña
        service.choropleth("taxa", Filters(enso_phase="la_nina"))


def test_municipality_enso_respects_season(service):
    rows = service.municipality(1, Filters(season="outono"))["enso"]
    assert rows and {r["season"] for r in rows} == {"outono"}


def test_invalid_filters_raise(service):
    with pytest.raises(ValueError):
        service.choropleth("participacao", Filters())  # exige estação
    with pytest.raises(ValueError):
        service.choropleth("inexistente", Filters())
    with pytest.raises(ValueError):
        Filters(start_year=2024, end_year=2020).validate()
    with pytest.raises(ValueError):
        Filters(variable="temperatura_alta", event_class="impacto").validate()
    with pytest.raises(SnapshotMissing):
        service.choropleth("taxa", Filters(variable="temperatura_alta"))  # snapshot sem térmica


def test_missing_snapshot(tmp_path):
    with pytest.raises(SnapshotMissing):
        AnalysisService(tmp_path / "vazio").ensure_loaded()


def test_municipality_comparison(service):
    result = service.municipality(1, Filters())
    shares = {s["season"]: s["share_norm"] for s in result["seasons"]}
    assert shares["outono"] == pytest.approx(0.8, abs=0.01)
    assert np.isclose(sum(shares.values()), 1)
    assert result["summary"]["pattern"] == "predominio_outono"
    assert {"estado", "regiao", "brasil"} <= set(result["comparison"])
    with pytest.raises(KeyError):
        service.municipality(999, Filters())


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_api_choropleth_and_definitions(client):
    response = client.get("/api/analysis/coropletico", params={"metric": "taxa", "season": "outono"})
    assert response.status_code == 200
    assert response.json()["filters"]["season"] == "outono"
    definitions = client.get("/api/analysis/definicoes").json()
    assert definitions["variables"]["temperatura_alta"]["available"] is False
    assert "anomalia_estatistica" in definitions["precipitation_classes"]
    assert client.get("/analysis/definicoes").status_code == 200  # caminho do proxy do Vite


@pytest.mark.parametrize(
    "params,status",
    [
        ({"metric": "participacao"}, 422),
        ({"metric": "taxa", "variable": "vento"}, 422),
        ({"metric": "taxa", "start_year": 2024, "end_year": 2020}, 422),
        ({"metric": "taxa", "variable": "umidade_alta", "event_class": "impacto"}, 422),
        ({"metric": "taxa", "variable": "temperatura_alta"}, 503),
    ],
)
def test_api_errors(client, params, status):
    assert client.get("/api/analysis/coropletico", params=params).status_code == status


def test_api_municipality_regions_ranking(client):
    assert client.get("/api/analysis/municipios/999").status_code == 404
    body = client.get("/api/analysis/municipios/1").json()
    assert body["nome"] == "A"
    regions = client.get("/api/analysis/regioes").json()
    assert any(p["regiao"] == "Brasil" for p in regions["pooled"])
    ranking = client.get("/api/analysis/ranking", params={"season": "outono", "limit": 5}).json()
    assert ranking[0]["codigo_ibge"] == 1
    assert client.get("/api/analysis/ranking").status_code == 422  # estação obrigatória


# ---------------------------------------------------------------------------
# Notícias × intensidade e visão geral
# ---------------------------------------------------------------------------


def test_news_by_intensity_uses_only_investigated_events(service):
    result = service.news_by_intensity()
    # investigados: município A (45 eventos, 9 com notícia) e C (2 contados); B não foi investigado
    assert result["investigated_events"] == 47
    assert result["overall"]["with_news"] == 9
    bins = {b["label"]: b for b in result["by_intensity_daily"]}
    assert bins["40–60 mm"]["n"] == 9 and bins["40–60 mm"]["pct"] == 100.0  # 50 mm, todos com notícia
    assert bins["< 20 mm"]["n"] == 38 and bins["< 20 mm"]["pct"] == 0.0
    assert bins["≥ 100 mm"]["n"] == 0 and bins["≥ 100 mm"]["pct"] is None
    assert result["by_high_intensity"]["alta"]["pct"] == 100.0
    ci = bins["40–60 mm"]
    assert ci["ci_low"] < 100.0 and ci["ci_high"] == 100.0  # Wilson: limite inferior < 100% com n = 9
    assert result["caveats"]


def test_news_by_intensity_requires_investigation_flag(tmp_path):
    directory = _snapshot(tmp_path)
    frame = pd.read_parquet(directory / "precipitacao_anomalias.parquet").drop(columns="news_investigated")
    frame.to_parquet(directory / "precipitacao_anomalias.parquet", index=False)
    with pytest.raises(SnapshotMissing):
        AnalysisService(directory).news_by_intensity()


def test_overview_and_api(client, service):
    overview = service.overview()
    assert overview["municipalities"] == 4 and overview["rain_events"] > 0
    assert client.get("/api/analysis/visao-geral").status_code == 200
    body = client.get("/api/analysis/noticias-intensidade").json()
    assert body["investigated_events"] == 47
