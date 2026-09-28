from pydantic import BaseModel, ConfigDict


class MunicipioDetailsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo_ibge: int
    municipio: str
    uf: str
    estado: str
    regiao: str | None
    mesorregiao: str | None
    microrregiao: str | None
    populacao: int | None
    ano_populacao: int | None
    bioma: str | None
    geomorfologia: str | None
    regiao_geomorfologica: str | None
    dominio_geomorfologico: str | None
    area_km2: float | None


class MunicipioBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo_ibge: int
    latitude: float | None
    longitude: float | None
    details: MunicipioDetailsResponse | None


class MunicipioResponse(MunicipioBaseResponse):
    geometry: dict


class MunicipioSemGeometriaResponse(MunicipioBaseResponse):
    pass