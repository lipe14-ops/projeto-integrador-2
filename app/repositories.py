from datetime import date, datetime as DateTimeValue

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, defer, joinedload

from app.models.enso_mensal import EnsoMensal
from app.models.municipio import Municipio
from app.models.municipio_details import MunicipioDetails
from app.models.registro_climatico import RegistroClimatico


def get_by_codigo_ibge(
    db: Session,
    codigo_ibge: int,
):
    stmt = (
        select(Municipio)
        .options(
            joinedload(Municipio.details),
            defer(Municipio.geometry),
        )
        .where(
            Municipio.codigo_ibge == codigo_ibge
        )
    )

    return db.scalar(stmt)


def get_geometria_geojson(db: Session, codigo_ibge: int):
    stmt = select(func.ST_AsGeoJSON(Municipio.geometry)).where(
        Municipio.codigo_ibge == codigo_ibge
    )
    return db.scalar(stmt)


def list_geometrias_geojson(db: Session, codigos_ibge: list[int]):
    stmt = (
        select(Municipio.codigo_ibge, func.ST_AsGeoJSON(Municipio.geometry))
        .where(Municipio.codigo_ibge.in_(codigos_ibge))
        .order_by(Municipio.codigo_ibge)
    )
    return db.execute(stmt).all()


def list_geometrias_por_uf(db: Session, uf: str):
    stmt = (
        select(Municipio.codigo_ibge, func.ST_AsGeoJSON(Municipio.geometry))
        .join(MunicipioDetails, MunicipioDetails.codigo_ibge == Municipio.codigo_ibge)
        .where(MunicipioDetails.uf == uf)
    )
    return db.execute(stmt).all()


def municipio_existe(db: Session, codigo_ibge: int) -> bool:
    stmt = select(Municipio.codigo_ibge).where(
        Municipio.codigo_ibge == codigo_ibge
    )
    return db.scalar(stmt) is not None


def list_enso_mensal(db: Session, inicio: date, fim: date):
    stmt = (
        select(
            EnsoMensal.year,
            EnsoMensal.month,
            EnsoMensal.enso_index,
        )
        .where(
            or_(
                EnsoMensal.year > inicio.year,
                and_(EnsoMensal.year == inicio.year, EnsoMensal.month >= inicio.month),
            ),
            or_(
                EnsoMensal.year < fim.year,
                and_(EnsoMensal.year == fim.year, EnsoMensal.month <= fim.month),
            ),
        )
        .order_by(EnsoMensal.year, EnsoMensal.month)
    )
    return db.execute(stmt).mappings().all()


def list_municipios(
    db: Session,
    limit: int = 100,
    offset: int = 0,
):
    stmt = (
        select(Municipio)
        .options(
            joinedload(Municipio.details)
        )
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(stmt).unique().all()


def list_registros_climaticos(
    db: Session,
    codigo_ibge: int,
    inicio: DateTimeValue,
    fim_exclusivo: DateTimeValue,
):
    stmt = (
        select(
            RegistroClimatico.datetime,
            RegistroClimatico.umidade,
            RegistroClimatico.temperatura,
            RegistroClimatico.precipitacao,
        )
        .where(
            RegistroClimatico.codigo_ibge == codigo_ibge,
            RegistroClimatico.datetime >= inicio,
            RegistroClimatico.datetime < fim_exclusivo,
        )
        .order_by(RegistroClimatico.datetime)
    )

    return db.execute(stmt).mappings().all()