"""API ``/api/analysis``: mapa coroplético, distribuição sazonal e definições.

Lê o snapshot gerado por ``cli.py`` (ver ``snapshot.py``); a única consulta ao
banco é a malha municipal simplificada, usada para desenhar o mapa.
"""

from __future__ import annotations

import threading
from json import loads
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.climate_news.analysis.service import (
    CLASS_FILTERS,
    METRICS,
    VARIABLES,
    Filters,
    SnapshotMissing,
    get_service,
)
from app.climate_news.analysis.seasons import ENSO_PHASES, SEASONS
from app.database import get_db

router = APIRouter(tags=["Análise espacial e sazonal"])

Variable = Literal[tuple(VARIABLES)]  # type: ignore[valid-type]
EventClass = Literal[tuple(CLASS_FILTERS)]  # type: ignore[valid-type]
Metric = Literal[tuple(METRICS)]  # type: ignore[valid-type]
Season = Literal[SEASONS]  # type: ignore[valid-type]
EnsoPhase = Literal[ENSO_PHASES]  # type: ignore[valid-type]

# Tolerância de simplificação (graus). 0,01° ≈ 1 km: suficiente para a escala
# nacional; reduz a malha de ~500 MB para ~3,5 MB. Cada polígono é simplificado
# isoladamente, então podem surgir pequenas frestas entre vizinhos.
GEOMETRY_TOLERANCE = 0.01
_geometry_cache: dict[float, dict] = {}
_geometry_lock = threading.Lock()


def filters(
    variable: Variable = Query("precipitacao", description="Variável e sentido da anomalia"),
    event_class: EventClass = Query("todas", description="Classe operacional dos eventos"),
    start_year: int = Query(2017, ge=2015, le=2025),
    end_year: int = Query(2025, ge=2015, le=2025),
    season: Season | None = Query(None, description="Estação do Hemisfério Sul"),
    enso_phase: EnsoPhase | None = Query(None, description="Só meses desta fase (episódios NOAA)"),
) -> Filters:
    f = Filters(variable, event_class, start_year, end_year, season, enso_phase)
    try:
        f.validate()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return f


def _call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except SnapshotMissing as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/definicoes")
def definitions():
    """Definições operacionais, métricas, estações, regra ENSO e data do snapshot."""
    return _call(get_service().definitions)


@router.get("/coropletico")
def choropleth(
    metric: Metric = Query("taxa"),
    compare_phase: Literal["el_nino", "la_nina"] = Query("el_nino", description="Só para metric=razao_enso"),
    f: Filters = Depends(filters),
):
    """Valor da métrica por município, com quebras de classe, status e resumo."""
    return _call(get_service().choropleth, metric, f, compare_phase)


@router.get("/municipios/{codigo_ibge}")
def municipality(codigo_ibge: int, f: Filters = Depends(filters)):
    """Distribuição sazonal do município comparada com UF, região e Brasil; ENSO por estação."""
    try:
        return _call(get_service().municipality, codigo_ibge, f)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Município não encontrado") from error


@router.get("/regioes")
def regions(f: Filters = Depends(filters)):
    """Participação sazonal agregada por região, padrões municipais e I de Moran."""
    return _call(get_service().regions, f)


@router.get("/ranking")
def ranking(
    season: Season = Query(..., description="Estação usada para ordenar"),
    limit: int = Query(20, ge=1, le=200),
    ascending: bool = Query(False),
    f: Filters = Depends(filters),
):
    """Municípios com maior (ou menor) participação normalizada da estação (≥ 20 eventos)."""
    return _call(get_service().ranking, f, season, limit, ascending)


@router.get("/noticias-intensidade")
def news_by_intensity():
    """Eventos de chuva com notícia verificada, por intensidade e por classe (IC 95% de Wilson)."""
    return _call(get_service().news_by_intensity)


@router.get("/visao-geral")
def overview():
    """Volume de dados reunido pela plataforma."""
    return _call(get_service().overview)


@router.get("/geometrias")
def geometries(db: Session = Depends(get_db)):
    """Malha municipal nacional simplificada (GeoJSON), em cache no processo."""
    with _geometry_lock:
        cached = _geometry_cache.get(GEOMETRY_TOLERANCE)
        if cached is None:
            rows = db.execute(
                text(
                    "SELECT codigo_ibge, ST_AsGeoJSON(ST_SimplifyPreserveTopology(geometry, :tol), 4) "
                    "FROM municipio WHERE geometry IS NOT NULL ORDER BY codigo_ibge"
                ),
                {"tol": GEOMETRY_TOLERANCE},
            ).all()
            cached = {
                "type": "FeatureCollection",
                "properties": {"simplification_degrees": GEOMETRY_TOLERANCE, "source": "Malha municipal IBGE 2025"},
                "features": [
                    {"type": "Feature", "properties": {"codigo_ibge": int(code)}, "geometry": loads(geometry)}
                    for code, geometry in rows
                    if geometry
                ],
            }
            _geometry_cache[GEOMETRY_TOLERANCE] = cached
    return cached
