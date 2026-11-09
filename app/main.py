from datetime import date, datetime, time, timedelta, timezone
from json import loads

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import (
    get_by_codigo_ibge,
    get_geometria_geojson,
    list_enso_mensal,
    list_geometrias_geojson,
    list_geometrias_por_uf,
    list_registros_climaticos,
    list_registros_climaticos_mensais,
    list_municipios,
    municipio_existe,
)
from app.schemas.clima import ClimaMunicipioResponse
from app.schemas.municipio import MunicipioSemGeometriaResponse
from app.climate_news.router import router as climate_news_router

app = FastAPI(
    title="API de Municípios",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# /api/climate é o caminho público; /climate atende o proxy do Vite, que
# remove o prefixo /api ao encaminhar as chamadas do front-end.
app.include_router(climate_news_router, prefix="/api/climate")
app.include_router(climate_news_router, prefix="/climate", include_in_schema=False)


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.get("/municipios", response_model=list[MunicipioSemGeometriaResponse])
def municipios(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
):
    municipios = list_municipios(
        db,
        limit=limit,
        offset=offset,
    )

    return municipios


@app.get("/municipios/geometrias", response_model=dict[str, object])
def geometrias_municipios(
    codigos_ibge: list[int] | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Códigos IBGE; repita o parâmetro para consultar vários municípios",
    ),
    uf: str | None = Query(
        default=None,
        min_length=2,
        max_length=2,
        pattern="^[A-Za-z]{2}$",
        description="Sigla da unidade federativa, por exemplo GO",
    ),
    db: Session = Depends(get_db),
):
    if bool(codigos_ibge) == bool(uf):
        raise HTTPException(
            status_code=422,
            detail="Informe codigos_ibge ou uf, mas não ambos",
        )

    if uf:
        rows = list_geometrias_por_uf(db, uf.upper())
    else:
        rows = list_geometrias_geojson(db, codigos_ibge)

    geometria_por_codigo = {codigo: geometria for codigo, geometria in rows}
    ausentes = sorted(set(codigos_ibge or []) - geometria_por_codigo.keys())
    if ausentes:
        raise HTTPException(
            status_code=404,
            detail={"municipios_nao_encontrados": ausentes},
        )

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"codigo_ibge": codigo},
                "geometry": loads(geometria_por_codigo[codigo]),
            }
            for codigo in sorted(geometria_por_codigo)
        ],
    }


@app.get(
    "/municipios/{codigo_ibge}",
    response_model=MunicipioSemGeometriaResponse,
)
def municipio(
    codigo_ibge: int,
    db: Session = Depends(get_db),
):
    municipio = get_by_codigo_ibge(
        db,
        codigo_ibge,
    )

    if municipio is None:
        raise HTTPException(
            status_code=404,
            detail="Município não encontrado",
        )

    return municipio


@app.get("/municipios/{codigo_ibge}/geometria", response_model=dict[str, object])
def geometria_municipio(
    codigo_ibge: int,
    db: Session = Depends(get_db),
):
    geometria = get_geometria_geojson(db, codigo_ibge)
    if geometria is None:
        raise HTTPException(status_code=404, detail="Município não encontrado")
    return loads(geometria)


@app.get(
    "/municipios/{codigo_ibge}/clima",
    response_model=ClimaMunicipioResponse,
)
def clima_municipio(
    codigo_ibge: int,
    inicio: date = Query(description="Data inicial inclusiva (UTC), no formato AAAA-MM-DD"),
    fim: date = Query(description="Data final inclusiva (UTC), no formato AAAA-MM-DD"),
    db: Session = Depends(get_db),
):
    if inicio > fim:
        raise HTTPException(
            status_code=422,
            detail="A data inicial não pode ser posterior à data final",
        )

    inicio_utc = datetime.combine(inicio, time.min, tzinfo=timezone.utc)
    fim_exclusivo_utc = datetime.combine(
        fim + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )

    registros = list_registros_climaticos(
        db,
        codigo_ibge,
        inicio_utc,
        fim_exclusivo_utc,
    )
    if not registros and not municipio_existe(db, codigo_ibge):
        raise HTTPException(status_code=404, detail="Município não encontrado")
    return {
        "codigo_ibge": codigo_ibge,
        "registros": registros,
        "enso": list_enso_mensal(db, inicio, fim),
    }


@app.get(
    "/municipios/{codigo_ibge}/clima/mensal",
    response_model=ClimaMunicipioResponse,
)
def clima_municipio_mensal(
    codigo_ibge: int,
    inicio: date = Query(description="Data inicial inclusiva (UTC), no formato AAAA-MM-DD"),
    fim: date = Query(description="Data final inclusiva (UTC), no formato AAAA-MM-DD"),
    db: Session = Depends(get_db),
):
    if inicio > fim:
        raise HTTPException(
            status_code=422,
            detail="A data inicial não pode ser posterior à data final",
        )

    inicio_utc = datetime.combine(inicio, time.min, tzinfo=timezone.utc)
    fim_exclusivo_utc = datetime.combine(
        fim + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )
    registros = list_registros_climaticos_mensais(
        db,
        codigo_ibge,
        inicio_utc,
        fim_exclusivo_utc,
    )
    if not registros and not municipio_existe(db, codigo_ibge):
        raise HTTPException(status_code=404, detail="Município não encontrado")
    return {
        "codigo_ibge": codigo_ibge,
        "registros": registros,
        "enso": list_enso_mensal(db, inicio, fim),
    }
