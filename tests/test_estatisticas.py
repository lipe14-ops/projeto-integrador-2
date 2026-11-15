"""Estatísticas gerais (``app/estatisticas``) sobre dados mensais SINTÉTICOS.

Confere a ponderação por área, os recortes, as estações (verão em dois anos),
a remoção do ciclo sazonal antes da comparação ENSO e a API.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.estatisticas import calculos as c
from app.estatisticas import router as est_router
from app.estatisticas.service import EstatisticasService

ANOS = range(2015, 2026)


def _mensal() -> pd.DataFrame:
    """3 municípios: Norte grande e quente (100 km², 26 °C), Sul pequeno e frio (10 km², 16 °C),
    município novo sem região cadastrada (MT) e uma lagoa sem dado nenhum."""
    linhas = []
    for ano in ANOS:
        for mes in range(1, 13):
            ciclo = 2 * np.cos(2 * np.pi * (mes - 1) / 12)  # mais quente em jan
            linhas += [
                {"codigo_ibge": 1, "year": ano, "month": mes, "temperatura": 26 + ciclo, "umidade": 80.0,
                 "precipitacao": 200.0, "regiao": "Norte", "uf": "AM", "area_km2": 100.0},
                {"codigo_ibge": 2, "year": ano, "month": mes, "temperatura": 16 + ciclo, "umidade": 70.0,
                 "precipitacao": 100.0 + (30 if ano == 2023 else 0), "regiao": "Sul", "uf": "RS", "area_km2": 10.0},
                {"codigo_ibge": 3, "year": ano, "month": mes, "temperatura": 24 + ciclo, "umidade": 60.0,
                 "precipitacao": 120.0, "regiao": None, "uf": "MT", "area_km2": 10.0},
                {"codigo_ibge": 4300001, "year": ano, "month": mes, "temperatura": None, "umidade": None,
                 "precipitacao": None, "regiao": None, "uf": "RS", "area_km2": 50.0},
            ]
    return pd.DataFrame(linhas)


def _enso() -> pd.DataFrame:
    # El Niño de mai/2023 a abr/2024 (12 meses ≥ 0,5); o resto neutro
    linhas = []
    for ano in ANOS:
        for mes in range(1, 13):
            dentro = (ano == 2023 and mes >= 5) or (ano == 2024 and mes <= 4)
            linhas.append({"year": ano, "month": mes, "oni": 1.2 if dentro else 0.0})
    return pd.DataFrame(linhas)


@pytest.fixture
def service():
    nomes = {1: ("Norteia", "AM"), 2: ("Sulina", "RS"), 3: ("Nova", "MT"), 4300001: ("Lagoa", "RS")}
    return EstatisticasService(mensal=_mensal(), enso=_enso(), nomes=nomes)


def test_preparar_completa_regiao_pela_uf_e_descarta_lagoa(service):
    df = service.df
    assert set(df["codigo_ibge"]) == {1, 2, 3}
    assert (df.loc[df.codigo_ibge == 3, "regiao"] == "Centro-Oeste").all()
    # dezembro pertence ao verão do ano seguinte
    dez = df[(df.year == 2020) & (df.month == 12)]
    assert (dez["season_year"] == 2021).all() and (dez["estacao"] == "verao").all()


def test_resumo_pondera_pela_area(service):
    r = service.resumo(c.Recorte())
    t = r["indicadores"]["temperatura"]
    # média anual do ciclo coseno é zero: 26, 16 e 24 °C com pesos 100, 10 e 10
    esperado = (26 * 100 + 16 * 10 + 24 * 10) / 120
    assert t["valor"] == pytest.approx(esperado, abs=0.01)
    assert t["media_simples_municipios"] == pytest.approx((26 + 16 + 24) / 3, abs=0.01)
    assert r["municipios_com_dados"] == 3
    assert r["meses"] == 132
    assert t["diferenca"] is None  # período completo não tem comparação
    assert r["indicadores"]["precipitacao"]["anual_equivalente"] is not None


def test_resumo_regiao_e_comparacao(service):
    r = service.resumo(c.Recorte(2023, 2023, regiao="Sul"))
    p = r["indicadores"]["precipitacao"]
    assert p["valor"] == pytest.approx(130.0)
    assert p["referencia_2015_2025"] == pytest.approx(100 + 30 / 11, abs=0.01)
    assert p["diferenca"] == pytest.approx(130 - (100 + 30 / 11), abs=0.01)
    assert r["municipios_com_dados"] == 1
    assert r["extremos_mensais"]["precipitacao_max"]["municipio"] == "Sulina"


def test_serie_total_anual_so_com_ano_completo(service):
    s = service.serie(c.Recorte(2015, 2016))
    assert len(s["mensal"]) == 24
    assert all(a["precipitacao_total"] is not None for a in s["anual"])
    s_enso = service.serie(c.Recorte(enso="el_nino"))
    assert all(a["precipitacao_total"] is None for a in s_enso["anual"])  # meses diferentes por ano
    assert {a["ano"] for a in s_enso["anual"]} == {2023, 2024}
    assert len(s["ciclo_mensal"]) == 12


def test_sazonal_exige_tres_meses(service):
    s = service.sazonal(c.Recorte())
    veroes = [x["ano"] for x in s["por_ano"] if x["estacao"] == "verao"]
    assert 2015 not in veroes  # sem dez/2014
    assert veroes == list(range(2016, 2026))
    inverno = next(x for x in s["resumo"] if x["estacao"] == "inverno")
    verao = next(x for x in s["resumo"] if x["estacao"] == "verao")
    assert verao["temperatura"]["media"] > inverno["temperatura"]["media"]


def test_enso_remove_o_ciclo_sazonal(service):
    e = service.enso(c.Recorte())
    assert e["meses_por_fase"]["el_nino"] == 12
    sul = {(x["estacao"], x["fase"]): x for x in e["linhas"] if x["escopo"] == "Sul"}
    # a temperatura só tem ciclo sazonal: anomalia nula em qualquer fase
    assert sul[("todas", "el_nino")]["temperatura"] == pytest.approx(0, abs=1e-6)
    # chuva extra só em 2023: El Niño (8 meses de 2023 em 12) fica acima do neutro
    assert sul[("todas", "el_nino")]["precipitacao"] > sul[("todas", "neutro")]["precipitacao"]
    assert sul[("todas", "el_nino")]["precipitacao_pct"] is not None


def test_mapa_e_quebras(service):
    m = service.mapa(c.Recorte(), "temperatura")
    assert m["resumo"]["com_valor"] == 3
    assert m["quebras"] == sorted(m["quebras"])
    assert {v["codigo_ibge"] for v in m["valores"]} == {1, 2, 3}
    assert c.quebras_quantis(pd.Series([1.0, 1.0])) == []
    with pytest.raises(ValueError):
        service.mapa(c.Recorte(), "vento")


def test_regioes_e_ufs(service):
    r = service.regioes(c.Recorte())
    norte = next(x for x in r["regioes"] if x["regiao"] == "Norte")
    nordeste = next(x for x in r["regioes"] if x["regiao"] == "Nordeste")
    assert norte["municipios"] == 1 and norte["umidade"] == pytest.approx(80)
    assert nordeste["municipios"] == 0 and nordeste["temperatura"] is None
    assert len([x for x in r["ciclo_mensal"] if x["regiao"] == "Sul"]) == 12
    assert {u["uf"] for u in service.ufs()} == {"AM", "RS", "MT"}


def test_recorte_valida():
    with pytest.raises(ValueError):
        c.Recorte(2020, 2018).validar()
    with pytest.raises(ValueError):
        c.Recorte(regiao="Atlântida").validar()


def test_api(service, monkeypatch):
    from fastapi import FastAPI

    monkeypatch.setattr(est_router, "get_service", lambda: service)
    app = FastAPI()
    app.include_router(est_router.router, prefix="/api/estatisticas")
    client = TestClient(app)
    assert client.get("/api/estatisticas/resumo", params={"regiao": "Sul"}).json()["municipios_com_dados"] == 1
    assert client.get("/api/estatisticas/resumo", params={"inicio": 2020, "fim": 2018}).status_code == 422
    assert client.get("/api/estatisticas/resumo", params={"regiao": "X"}).status_code == 422
    assert client.get("/api/estatisticas/mapa", params={"variavel": "precipitacao"}).status_code == 200
    assert client.get("/api/estatisticas/abrangencia").json()["municipios_com_dados"] == 3
    for rota in ("serie", "sazonal", "regioes", "enso", "ufs", "metodo"):
        assert client.get(f"/api/estatisticas/{rota}").status_code == 200


def test_panorama_anomalias_sobre_snapshot_sintetico(tmp_path):
    from app.climate_news.analysis.service import AnalysisService
    from app.estatisticas.anomalias import panorama
    from tests.test_analysis_api import _snapshot

    svc = AnalysisService(_snapshot(tmp_path))
    p = panorama(svc, c.Recorte())
    assert p["recorte"]["inicio"] == 2017  # anos anteriores só treinam os modelos
    chuva = p["variaveis"][0]
    # mesma contagem do mapa coroplético (filtros e desagrupamento idênticos)
    mapa = svc.choropleth("contagem", __import__("app.climate_news.analysis.service", fromlist=["Filters"]).Filters())
    assert chuva["totais"]["todas"]["eventos"] == mapa["summary"]["total_events"]
    assert sum(a["todas"] for a in chuva["por_ano"]) == chuva["totais"]["todas"]["eventos"]
    assert sum(e["todas"] for e in chuva["por_estacao"]) == chuva["totais"]["todas"]["eventos"]
    assert chuva["ranking"][0]["municipio"] in {"A", "B"}  # C tem menos de 20 eventos
    sul = panorama(svc, c.Recorte(regiao="Sul", estacao="outono"))["variaveis"][0]
    assert all(x["todas"] == 0 for x in sul["por_regiao"] if x["regiao"] != "Sul")
    assert all(x["todas"] == 0 for x in sul["por_estacao"] if x["estacao"] != "outono")


def test_comparacao_vazia_quando_recorte_contem_todos_os_meses(service):
    # todo o El Niño sintético (mai/2023–abr/2024) está em 2023–2024: comparar com 2015–2025 não faz sentido
    r = service.resumo(c.Recorte(2023, 2024, enso="el_nino"))
    assert r["meses"] == r["meses_referencia"] == 12
    assert r["indicadores"]["temperatura"]["diferenca"] is None
