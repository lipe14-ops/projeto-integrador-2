"""Acesso aos dados de entrada: série diária do banco, contexto municipal e ONI."""

from __future__ import annotations

import re
from datetime import date

import pandas as pd
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.climate_news.agents.base import MunicipalityContext
from app.climate_news.detection.preparation import (
    DataQualityReport,
    aggregate_era5_12h_to_daily,
    prepare_daily_series,
)
from app.models.enso_mensal import EnsoMensal
from app.models.municipio import Municipio  # noqa: F401 — registra relacionamentos
from app.models.registro_climatico import RegistroClimatico  # noqa: F401
from app.models.municipio_details import MunicipioDetails


class MunicipalityNotFound(LookupError):
    pass


def resolve_municipality(
    db: Session,
    name: str | None = None,
    uf: str | None = None,
    codigo_ibge: int | None = None,
    max_neighbors: int = 5,
) -> MunicipalityContext:
    stmt = select(MunicipioDetails)
    if codigo_ibge is not None:
        stmt = stmt.where(MunicipioDetails.codigo_ibge == codigo_ibge)
    else:
        if not name:
            raise ValueError("Informe o nome do município ou o código IBGE.")
        stmt = stmt.where(func.lower(MunicipioDetails.municipio) == name.strip().lower())
        if uf:
            stmt = stmt.where(MunicipioDetails.uf == uf.upper())
    rows = db.scalars(stmt).all()
    if not rows:
        raise MunicipalityNotFound(f"Município não encontrado: {name or codigo_ibge} {uf or ''}".strip())
    if len(rows) > 1:
        options = ", ".join(f"{r.municipio}/{r.uf} ({r.codigo_ibge})" for r in rows)
        raise ValueError(f"Nome ambíguo; informe a UF ou o código IBGE: {options}")
    details = rows[0]
    homonyms = db.scalar(
        select(func.count()).select_from(MunicipioDetails).where(
            func.lower(MunicipioDetails.municipio) == details.municipio.lower(),
            MunicipioDetails.codigo_ibge != details.codigo_ibge,
        )
    )
    # outros municípios cujo nome contém este como palavras inteiras
    # ("Lucas do Rio Verde", "Porto Alegre do Norte"): menções a eles não contam
    pattern = re.compile(rf"(?<![\w-]){re.escape(details.municipio)}(?![\w-])", re.IGNORECASE)
    colliding = [
        nome
        for (nome,) in db.execute(
            select(MunicipioDetails.municipio).where(
                MunicipioDetails.municipio.ilike(f"%{details.municipio}%"),
                func.lower(MunicipioDetails.municipio) != details.municipio.lower(),
            )
        )
        if pattern.search(nome)
    ]
    neighbors = db.execute(
        text(
            """
            SELECT d.municipio
            FROM municipio AS alvo
            JOIN municipio AS m ON m.codigo_ibge <> alvo.codigo_ibge
                 AND m.geometry && alvo.geometry AND ST_Touches(m.geometry, alvo.geometry)
            JOIN municipio_details AS d ON d.codigo_ibge = m.codigo_ibge
            WHERE alvo.codigo_ibge = :codigo
              AND d.municipio NOT ILIKE 'Área Operacional%'  -- áreas especiais do IBGE
            ORDER BY d.populacao DESC NULLS LAST
            LIMIT :limite
            """
        ),
        {"codigo": details.codigo_ibge, "limite": max_neighbors},
    ).scalars().all()
    return MunicipalityContext(
        name=details.municipio,
        uf=details.uf,
        state=details.estado,
        region=details.regiao,
        codigo_ibge=int(details.codigo_ibge),
        neighbors=list(neighbors),
        homonym=bool(homonyms),
        colliding_names=sorted(set(colliding)),
    )


def _has_daily_view(db: Session) -> bool:
    return bool(db.scalar(text("SELECT to_regclass('precipitacao_diaria') IS NOT NULL")))


def load_daily_series(
    db: Session,
    codigo_ibge: int,
    start: date | None = None,
    end: date | None = None,
) -> tuple[pd.Series, DataQualityReport]:
    """Série diária do município.

    Usa a visão ``precipitacao_diaria`` (gravada em ordem de município) quando
    existe; senão agrega os acumulados de 12 h de ``registro_climatico``. Os dois
    caminhos seguem o mesmo critério: dia com uma só metade fica ausente.
    """
    if _has_daily_view(db):
        conditions = ["codigo_ibge = :codigo"]
        params: dict = {"codigo": codigo_ibge}
        if start:
            conditions.append("dia >= :inicio")
            params["inicio"] = start
        if end:
            conditions.append("dia <= :fim")
            params["fim"] = end
        rows = db.execute(
            text(
                "SELECT dia, precipitacao, n_metades FROM precipitacao_diaria "
                f"WHERE {' AND '.join(conditions)} ORDER BY codigo_ibge, dia"
            ),
            params,
        ).all()
        if not rows:
            raise MunicipalityNotFound(f"Sem registros climáticos para o município {codigo_ibge}.")
        frame = pd.DataFrame(rows, columns=["date", "precipitation_mm", "n"])
        incomplete = int((frame["n"] < 2).sum())
        frame.loc[frame["n"] < 2, "precipitation_mm"] = float("nan")
        return prepare_daily_series(frame[["date", "precipitation_mm"]], incomplete_aggregation=incomplete)

    conditions = ["codigo_ibge = :codigo"]
    params: dict = {"codigo": codigo_ibge}
    if start:
        conditions.append("datetime > :inicio")  # 00 UTC do dia inicial pertence ao dia anterior
        params["inicio"] = pd.Timestamp(start, tz="UTC")
    if end:
        conditions.append("datetime <= :fim")
        params["fim"] = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    rows = db.execute(
        text(f"SELECT datetime, precipitacao FROM registro_climatico WHERE {' AND '.join(conditions)} ORDER BY codigo_ibge, datetime"),
        params,
    ).all()
    if not rows:
        raise MunicipalityNotFound(f"Sem registros climáticos para o município {codigo_ibge}.")
    frame = pd.DataFrame(rows, columns=["datetime", "precipitacao"])
    daily, incomplete = aggregate_era5_12h_to_daily(frame)
    return prepare_daily_series(daily, incomplete_aggregation=incomplete)


def load_enso(db: Session) -> dict[tuple[int, int], float]:
    rows = db.execute(select(EnsoMensal.year, EnsoMensal.month, EnsoMensal.enso_index)).all()
    return {(int(y), int(m)): float(v) for y, m, v in rows if v is not None}
