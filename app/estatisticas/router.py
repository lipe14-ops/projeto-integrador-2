"""API ``/api/estatisticas``: panorama climático nacional (Estatísticas Gerais).

Todas as agregações são feitas no servidor sobre a visão mensal ``clima_mensal``
(nunca os registros diários de todos os municípios no navegador).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.climate_news.analysis.service import SnapshotMissing
from app.climate_news.analysis.service import get_service as get_analysis_service
from app.estatisticas import anomalias
from app.estatisticas.calculos import ANO_FIM, ANO_INICIO, METODO, Recorte
from app.estatisticas.service import get_service

router = APIRouter(tags=["Estatísticas gerais"])

Regiao = Literal["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
Estacao = Literal["verao", "outono", "inverno", "primavera"]
Fase = Literal["el_nino", "la_nina", "neutro"]


def recorte(
    inicio: int = Query(ANO_INICIO, ge=ANO_INICIO, le=ANO_FIM, description="Ano inicial"),
    fim: int = Query(ANO_FIM, ge=ANO_INICIO, le=ANO_FIM, description="Ano final"),
    regiao: Regiao | None = Query(None),
    estacao: Estacao | None = Query(None, description="Estação meteorológica do Hemisfério Sul"),
    enso: Fase | None = Query(None, description="Fase ENSO (episódios NOAA/CPC)"),
) -> Recorte:
    r = Recorte(inicio, fim, regiao, estacao, enso)
    try:
        r.validar()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return r


@router.get("/abrangencia")
def abrangencia():
    """Cobertura da base: municípios, período, variáveis e fonte."""
    return get_service().abrangencia()


@router.get("/metodo")
def metodo():
    """Critérios de cálculo de cada indicador."""
    return METODO


@router.get("/resumo")
def resumo(r: Recorte = Depends(recorte)):
    """Indicadores principais do recorte (média ponderada pela área) e comparação com 2015–2025."""
    return get_service().resumo(r)


@router.get("/serie")
def serie(r: Recorte = Depends(recorte)):
    """Série mensal, anual e ciclo mensal médio do Brasil ou da região."""
    return get_service().serie(r)


@router.get("/sazonal")
def sazonal(r: Recorte = Depends(recorte)):
    """Valores por estação e ano, com resumo por estação."""
    return get_service().sazonal(r)


@router.get("/regioes")
def regioes(r: Recorte = Depends(recorte)):
    """Médias das cinco regiões e ciclo mensal médio de cada uma."""
    return get_service().regioes(r)


@router.get("/enso")
def enso(r: Recorte = Depends(recorte)):
    """Anomalias (sem o ciclo sazonal) por fase ENSO, estação e região."""
    return get_service().enso(r)


@router.get("/mapa")
def mapa(variavel: Literal["temperatura", "umidade", "precipitacao"] = Query("temperatura"),
         r: Recorte = Depends(recorte)):
    """Média de cada município no recorte, com quebras por quantis (o filtro de região não se aplica)."""
    return get_service().mapa(r, variavel)


@router.get("/ufs")
def ufs():
    """Médias 2015–2025 por unidade federativa."""
    return get_service().ufs()


@router.get("/anomalias")
def panorama_anomalias(r: Recorte = Depends(recorte)):
    """Eventos anômalos detectados, por variável, classe, ano, estação, região e município."""
    try:
        return _anomalias_cache(r)
    except SnapshotMissing as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


_cache: dict[Recorte, dict] = {}


def _anomalias_cache(r: Recorte) -> dict:
    if r not in _cache:
        if len(_cache) > 64:
            _cache.clear()
        _cache[r] = anomalias.panorama(get_analysis_service(), r)
    return _cache[r]


def aquecer() -> None:
    """Carrega ``clima_mensal`` e o recorte padrão das anomalias em segundo plano (≈ 25 s)."""
    import logging
    import os
    import threading

    if os.getenv("ESTATISTICAS_AQUECER", "1") != "1":
        return

    def tarefa():
        try:
            get_service().resumo(Recorte())
            _anomalias_cache(Recorte())
        except Exception:  # noqa: BLE001 — o aquecimento é opcional; a 1ª requisição refaz a carga
            logging.getLogger(__name__).exception("falha ao aquecer as estatísticas")

    threading.Thread(target=tarefa, daemon=True, name="aquecer-estatisticas").start()
